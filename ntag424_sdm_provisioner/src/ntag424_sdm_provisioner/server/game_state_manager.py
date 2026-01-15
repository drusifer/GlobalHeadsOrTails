import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict

from ntag424_sdm_provisioner.csv_key_manager import UID
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_entropy,
    nist_frequency_monobit_test,
)
log = logging.getLogger(__name__)

@dataclass
class TagGameState:
    """Game state for a single NTAG424 DNA tag."""
    uid: str
    outcome: str = ""  # "heads" or "tails"
    last_counter: int = 0
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())

class IGameStateManager(ABC):
    """Interface for game state persistence."""

    @abstractmethod
    def get_state(self, uid: str) -> TagGameState:
        pass

    @abstractmethod
    def update_state(self, uid: str, counter: int, outcome: str, cmac: str = "", is_test: bool = False):
        pass

    @abstractmethod
    def get_totals(self, include_test: bool = False) -> Dict[str, int]:
        pass

    @abstractmethod
    def analyze_flip_sequence_randomness(self, include_test: bool = False, uid: str | None = None) -> Dict:
        pass

    @abstractmethod
    def get_leaderboard_stats(self, include_test: bool = False) -> list[dict]:
        pass


class SqliteGameStateManager(IGameStateManager):
    """Manages game state persistence using SQLite."""

    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            # Table for historical logs (every scan)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    uid TEXT NOT NULL,
                    counter INTEGER NOT NULL,
                    outcome TEXT NOT NULL,
                    cmac TEXT,
                    is_test BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            # Index for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_uid_counter ON scan_logs (uid, counter)")

            # Add is_test column if it doesn't exist (for backward compatibility)
            cursor = conn.execute("PRAGMA table_info(scan_logs)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'is_test' not in columns:
                log.info("Adding 'is_test' column to scan_logs table.")
                conn.execute("ALTER TABLE scan_logs ADD COLUMN is_test BOOLEAN NOT NULL DEFAULT FALSE")

            conn.commit()

    def _query(self, sql: str, params: tuple = ()):
        with self._get_conn() as conn:
            # Get the latest scan for this UID
            log.debug(f"[GAME STATE SQLITE] Executing query: {sql}")
            cursor = conn.execute( sql, params)
            rows = cursor.fetchall()
            log.debug(f"[GAME STATE SQLITE] - Rows fetched: {len(rows)}")
            return rows

    def get_state(self, uid: str) -> TagGameState:
        uid = uid.upper()
        rows = self._query(
                "SELECT outcome, counter, timestamp FROM scan_logs WHERE uid = ? ORDER BY counter DESC LIMIT 1",
                (uid,)
        )
        if rows:
            row = rows[0]
            return TagGameState(uid=uid, outcome=row[0], last_counter=row[1], last_seen=row[2])
        else:
            return TagGameState(uid=uid)

    def update_state(self, uid: str, counter: int, outcome: str, cmac: str = "", is_test: bool = False):
        uid = uid.upper()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO scan_logs (uid, counter, outcome, cmac, is_test) VALUES (?, ?, ?, ?, ?)",
                (uid, counter, outcome.lower(), cmac, is_test)
            )
            conn.commit()
        log_prefix = "[TEST] " if is_test else ""
        log.info(f"{log_prefix}[GAME STATE SQLITE] Logged scan for {uid}: outcome={outcome.lower()}, ctr={counter}")

    def get_totals(self, include_test: bool = False) -> Dict[str, int]:
        heads = self._query(
            "SELECT COUNT(*) FROM scan_logs WHERE LOWER(outcome) = ? AND (is_test IS False OR ?)",
            ('heads', include_test)
        )[0][0]
        tails = self._query(
            "SELECT COUNT(*) FROM scan_logs WHERE LOWER(outcome) = ? AND (is_test IS False OR ?)",
            ('tails', include_test)
        )[0][0]

        return {"heads": heads, "tails": tails}

    def get_recent_flips(self, limit: int = 88) -> list[dict]:
        rows = self._query(
            "SELECT uid, LOWER(outcome), timestamp FROM scan_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        recent_flips = []
        for row in rows:
            uid_str, outcome, timestamp = row
            recent_flips.append({
                "asset_tag": UID(uid_str).asset_tag,
                "outcome": outcome,
                "timestamp": timestamp
            })
        return recent_flips

    def analyze_flip_sequence_randomness(self, include_test: bool = False, uid: str | None = None) -> Dict:
        """
        Fetches all flip outcomes, converts them to a binary sequence (HEADS=1, TAILS=0),
        and runs randomness tests (Shannon entropy, NIST Monobit).

        Args:
            include_test: If True, includes test data in the analysis.
            uid: If provided, analyzes flips only for this UID.

        Returns:
            A dictionary with the analysis results.
        """
        conditions = ["LOWER(outcome) IN ('heads', 'tails')"]
        params = []

        if uid:
            conditions.append("uid = ?")
            params.append(uid.upper())

        if not include_test:
            conditions.append("is_test IS FALSE")

        query = f"SELECT LOWER(outcome) FROM scan_logs WHERE {' AND '.join(conditions)} ORDER BY id ASC"

        rows = self._query(query, tuple(params))

        if not rows:
            return {"total_bits": 0, "entropy": 0.0, "nist_monobit_p_value": None, "nist_monobit_passed": None, "error": "No flips to analyze."}

        # Convert sequence to a string of bits
        bit_string = "".join(['1' if row[0] == 'heads' else '0' for row in rows])
        total_bits = len(bit_string)

        if total_bits == 0:
            return {"total_bits": 0, "entropy": 0.0, "nist_monobit_p_value": None, "nist_monobit_passed": None, "error": "No flips to analyze."}

        # Convert bit string to bytes
        if total_bits % 8 != 0:
            bit_string += '0' * (8 - total_bits % 8) # Pad to nearest byte
        byte_sequence = int(bit_string, 2).to_bytes(len(bit_string) // 8, byteorder='big')

        entropy = calculate_entropy(byte_sequence)
        p_value, passed, error = None, None, None
        try:
            p_value, passed = nist_frequency_monobit_test(byte_sequence)
        except ValueError as e:
            error = str(e)

        return {"total_bits": total_bits, "entropy": entropy, "nist_monobit_p_value": p_value, "nist_monobit_passed": passed, "nist_error": error}

    def get_leaderboard_stats(self, include_test: bool = False) -> list[dict]:
        """
        Calculates randomness stats for each coin and returns a ranked list.
        """
        # 1. Get all unique UIDs
        query = "SELECT DISTINCT uid FROM scan_logs"
        params = ()
        if not include_test:
            query += " WHERE is_test IS FALSE"
        
        uids_rows = self._query(query, params)
        uids = [row[0] for row in uids_rows]

        leaderboard = []
        for uid_str in uids:
            # 2. Get stats for each UID
            stats = self.analyze_flip_sequence_randomness(include_test=include_test, uid=uid_str)
            if stats and stats.get("total_bits", 0) > 0:
                leaderboard.append({
                    "coin_id": UID(uid_str).asset_tag,
                    **stats
                })

        # 3. Sort by entropy, descending
        leaderboard.sort(key=lambda x: x.get('entropy', 0), reverse=True)
        return leaderboard
