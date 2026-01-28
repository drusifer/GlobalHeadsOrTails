import csv
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


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

    @abstractmethod
    def get_state(self, uid: str) -> TagGameState:
        pass

    @abstractmethod
    def update_state(self, uid: str, counter: int, outcome: str, coin_name: str = "", cmac: str = ""):
        pass

    @abstractmethod
    def get_totals(self) -> dict[str, int]:
        pass

class CsvGameStateManager(IGameStateManager):
    """Manages game state persistence for tags using CSV (Legacy)."""

    FIELDNAMES = ["uid", "outcome", "coin_name", "last_counter", "last_seen"]

    def __init__(self, csv_path: str = "data/game_state.csv"):
        self.csv_path = Path(csv_path)
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_path.parent.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            log.info(f"[GAME STATE] Created new game state database: {self.csv_path}")

    def get_state(self, uid: str) -> TagGameState:
        """Get game state for a UID, or create default if not found."""
        uid = uid.upper()

        # Simple linear scan (fine for small CSVs)
        if self.csv_path.exists():
            with self.csv_path.open(newline="") as f:
                # If fieldnames is omitted, the first row of the file is used as the header
                reader = csv.DictReader(f)
                for row in reader:
                    if row["uid"].upper() == uid:
                        return TagGameState(
                            uid=row["uid"],
                            outcome=row.get("outcome", ""),
                            coin_name=row.get("coin_name", ""),
                            last_counter=int(row.get("last_counter", 0)),
                            last_seen=row.get("last_seen", "")
                        )

        return TagGameState(uid=uid)

    def update_state(self, uid: str, counter: int, outcome: str, coin_name: str = "", cmac: str = ""):
        """Update state for a UID."""
        uid = uid.upper()

        # Read all states
        states: dict[str, TagGameState] = {}
        if self.csv_path.exists():
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    states[row["uid"].upper()] = TagGameState(
                        uid=row["uid"],
                        outcome=row.get("outcome", ""),
                        coin_name=row.get("coin_name", ""),
                        last_counter=int(row.get("last_counter", 0)),
                        last_seen=row.get("last_seen", "")
                    )

        # Update specific state
        states[uid] = TagGameState(
            uid=uid,
            outcome=outcome,
            coin_name=coin_name,
            last_counter=counter,
            last_seen=datetime.now().isoformat()
        )

        # Write all back
        with self.csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for state in states.values():
                writer.writerow(asdict(state))

        log.info(f"[GAME STATE] Updated state for {uid}: coin={coin_name}, outcome={outcome}, ctr={counter}")

    def get_totals(self) -> dict[str, int]:
        """Calculate totals from current state snapshot."""
        heads = 0
        tails = 0
        if self.csv_path.exists():
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    o = row.get("outcome", "").lower()
                    if o == "heads":
                        heads += 1
                    elif o == "tails":
                        tails += 1
        return {"heads": heads, "tails": tails}


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
                    coin_name TEXT DEFAULT ''
                )
            """)
            # Index for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_uid_counter ON scan_logs (uid, counter)")

            # Migration: Add coin_name column if it doesn't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE scan_logs ADD COLUMN coin_name TEXT DEFAULT ''")
                log.info("[MIGRATION] Added coin_name column to scan_logs")
            except sqlite3.OperationalError:
                # Column already exists
                pass

            conn.commit()

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
                    coin_name=row[3] if len(row) > 3 else "",
                    last_counter=row[1],
                    last_seen=row[2]
                )
            else:
                return TagGameState(uid=uid)

    def update_state(self, uid: str, counter: int, outcome: str, coin_name: str = "", cmac: str = ""):
        uid = uid.upper()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO scan_logs (uid, counter, outcome, coin_name, cmac) VALUES (?, ?, ?, ?, ?)",
                (uid, counter, outcome, coin_name, cmac)
            )
            conn.commit()
        log.info(f"[GAME STATE SQLITE] Logged scan for {uid}: coin={coin_name}, outcome={outcome}, ctr={counter}")

    def get_totals(self) -> dict[str, int]:
        """Count unique coins by outcome, not individual scans."""
        with self._get_conn() as conn:
            # Count distinct coin_names for each outcome
            # A coin counts as "heads" if it has any heads scans
            # A coin counts as "tails" if it has any tails scans
            heads = conn.execute(
                "SELECT COUNT(DISTINCT coin_name) FROM scan_logs WHERE outcome = 'heads' AND coin_name != ''"
            ).fetchone()[0]
            tails = conn.execute(
                "SELECT COUNT(DISTINCT coin_name) FROM scan_logs WHERE outcome = 'tails' AND coin_name != ''"
            ).fetchone()[0]
            return {"heads": heads, "tails": tails}

    def get_totals_by_coin(self) -> dict[str, dict[str, int]]:
        """Get per-coin statistics showing scan counts for each outcome."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT coin_name, outcome, COUNT(*) as count
                FROM scan_logs
                WHERE coin_name != ''
                GROUP BY coin_name, outcome
            """)

            coins = {}
            for row in cursor:
                coin_name, outcome, count = row
                if coin_name not in coins:
                    coins[coin_name] = {"heads": 0, "tails": 0}
                coins[coin_name][outcome] = count

            return coins
