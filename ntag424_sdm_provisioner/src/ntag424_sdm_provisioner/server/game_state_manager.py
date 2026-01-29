import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Dict

from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_entropy,
    nist_frequency_monobit_test,
)
from ntag424_sdm_provisioner.csv_key_manager import UID


log = logging.getLogger(__name__)

@dataclass
class TagGameState:
    """Game state for a single NTAG424 DNA tag."""
    uid: str
    outcome: str = ""  # "heads" or "tails"
    coin_name: str = ""  # Shared identifier for both sides of the coin
    last_counter: int = 0
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())

class IGameStateManager(ABC):
    """Interface for game state persistence."""

    FIELDNAMES: ClassVar[list[str]] = ["uid", "outcome", "coin_name", "last_counter", "last_seen"]

    @abstractmethod
    def get_state(self, uid: str) -> TagGameState:
        pass

    @abstractmethod
    def update_state(self, uid: str, counter: int, outcome: str, coin_name: str = "", cmac: str = ""):
        pass

    @abstractmethod
    def get_totals(self, include_test: bool = False) -> dict[str, int]:
        pass

    @abstractmethod
    def analyze_flip_sequence_randomness(self, include_test: bool = False, uid: str | None = None) -> dict:
        pass


class SqliteGameStateManager(IGameStateManager):
    """Manages game state persistence using SQLite."""

    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def fix_db(self, conn: sqlite3.Connection):
        """Migration: Add coin_name and is_test columns if they don't exist."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(scan_logs)")
        columns = {row[1] for row in cursor.fetchall()}

        if 'coin_name' not in columns:
            cursor.execute("ALTER TABLE scan_logs ADD COLUMN coin_name TEXT DEFAULT ''")
            log.info("[MIGRATION] Added coin_name column to scan_logs")

        if 'is_test' not in columns:
            cursor.execute("ALTER TABLE scan_logs ADD COLUMN is_test BOOLEAN NOT NULL DEFAULT FALSE")
            log.info("[MIGRATION] Added is_test column to scan_logs")

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
                    coin_name TEXT DEFAULT '',
                    is_test BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            # Index for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_uid_counter ON scan_logs (uid, counter)")

            # Add new columns if they don't exist (for backward compatibility)
            self.fix_db(conn)
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
        with self._get_conn() as conn:
            # Get the latest scan for this UID
            cursor = conn.execute(
                "SELECT outcome, counter, timestamp, coin_name FROM scan_logs WHERE uid = ? ORDER BY counter DESC LIMIT 1",
                (uid,)
            )
            row = cursor.fetchone()

            if row:
                return TagGameState(
                    uid=uid,
                    outcome=row[0],
                    last_counter=row[1],
                    last_seen=row[2],
                    coin_name=row[3]
                )
            else:
                return TagGameState(uid=uid)

    def update_state(self, uid: str, counter: int, outcome: str, coin_name: str = "", cmac: str = "", is_test: bool = False):
        """Logs a new scan event to the database.

        Args:
            uid: The UID of the tag scanned.
            counter: The SDM counter value from the scan.
            outcome: The result of the flip (e.g., "heads", "tails").
            coin_name: The name of the coin associated with the tag.
            cmac: The CMAC value from the scan for verification.
            is_test: A boolean flag indicating if the scan is a test event.
        """
        uid = uid.upper()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO scan_logs (uid, counter, outcome, coin_name, cmac, is_test) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, counter, outcome.lower(), coin_name, cmac, is_test)
            )
            conn.commit()

        log_prefix = "[TEST] " if is_test else ""
        log.info(f"{log_prefix}[GAME STATE SQLITE] Logged scan for {uid}: coin='{coin_name}', outcome={outcome.lower()}, ctr={counter}")

    def get_totals(self, include_test: bool = False) -> Dict[str, int]:
        """Get total heads and tails across all unique coins."""
        
        base_query = "SELECT COUNT(*) FROM scan_logs WHERE LOWER(outcome) = ?"
        params = ['heads']

        if not include_test:
            base_query += " AND is_test IS FALSE"
        
        heads = self._query(base_query, tuple(params))[0][0]

        params = ['tails']
        tails = self._query(base_query, tuple(params))[0][0]

        return {"heads": heads, "tails": tails}

    def get_totals_by_coin(self) -> dict[str, dict[str, int]]:
        """Get per-coin statistics showing scan counts for each outcome."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT coin_name, outcome, COUNT(*) as count
                FROM scan_logs
                WHERE coin_name != '' and LOWER(outcome) IN ('heads', 'tails')
                GROUP BY coin_name, outcome
            """)

            coins = {}
            for row in cursor:
                coin_name, outcome, count = row
                if coin_name not in coins:
                    coins[coin_name] = {"heads": 0, "tails": 0}
                coins[coin_name][outcome.lower()] = count

            return coins

    def get_recent_flips(self, limit: int = 88) -> list[dict]:
        # Fetch the most recent scans, ensuring we get the coin_name
        query = "SELECT coin_name, uid, LOWER(outcome), timestamp FROM scan_logs ORDER BY id DESC LIMIT ?"
        rows = self._query(query, (limit,))
        recent_flips = []
        for row in rows:
            coin_name, uid_str, outcome, timestamp = row  # coin_name is row[0]
            recent_flips.append({
                "coin_name": coin_name,
                "asset_tag": UID(uid_str).asset_tag,
                "uid": uid_str,
                "outcome": outcome,
                "timestamp": timestamp
            })
        return recent_flips


    def analyze_flip_sequence_randomness(self, include_test: bool = False, coin_name: str | None = None) -> Dict:
        """Fetches all flip outcomes, converts them to a binary sequence (HEADS=1, TAILS=0),
        and runs randomness tests (Shannon entropy, NIST Monobit).

        Args:
            include_test: If True, includes test data in the analysis.
            coin_name: If provided, analyzes flips only for this coin.

        Returns:
            A dictionary with the analysis results.
        """

        conditions = ["LOWER(outcome) IN ('heads', 'tails')"]
        params = []

        if coin_name:
            conditions.append("coin_name = ?")
            params.append(coin_name.upper())

        if not include_test:
            conditions.append("is_test IS FALSE")

        query = f"SELECT LOWER(outcome) FROM scan_logs WHERE {' AND '.join(conditions)} ORDER BY id ASC"  # noqa: S608

        rows = self._query(query, tuple(params))

        if not rows:
            return {"total_bits": 0, "total_heads": 0, "total_tails": 0, "entropy": 0.0, "nist_monobit_p_value": None, "nist_monobit_passed": None, "error": "No flips to analyze."}

        # Convert sequence to a string of bits
        bit_string = "".join(['1' if row[0] == 'heads' else '0' for row in rows])
        total_bits = len(bit_string)
        total_heads = bit_string.count('1')
        total_tails = bit_string.count('0')

        if total_bits == 0:
            return {"total_bits": 0, "total_heads": 0, "total_tails": 0, "entropy": 0.0, "nist_monobit_p_value": None, "nist_monobit_passed": None, "error": "No flips to analyze."}

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

        # Add extra global stats if not analyzing a specific coin
        extra_stats = {}
        if not coin_name:
            totals = self.get_totals(include_test=include_test)
            
            # Build query to count unique coins
            coin_conditions = ["coin_name IS NOT NULL", "coin_name != ''"]
            coin_params = []
            if not include_test:
                coin_conditions.append("is_test IS FALSE")
            coin_query = f"SELECT COUNT(DISTINCT coin_name) FROM scan_logs WHERE {' AND '.join(coin_conditions)}"
            total_coins_result = self._query(coin_query, tuple(coin_params))
            total_coins = total_coins_result[0][0] if total_coins_result else 0

            extra_stats = {"total_coins": total_coins, "total_heads": totals.get("heads", 0), "total_tails": totals.get("tails", 0)}

        return {"total_bits": total_bits, "total_heads": total_heads, "total_tails": total_tails, "entropy": entropy, "nist_monobit_p_value": p_value, "nist_monobit_passed": passed, "nist_error": error, **extra_stats}

    def get_leaderboard_stats(self, include_test: bool = False) -> list[dict]:
        """Calculates randomness stats for each coin and returns a ranked list.

        Args:
            include_test: If True, includes test data in the analysis.
        """
        # 1. Get all unique coin_names
        conditions = ["coin_name IS NOT NULL", "coin_name != ''"]
        params = []

        if not include_test:
            conditions.append("is_test IS FALSE")
            conditions.append("LOWER(outcome) IN ('heads', 'tails')")

        query = f"SELECT DISTINCT coin_name FROM scan_logs WHERE {' AND '.join(conditions)}"
        results = self._query(query, params)
        coin_names = [row[0] for row in results]

        leaderboard = []
        for coin_name in coin_names:
            # 2. Get stats for each UID
            stats = self.analyze_flip_sequence_randomness(include_test=include_test, coin_name=coin_name)
            if stats and stats.get("total_bits", 0) > 0:
                leaderboard.append({
                    "coin_name": coin_name,
                    **stats
                })

        # 3. Sort by entropy, descending
        leaderboard.sort(key=lambda x: x.get('entropy', 0), reverse=True)
        return leaderboard
