"""Unit tests for FlipOffService.

Tests cover: challenge creation, duplicate-challenge guard, same-coin guard,
invalid flip count, flip counting, entropy winner determination, tie handling,
and stale challenge expiry.
"""
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ntag424_sdm_provisioner.server.flip_off_service import FlipOffError, FlipOffService
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager


COIN_A = "HANDSOME-HERON"
COIN_B = "SWIFT-FALCON"
COIN_C = "BRAVE-BEAR"

DB_PATH = Path("test_temp_flipoff") / "flipoff_test.db"


@pytest.fixture
def services():
    """Shared DB with both SqliteGameStateManager and FlipOffService."""
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    gsm = SqliteGameStateManager(db_path=str(DB_PATH))
    fos = FlipOffService(db_path=str(DB_PATH))
    yield gsm, fos

    shutil.rmtree(DB_PATH.parent)


def add_flips(gsm: SqliteGameStateManager, coin: str, outcomes: list[str]) -> None:
    """Helper: insert scan_logs entries for a coin."""
    for i, outcome in enumerate(outcomes, start=1):
        gsm.update_state(f"04{coin[:6].encode().hex()}{i:04x}", i, outcome, coin)


# --- Challenge Creation ---

def test_create_challenge_returns_id(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)
    assert isinstance(cid, int)
    assert cid > 0


def test_create_challenge_stores_correct_fields(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 25)
    challenge = fos.get_challenge(cid)
    assert challenge["challenger_coin_name"] == COIN_A
    assert challenge["challenged_coin_name"] == COIN_B
    assert challenge["flip_count"] == 25
    assert challenge["status"] == "pending"
    assert challenge["challenger_flips_done"] == 0
    assert challenge["challenged_flips_done"] == 0


def test_create_challenge_invalid_flip_count(services):
    _, fos = services
    with pytest.raises(FlipOffError, match="flip_count must be one of"):
        fos.create_challenge(COIN_A, COIN_B, 7)


def test_create_challenge_same_coin_raises(services):
    _, fos = services
    with pytest.raises(FlipOffError, match="cannot challenge itself"):
        fos.create_challenge(COIN_A, COIN_A, 10)


def test_create_challenge_blocks_duplicate_challenger(services):
    _, fos = services
    fos.create_challenge(COIN_A, COIN_B, 10)
    with pytest.raises(FlipOffError, match="already has an active challenge"):
        fos.create_challenge(COIN_A, COIN_C, 10)


def test_create_challenge_blocks_duplicate_challenged(services):
    _, fos = services
    fos.create_challenge(COIN_A, COIN_B, 10)
    with pytest.raises(FlipOffError, match="already has an active challenge"):
        fos.create_challenge(COIN_C, COIN_B, 10)


# --- get_active_challenge ---

def test_get_active_challenge_returns_none_when_no_challenge(services):
    _, fos = services
    assert fos.get_active_challenge(COIN_A) is None


def test_get_active_challenge_returns_for_both_coins(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)
    assert fos.get_active_challenge(COIN_A)["id"] == cid
    assert fos.get_active_challenge(COIN_B)["id"] == cid


# --- Flip Counting ---

def test_record_flip_noop_for_uninvolved_coin(services):
    _, fos = services
    fos.create_challenge(COIN_A, COIN_B, 10)
    fos.record_flip(COIN_C)  # uninvolved — should not raise or change anything
    challenge = fos.get_active_challenge(COIN_A)
    assert challenge["challenger_flips_done"] == 0
    assert challenge["challenged_flips_done"] == 0


def test_record_flip_increments_challenger(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)
    fos.record_flip(COIN_A)
    challenge = fos.get_challenge(cid)
    assert challenge["challenger_flips_done"] == 1
    assert challenge["challenged_flips_done"] == 0
    assert challenge["status"] == "in_progress"


def test_record_flip_increments_challenged(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)
    fos.record_flip(COIN_B)
    challenge = fos.get_challenge(cid)
    assert challenge["challenger_flips_done"] == 0
    assert challenge["challenged_flips_done"] == 1


# --- Winner Determination ---

def _setup_alternating_flips(gsm, coin, n):
    """Add n flips alternating H/T for decent entropy."""
    outcomes = ["heads" if i % 2 == 0 else "tails" for i in range(n)]
    add_flips(gsm, coin, outcomes)


def test_winner_determined_when_both_reach_flip_count(services):
    """When both coins hit flip_count, challenge completes and winner is set."""
    gsm, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)

    _setup_alternating_flips(gsm, COIN_A, 10)
    _setup_alternating_flips(gsm, COIN_B, 10)

    for _ in range(10):
        fos.record_flip(COIN_A)
    for _ in range(10):
        fos.record_flip(COIN_B)

    challenge = fos.get_challenge(cid)
    assert challenge["status"] == "complete"
    assert challenge["winner_coin_name"] is not None
    assert challenge["challenger_entropy"] is not None
    assert challenge["challenged_entropy"] is not None
    assert challenge["completed_at"] is not None


def test_winner_higher_entropy_with_valid_count(services):
    """The coin with higher entropy wins — using valid flip_count=10.

    With 10-bit sequences padded to 16 bits (6 zero pad):
    - COIN_A: 8 heads + 2 tails → padded 8/16 ones = 50/50 → max entropy
    - COIN_B: all tails → padded 0/16 ones = zero entropy
    """
    gsm, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)

    # COIN_A: 8 heads + 2 tails → padded ratio 8/16 = 50/50 → maximum entropy
    add_flips(gsm, COIN_A, ["heads"] * 8 + ["tails"] * 2)
    # COIN_B: all tails → padded ratio 0/16 = 0 → zero entropy
    add_flips(gsm, COIN_B, ["tails"] * 10)

    for _ in range(10):
        fos.record_flip(COIN_A)
    for _ in range(10):
        fos.record_flip(COIN_B)

    challenge = fos.get_challenge(cid)
    assert challenge["status"] == "complete"
    assert challenge["winner_coin_name"] == COIN_A
    assert challenge["challenger_entropy"] > challenge["challenged_entropy"]


def test_tie_recorded_as_draw(services):
    """Identical entropy sequences result in a DRAW."""
    gsm, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)

    # Identical sequences → identical entropy
    outcomes = ["heads", "tails"] * 5
    add_flips(gsm, COIN_A, outcomes)
    add_flips(gsm, COIN_B, outcomes)

    for _ in range(10):
        fos.record_flip(COIN_A)
    for _ in range(10):
        fos.record_flip(COIN_B)

    challenge = fos.get_challenge(cid)
    assert challenge["status"] == "complete"
    assert challenge["winner_coin_name"] == "DRAW"


def test_challenge_not_completed_until_both_reach_count(services):
    """Challenge stays in_progress until BOTH coins reach flip_count."""
    gsm, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)
    add_flips(gsm, COIN_A, ["heads"] * 10)

    for _ in range(10):
        fos.record_flip(COIN_A)

    challenge = fos.get_challenge(cid)
    assert challenge["status"] == "in_progress"  # B hasn't flipped yet
    assert challenge["winner_coin_name"] is None


# --- Expiry ---

def test_expire_stale_challenges_marks_old_as_expired(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)

    # Backdate created_at to 25 hours ago (beyond 24h expiry window)
    import sqlite3
    cutoff = (datetime.utcnow() - timedelta(hours=25)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE flip_off_challenges SET created_at = ? WHERE id = ?", (cutoff, cid))
        conn.commit()

    expired = fos.expire_stale_challenges(hours=24)
    assert len(expired) == 1
    assert expired[0]["id"] == cid
    assert fos.get_challenge(cid)["status"] == "expired"


def test_expire_stale_challenges_leaves_recent_intact(services):
    _, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)

    expired = fos.expire_stale_challenges(hours=24)
    assert len(expired) == 0
    assert fos.get_challenge(cid)["status"] == "pending"


def test_expire_does_not_affect_complete_challenges(services):
    gsm, fos = services
    cid = fos.create_challenge(COIN_A, COIN_B, 10)

    add_flips(gsm, COIN_A, ["heads", "tails"] * 5)
    add_flips(gsm, COIN_B, ["heads", "tails"] * 5)
    for _ in range(10):
        fos.record_flip(COIN_A)
    for _ in range(10):
        fos.record_flip(COIN_B)

    assert fos.get_challenge(cid)["status"] == "complete"
    expired = fos.expire_stale_challenges(hours=0)  # expire everything pending
    assert fos.get_challenge(cid)["status"] == "complete"  # unchanged
    assert all(e["id"] != cid for e in expired)
