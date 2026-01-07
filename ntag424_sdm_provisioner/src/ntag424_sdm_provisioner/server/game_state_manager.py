import csv
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

log = logging.getLogger(__name__)

@dataclass
class TagGameState:
    """Game state for a single NTAG424 DNA tag."""
    uid: str
    outcome: str = ""  # "heads" or "tails"
    last_counter: int = 0
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())

class GameStateManager:
    """Manages game state persistence for tags."""

    FIELDNAMES = ["uid", "outcome", "last_counter", "last_seen"]

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
        if self.csv_path.exists():
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f, fieldnames=self.FIELDNAMES)
                try:
                    next(reader) # Skip header if reading manually, but DictReader handles it if we don't pass fieldnames or if we do?
                    # DictReader reads header automatically if fieldnames is None.
                    # If fieldnames IS passed, it assumes first row is data unless we skip?
                    # Wait, standard DictReader behavior:
                    # If fieldnames is omitted, first row is header.
                    # If fieldnames is provided, first row IS data.
                    # Let's re-read carefully.
                    pass 
                except StopIteration:
                    pass

            # Let's just read it safely
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f) # Infer headers
                for row in reader:
                    if row["uid"].upper() == uid:
                        return TagGameState(
                            uid=row["uid"],
                            outcome=row.get("outcome", ""),
                            last_counter=int(row.get("last_counter", 0)),
                            last_seen=row.get("last_seen", "")
                        )
        
        return TagGameState(uid=uid)

    def update_state(self, uid: str, counter: int, outcome: str):
        """Update state for a UID."""
        uid = uid.upper()
        
        # Read all states
        states: Dict[str, TagGameState] = {}
        if self.csv_path.exists():
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    states[row["uid"].upper()] = TagGameState(
                        uid=row["uid"],
                        outcome=row.get("outcome", ""),
                        last_counter=int(row.get("last_counter", 0)),
                        last_seen=row.get("last_seen", "")
                    )

        # Update specific state
        states[uid] = TagGameState(
            uid=uid,
            outcome=outcome,
            last_counter=counter,
            last_seen=datetime.now().isoformat()
        )

        # Write all back
        with self.csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for state in states.values():
                writer.writerow(asdict(state))
        
        log.info(f"[GAME STATE] Updated state for {uid}: outcome={outcome}, ctr={counter}")
