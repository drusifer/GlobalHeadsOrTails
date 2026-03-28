import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ntag424_sdm_provisioner.crypto.crypto_primitives import calculate_entropy

log = logging.getLogger(__name__)

VALID_FLIP_COUNTS = (10, 25, 50, 100)


class FlipOffError(ValueError):
    """Raised for invalid challenge operations."""


class FlipOffService:
    """Manages Flip Off challenge lifecycle.

    Shares the same SQLite database as SqliteGameStateManager so it can
    query scan_logs for post-challenge flip entropy calculations.
    """

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flip_off_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    baseline_scan_id INTEGER NOT NULL DEFAULT 0,
                    challenger_coin_name TEXT NOT NULL,
                    challenged_coin_name TEXT NOT NULL,
                    flip_count INTEGER NOT NULL CHECK(flip_count IN (10, 25, 50, 100)),
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'in_progress', 'complete', 'expired')),
                    challenger_flips_done INTEGER NOT NULL DEFAULT 0,
                    challenged_flips_done INTEGER NOT NULL DEFAULT 0,
                    challenger_entropy REAL,
                    challenged_entropy REAL,
                    winner_coin_name TEXT,
                    completed_at DATETIME,
                    end_condition TEXT CHECK(end_condition IN ('win','draw','yield','expired'))
                )
            """)
            conn.commit()
            try:
                conn.execute(
                    "ALTER TABLE flip_off_challenges ADD COLUMN end_condition TEXT"
                    " CHECK(end_condition IN ('win','draw','yield','expired'))"
                )
                conn.commit()
            except Exception:
                pass  # column already exists

    def create_challenge(
        self, challenger_coin: str, challenged_coin: str, flip_count: int
    ) -> int:
        """Creates a new Flip Off challenge.

        Args:
            challenger_coin: coin_name of the initiating coin.
            challenged_coin: coin_name of the target coin.
            flip_count: number of flips each coin must complete (10/25/50/100).

        Returns:
            The new challenge ID.

        Raises:
            FlipOffError: if inputs are invalid or either coin has an active challenge.
        """
        if flip_count not in VALID_FLIP_COUNTS:
            raise FlipOffError(f"flip_count must be one of {VALID_FLIP_COUNTS}")
        if challenger_coin == challenged_coin:
            raise FlipOffError("A coin cannot challenge itself.")

        with self._get_conn() as conn:
            # Check + insert in one connection so the constraint is atomic.
            # Multiple concurrent flip-offs are allowed; each coin may only
            # appear in one active challenge at a time (either role).
            active_sql = """
                SELECT id FROM flip_off_challenges
                WHERE status IN ('pending', 'in_progress')
                  AND (challenger_coin_name = ? OR challenged_coin_name = ?)
                LIMIT 1"""
            if conn.execute(active_sql, (challenger_coin, challenger_coin)).fetchone():
                raise FlipOffError(f"{challenger_coin} already has an active challenge.")
            if conn.execute(active_sql, (challenged_coin, challenged_coin)).fetchone():
                raise FlipOffError(f"{challenged_coin} already has an active challenge.")

            # Capture scan baseline so only flips after this point count
            result = conn.execute("SELECT COALESCE(MAX(id), 0) FROM scan_logs").fetchone()
            baseline_scan_id = result[0] if result else 0

            cursor = conn.execute(
                """INSERT INTO flip_off_challenges
                   (challenger_coin_name, challenged_coin_name, flip_count, baseline_scan_id)
                   VALUES (?, ?, ?, ?)""",
                (challenger_coin, challenged_coin, flip_count, baseline_scan_id),
            )
            conn.commit()
            challenge_id = cursor.lastrowid

        log.info(
            "[FLIP OFF] Challenge %d created: %s vs %s (%d flips)",
            challenge_id, challenger_coin, challenged_coin, flip_count,
        )
        return challenge_id

    def get_active_challenge(self, coin_name: str) -> Optional[dict]:
        """Returns the active (pending/in_progress) challenge for a coin, or None."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status IN ('pending', 'in_progress')
                     AND (challenger_coin_name = ? OR challenged_coin_name = ?)
                   ORDER BY id DESC LIMIT 1""",
                (coin_name, coin_name),
            )
            row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def get_challenge(self, challenge_id: int) -> Optional[dict]:
        """Returns a challenge record by ID, or None."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges WHERE id = ?""",
                (challenge_id,),
            )
            row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def record_flip(self, coin_name: str) -> None:
        """Called after each validated flip. Increments challenge progress.

        When both coins reach flip_count, calculates entropy and records the winner.
        No-op if the coin has no active challenge.
        """
        challenge = self.get_active_challenge(coin_name)
        if not challenge:
            return

        cid = challenge["id"]
        is_challenger = challenge["challenger_coin_name"] == coin_name
        col = "challenger_flips_done" if is_challenger else "challenged_flips_done"

        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE flip_off_challenges SET {col} = {col} + 1, status = 'in_progress' WHERE id = ?",  # noqa: S608
                (cid,),
            )
            conn.commit()

        updated = self.get_challenge(cid)
        if not updated:
            return
        log.info(
            "[FLIP OFF] record_flip challenge=%d coin=%s %s=%d/%d %s=%d/%d",
            cid, coin_name,
            updated["challenger_coin_name"], updated["challenger_flips_done"], updated["flip_count"],
            updated["challenged_coin_name"], updated["challenged_flips_done"], updated["flip_count"],
        )
        if (
            updated["challenger_flips_done"] >= updated["flip_count"]
            and updated["challenged_flips_done"] >= updated["flip_count"]
        ):
            log.info("[FLIP OFF] challenge=%d both coins done — calculating winner", cid)
            self._calculate_winner(cid)

    def _calculate_winner(self, challenge_id: int) -> None:
        """Queries scan_logs for N post-challenge flips per coin, calculates entropy, records winner."""
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return

        challenger = challenge["challenger_coin_name"]
        challenged = challenge["challenged_coin_name"]
        n = challenge["flip_count"]
        baseline = challenge["baseline_scan_id"]

        challenger_entropy = self._coin_challenge_entropy(challenger, baseline, n)
        challenged_entropy = self._coin_challenge_entropy(challenged, baseline, n)

        if round(challenger_entropy, 4) > round(challenged_entropy, 4):
            winner = challenger
        elif round(challenged_entropy, 4) > round(challenger_entropy, 4):
            winner = challenged
        else:
            winner = "DRAW"

        end_condition = 'draw' if winner == 'DRAW' else 'win'
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE flip_off_challenges
                   SET status = 'complete', challenger_entropy = ?, challenged_entropy = ?,
                       winner_coin_name = ?, completed_at = CURRENT_TIMESTAMP, end_condition = ?
                   WHERE id = ?""",
                (round(challenger_entropy, 4), round(challenged_entropy, 4), winner, end_condition, challenge_id),
            )
            conn.commit()

        log.info(
            "[FLIP OFF] Challenge %d complete: %s(%.4f) vs %s(%.4f) → winner=%s",
            challenge_id, challenger, challenger_entropy, challenged, challenged_entropy, winner,
        )

    def _coin_challenge_entropy(self, coin_name: str, baseline_scan_id: int, n: int) -> float:
        """Returns Shannon entropy for a coin's N validated flips after challenge creation.

        Uses H=1/T=0 bit encoding, same as analyze_flip_sequence_randomness().
        Filters by scan_logs.id > baseline_scan_id (set at challenge creation time)
        to avoid timestamp collision issues.
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT LOWER(outcome) FROM scan_logs
                   WHERE coin_name = ? AND id > ? AND is_test IS FALSE
                     AND LOWER(outcome) IN ('heads', 'tails')
                   ORDER BY id ASC LIMIT ?""",
                (coin_name, baseline_scan_id, n),
            )
            rows = cursor.fetchall()

        if not rows:
            return 0.0

        bit_string = "".join("1" if r[0] == "heads" else "0" for r in rows)
        if len(bit_string) % 8 != 0:
            bit_string += "0" * (8 - len(bit_string) % 8)
        byte_sequence = int(bit_string, 2).to_bytes(len(bit_string) // 8, byteorder="big")
        return calculate_entropy(byte_sequence)

    def get_latest_challenge(self, coin_name: str) -> Optional[dict]:
        """Returns the most recent non-expired challenge for a coin (any status except expired)."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status != 'expired'
                     AND (challenger_coin_name = ? OR challenged_coin_name = ?)
                   ORDER BY id DESC LIMIT 1""",
                (coin_name, coin_name),
            )
            row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def yield_challenge(self, coin_name: str) -> dict:
        """The given coin yields, granting the opponent an immediate victory.

        Args:
            coin_name: the coin that is surrendering.

        Returns:
            The updated challenge record.

        Raises:
            FlipOffError: if the coin has no active challenge.
        """
        challenge = self.get_active_challenge(coin_name)
        if not challenge:
            raise FlipOffError(f"{coin_name} has no active challenge to yield.")

        winner = (
            challenge["challenged_coin_name"]
            if challenge["challenger_coin_name"] == coin_name
            else challenge["challenger_coin_name"]
        )
        challenger_entropy = self._coin_challenge_entropy(
            challenge["challenger_coin_name"], challenge["baseline_scan_id"], challenge["flip_count"]
        )
        challenged_entropy = self._coin_challenge_entropy(
            challenge["challenged_coin_name"], challenge["baseline_scan_id"], challenge["flip_count"]
        )

        with self._get_conn() as conn:
            conn.execute(
                """UPDATE flip_off_challenges
                   SET status = 'complete', winner_coin_name = ?,
                       challenger_entropy = ?, challenged_entropy = ?,
                       completed_at = CURRENT_TIMESTAMP, end_condition = 'yield'
                   WHERE id = ?""",
                (winner, round(challenger_entropy, 4), round(challenged_entropy, 4), challenge["id"]),
            )
            conn.commit()

        log.info("[FLIP OFF] Challenge %d yielded by %s — %s wins", challenge["id"], coin_name, winner)
        return self.get_challenge(challenge["id"])

    def get_recent_completed(self, limit: int = 3) -> list:
        """Returns the most recently completed challenges."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status = 'complete'
                   ORDER BY completed_at DESC LIMIT ?""",
                (limit,),
            )
            rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_all_coin_stats(self) -> dict:
        """Returns flip-off W/L/D stats per coin for completed challenges."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT coin_name,
                       SUM(CASE WHEN winner_coin_name = coin_name THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN winner_coin_name != coin_name AND winner_coin_name != 'DRAW' THEN 1 ELSE 0 END) as losses,
                       SUM(CASE WHEN winner_coin_name = 'DRAW' THEN 1 ELSE 0 END) as draws
                FROM (
                    SELECT challenger_coin_name AS coin_name, winner_coin_name
                    FROM flip_off_challenges WHERE status = 'complete'
                    UNION ALL
                    SELECT challenged_coin_name AS coin_name, winner_coin_name
                    FROM flip_off_challenges WHERE status = 'complete'
                )
                GROUP BY coin_name
            """)
            rows = cursor.fetchall()
        return {row[0]: {"wins": row[1], "losses": row[2], "draws": row[3]} for row in rows}

    def get_all_active_challenges(self) -> list:
        """Returns all active (pending/in_progress) challenges."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """SELECT id, created_at, baseline_scan_id, challenger_coin_name, challenged_coin_name,
                          flip_count, status, challenger_flips_done, challenged_flips_done,
                          challenger_entropy, challenged_entropy, winner_coin_name, completed_at, end_condition
                   FROM flip_off_challenges
                   WHERE status IN ('pending', 'in_progress')
                   ORDER BY id DESC""",
            )
            rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def expire_stale_challenges(self, hours: int = 24) -> list:
        """Marks challenges older than `hours` hours as 'expired'.

        Returns:
            List of expired challenge dicts (for SSE notification).
        """
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT id FROM flip_off_challenges
                   WHERE status IN ('pending', 'in_progress') AND created_at < ?""",
                (cutoff,),
            ).fetchall()
            if not rows:
                return []
            ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids))
            conn.execute(
                f"UPDATE flip_off_challenges SET status = 'expired', end_condition = 'expired', completed_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",  # noqa: S608
                ids,
            )
            conn.commit()

        log.info("[FLIP OFF] Expired %d challenge(s)", len(ids))
        return [self.get_challenge(cid) for cid in ids]

    @staticmethod
    def _row_to_dict(row: tuple) -> dict:
        keys = [
            "id", "created_at", "baseline_scan_id", "challenger_coin_name", "challenged_coin_name",
            "flip_count", "status", "challenger_flips_done", "challenged_flips_done",
            "challenger_entropy", "challenged_entropy", "winner_coin_name", "completed_at", "end_condition",
        ]
        return dict(zip(keys, row))
