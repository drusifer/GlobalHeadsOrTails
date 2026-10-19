"""VIP Bat Signal service for gs.works/contact SDM tap authentication and ntfy.sh alerts."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sqlite3
import urllib.request

log = logging.getLogger(__name__)

DEFAULT_NTFY_URL = "https://ntfy.sh"
DEFAULT_NTFY_TOPIC = "gsworks-bat-signal-043f13e2"


class VipService:
    """Tracks per-tag VIP SDM read counters, persists VIP messages, and dispatches ntfy.sh push alerts."""

    def __init__(
        self,
        db_path: str,
        ntfy_url: str | None = None,
        ntfy_topic: str | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.ntfy_url = (ntfy_url or os.getenv("NTFY_URL") or DEFAULT_NTFY_URL).rstrip("/")
        self.ntfy_topic = (ntfy_topic or os.getenv("NTFY_TOPIC") or DEFAULT_NTFY_TOPIC).strip()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vip_counters (
                    uid          TEXT PRIMARY KEY,
                    last_counter INTEGER NOT NULL DEFAULT 0,
                    updated_at   TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vip_messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid         TEXT NOT NULL,
                    counter     INTEGER NOT NULL,
                    sender      TEXT NOT NULL,
                    message     TEXT NOT NULL,
                    ntfy_status TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                )
            """)
            conn.commit()

    def get_last_counter(self, uid: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT last_counter FROM vip_counters WHERE uid = ?",
                (uid.upper(),),
            ).fetchone()
        return int(row["last_counter"]) if row else -1

    def is_counter_fresh(self, uid: str, counter: int) -> bool:
        """Return True if counter is strictly greater than the last consumed VIP send counter."""
        if counter < 0:
            return False
        return counter > self.get_last_counter(uid)

    def send_bat_signal(
        self,
        uid: str,
        counter: int,
        sender: str,
        message: str,
    ) -> tuple[bool, str]:
        """Record VIP message, advance anti-replay counter, and POST urgent push alert to ntfy.sh."""
        uid_norm = uid.upper()
        if not self.is_counter_fresh(uid_norm, counter):
            return False, "replayed_counter"

        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO vip_messages (uid, counter, sender, message, ntfy_status, created_at)
                   VALUES (?, ?, ?, ?, 'pending', ?)""",
                (uid_norm, counter, sender, message, now_iso),
            )
            msg_id = cur.lastrowid
            conn.execute(
                """INSERT INTO vip_counters (uid, last_counter, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(uid) DO UPDATE SET
                       last_counter = excluded.last_counter,
                       updated_at = excluded.updated_at""",
                (uid_norm, counter, now_iso),
            )
            conn.commit()

        target_url = f"{self.ntfy_url}/{self.ntfy_topic}"
        payload = (
            f"From: {sender}\n"
            f"Tag UID: {uid_norm} (ctr={counter:06X})\n\n"
            f"{message}"
        ).encode("utf-8")
        req = urllib.request.Request(
            target_url,
            data=payload,
            method="POST",
            headers={
                "Title": "GS.WORKS VIP Bat Signal",
                "Priority": "urgent",
                "Tags": "rotating_light,bat",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

        ntfy_ok = False
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status_code = getattr(resp, "status", 200)
                ntfy_ok = 200 <= int(status_code) < 300
        except Exception as exc:
            log.warning("[VIP] ntfy.sh delivery failed for uid=%s ctr=%d: %s", uid_norm, counter, exc)
            ntfy_ok = False

        final_status = "sent" if ntfy_ok else "failed"
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE vip_messages SET ntfy_status = ? WHERE id = ?",
                (final_status, msg_id),
            )
            conn.commit()

        if ntfy_ok:
            log.info("[VIP] Bat Signal dispatched via ntfy.sh for uid=%s ctr=%d sender=%r", uid_norm, counter, sender)
            return True, "sent"
        return False, "notification_delivery_failed"

    def list_messages(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, uid, counter, sender, message, ntfy_status, created_at FROM vip_messages ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]
