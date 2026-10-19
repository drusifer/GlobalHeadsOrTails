---
name: Arch — Flip Off Challenge
type: architecture
date: 2026-03-26
sprint: Flip Off
---

# Architecture: Flip Off Challenge

## Component Map

```
app.py (index route)
  └── FlipOffService.record_flip(coin_name, timestamp)  ← passive, on every validated flip
  └── FlipOffService.get_active_challenge(coin_name)    ← for result page display

POST /challenge/create  (new route in app.py)
  └── FlipOffService.create_challenge(challenger, challenged, flip_count)

GET /challenge/<id>     (new route, optional detail view)
  └── FlipOffService.get_challenge(id)

index.html
  └── Challenge section (conditional: valid tap + no active challenge)
  └── Active challenge progress bar (if in challenge)
  └── Completed challenge result card (if challenge complete)
```

## New Service: FlipOffService

File: `server/flip_off_service.py`

```python
class FlipOffService:
    def __init__(self, db_path: str): ...

    def create_challenge(
        self, challenger_coin: str, challenged_coin: str, flip_count: int
    ) -> int:
        """Creates a new challenge. Raises if either coin has active challenge, or same coin."""

    def record_flip(self, coin_name: str) -> None:
        """Called after every validated flip. Increments challenge progress.
        When both coins reach flip_count, calculates and records winner."""

    def get_active_challenge(self, coin_name: str) -> dict | None:
        """Returns active challenge data for a coin, or None."""

    def get_challenge(self, challenge_id: int) -> dict | None:
        """Returns full challenge record."""

    def _calculate_winner(self, challenge_id: int) -> None:
        """Queries scan_logs for each coin's N post-challenge flips,
        calculates entropy (H=1/T=0 bit encoding), records winner."""

    def expire_stale_challenges(self, days: int = 7) -> None:
        """Marks challenges older than N days with no progress as 'expired'."""
```

## DB Schema

```sql
CREATE TABLE flip_off_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    baseline_scan_id INTEGER NOT NULL DEFAULT 0,  -- max(scan_logs.id) at challenge creation
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
    completed_at DATETIME
);
```

Flip counting query (for `_calculate_winner`):
```sql
SELECT LOWER(outcome) FROM scan_logs
WHERE coin_name = ? AND timestamp > ? AND is_test IS FALSE
  AND LOWER(outcome) IN ('heads', 'tails')
ORDER BY id ASC
LIMIT ?
```
where `?` = coin_name, challenge.created_at, challenge.flip_count

## app.py Changes

### In `index` route (after `update_state()` success):
```python
from ntag424_sdm_provisioner.server.flip_off_service import FlipOffService

# Passive flip counting (add to create_app init too)
flip_off_service.record_flip(coin_name)

# Pass challenge state to template
active_challenge = flip_off_service.get_active_challenge(coin_name)
```

### New routes:
```python
@app.route("/challenge/create", methods=["POST"])
def challenge_create():
    # challenger_coin from form, challenged_coin from form, flip_count from form
    # Returns redirect to result page

@app.route("/challenge/<int:challenge_id>")
def challenge_detail(challenge_id):
    # Returns challenge status JSON or rendered page
```

## Template Changes (index.html)

Three new conditional sections (always below the existing flip result):

1. **Challenge launcher** — shown when: valid tap, no active challenge, coin in leaderboard
   - Leaderboard selector (excludes own coin)
   - Flip count: 10 / 25 / 50 / 100
   - Submit button: "Start Flip Off"

2. **Active challenge progress** — shown when coin has `pending`/`in_progress` challenge
   - Challenger: N/M flips | Challenged: N/M flips
   - Status badge

3. **Challenge result card** — shown when challenge is `complete`
   - Winner name, both entropy scores (4 dp)
   - Brief explanation: "Higher entropy = more random coin"

## Entropy Calculation

Reuses `calculate_entropy()` from `crypto_primitives.py`.
Bit encoding: HEADS=1, TAILS=0 (same as `analyze_flip_sequence_randomness()`).
Padding to nearest byte before calling `calculate_entropy()` (same pattern).
Compare challenger_entropy vs challenged_entropy to 4 decimal places.
Tie = draw (winner_coin_name = 'DRAW').

## What Does NOT Change

- `SqliteGameStateManager` — no modifications needed
- `CsvKeyManager` — no modifications needed
- Existing CMAC validation flow — no modifications needed
- `scan_logs` table — no schema change needed

## Phase Plan (for Mouse)

- **Phase 1**: `FlipOffService` + DB migration (no UI) + unit tests
- **Phase 2**: app.py integration (routes + passive flip counting) + template sections + tests
