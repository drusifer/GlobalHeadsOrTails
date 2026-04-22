import logging
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)


class CoinMessageService:
    """Stores and retrieves per-coin custom Heads/Tails display messages."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coin_custom_messages (
                    coin_name     TEXT PRIMARY KEY,
                    heads_message TEXT NOT NULL DEFAULT '',
                    tails_message TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.commit()

    def get_messages(self, coin_name: str) -> tuple[str, str]:
        """Returns (heads_message, tails_message). Empty strings if not set."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT heads_message, tails_message FROM coin_custom_messages WHERE coin_name = ?",
                (coin_name,),
            ).fetchone()
        return (row[0], row[1]) if row else ("", "")

    def set_messages(self, coin_name: str, heads_message: str, tails_message: str) -> None:
        """UPSERT custom messages for a coin."""
        heads = heads_message.strip()
        tails = tails_message.strip()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO coin_custom_messages (coin_name, heads_message, tails_message)
                   VALUES (?, ?, ?)""",
                (coin_name, heads, tails),
            )
            conn.commit()
        log.info("[COIN MSG] set_messages coin=%s heads=%r tails=%r", coin_name, heads, tails)

    def validate_tap_auth(self, coin_name: str, cmac_hex: str, ctr_hex: str) -> bool:
        """Returns True iff the coin's last scan_logs entry matches cmac and counter."""
        try:
            expected_counter = int(ctr_hex, 16)
        except ValueError:
            return False
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT cmac, counter FROM scan_logs
                   WHERE coin_name = ? ORDER BY counter DESC LIMIT 1""",
                (coin_name,),
            ).fetchone()
        if not row:
            return False
        stored_cmac, stored_counter = row
        return stored_cmac == cmac_hex and stored_counter == expected_counter
