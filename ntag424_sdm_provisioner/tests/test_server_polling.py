"""Tests for polling endpoints: GET /api/flips/since and GET /api/state.

Verifies the two-endpoint polling protocol that replaced SSE:
  /api/flips/since?ts=<iso>  → {"has_new": bool}
  /api/state?since=<iso>     → full state snapshot
"""
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, Outcome, TagKeys, UID
from ntag424_sdm_provisioner.server.app import create_app


COIN_A = "HAPPY-HAWK-001"
UID_A_HEADS = "0401000000001A"
UID_A_TAILS = "0401000000001B"
COIN_B = "SWIFT-FALCON"
UID_B = "0402000000002A"


@pytest.fixture
def app_ctx(tmp_path):
    db_path = tmp_path / "test.db"
    key_csv = tmp_path / "keys.csv"
    km = CsvKeyManager(csv_path=str(key_csv))
    for uid, outcome, coin in [
        (UID_A_HEADS, Outcome.HEADS, COIN_A),
        (UID_A_TAILS, Outcome.TAILS, COIN_A),
        (UID_B,       Outcome.TAILS, COIN_B),
    ]:
        km.save_tag_keys(TagKeys(
            uid=UID(uid), outcome=outcome, coin_name=coin,
            picc_master_key="0" * 32, app_read_key="0" * 32, sdm_mac_key="0" * 32,
        ))
    app = create_app(key_csv_path=str(key_csv), db_path=str(db_path))
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client, app.game_manager, app.flip_off_service


def tap(client, uid: str, ctr: int, outcome: str):
    return client.get(f"/api/flip?uid={uid}&ctr={ctr:08x}&cmac=DEAD&drew_test_outcome={outcome}")


# ---------------------------------------------------------------------------
# /api/flips/since
# ---------------------------------------------------------------------------

def test_flips_since_no_ts_returns_has_new_true(app_ctx):
    """Omitting ts means 'give me everything' — always has_new=True."""
    client, _, _ = app_ctx
    resp = client.get("/api/flips/since")
    assert resp.status_code == 200
    assert resp.get_json()["has_new"] is True


def test_flips_since_future_ts_returns_false_when_no_flip(app_ctx):
    """A timestamp in the future means no flip has occurred after it."""
    client, _, _ = app_ctx
    future = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    resp = client.get(f"/api/flips/since?ts={future}")
    assert resp.status_code == 200
    assert resp.get_json()["has_new"] is False


def test_flips_since_returns_true_after_new_flip(app_ctx):
    """After recording a flip, has_new=True for a timestamp before the flip."""
    client, _, _ = app_ctx
    before = (datetime.utcnow() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    tap(client, UID_A_HEADS, 1, "heads")
    resp = client.get(f"/api/flips/since?ts={before}")
    assert resp.status_code == 200
    assert resp.get_json()["has_new"] is True


def test_flips_since_returns_false_when_no_newer_flip(app_ctx):
    """ts after the last flip means nothing new."""
    client, _, _ = app_ctx
    tap(client, UID_A_HEADS, 1, "heads")
    after = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    resp = client.get(f"/api/flips/since?ts={after}")
    assert resp.status_code == 200
    assert resp.get_json()["has_new"] is False


# ---------------------------------------------------------------------------
# /api/state
# ---------------------------------------------------------------------------

def test_api_state_returns_expected_shape(app_ctx):
    """Response must have all required keys."""
    client, _, _ = app_ctx
    resp = client.get("/api/state")
    assert resp.status_code == 200
    data = resp.get_json()
    for key in ("recent_flips", "totals", "active_challenges", "recent_completed",
                "latest_flip", "just_completed", "latest_timestamp"):
        assert key in data, f"missing key: {key}"


def test_api_state_latest_flip_matches_most_recent(app_ctx):
    """latest_flip and latest_timestamp reflect the most recent recorded flip."""
    client, _, _ = app_ctx
    tap(client, UID_A_HEADS, 1, "heads")
    resp = client.get("/api/state")
    data = resp.get_json()
    assert data["latest_flip"] is not None
    assert data["latest_flip"]["outcome"] == "heads"
    assert data["latest_timestamp"] == data["latest_flip"]["timestamp"]


def test_api_state_totals_reflect_flips(app_ctx):
    """totals.heads increments after a heads tap (include_test so test taps are counted)."""
    client, _, _ = app_ctx
    tap(client, UID_A_HEADS, 1, "heads")
    tap(client, UID_A_TAILS, 2, "tails")
    resp = client.get("/api/state?drew_test_outcome=heads")
    totals = resp.get_json()["totals"]
    assert totals["heads"] >= 1
    assert totals["tails"] >= 1


def test_api_state_empty_latest_timestamp_when_no_flips(app_ctx):
    """No flips recorded → latest_timestamp is empty string."""
    client, _, _ = app_ctx
    resp = client.get("/api/state")
    data = resp.get_json()
    assert data["latest_timestamp"] == ""
    assert data["latest_flip"] is None


def test_api_state_just_completed_populated_via_since(app_ctx):
    """since param causes just_completed to list challenges completed after that ts."""
    client, _, flip_off_service = app_ctx
    # Create a challenge and manually complete it
    cid = flip_off_service.create_challenge(COIN_A, COIN_B, 10)
    before = (datetime.utcnow() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    # Complete the challenge by directly calling _calculate_winner via enough flips
    # Use low-level update to set it complete
    from ntag424_sdm_provisioner.server.flip_off_service import FlipOffService
    with flip_off_service._get_conn() as conn:
        conn.execute(
            "UPDATE flip_off_challenges SET status='complete', winner_coin_name=?, "
            "completed_at=CURRENT_TIMESTAMP, end_condition='win' WHERE id=?",
            (COIN_A, cid),
        )
        conn.commit()
    resp = client.get(f"/api/state?since={before}")
    data = resp.get_json()
    assert any(c["id"] == cid for c in data["just_completed"])


def test_api_state_just_completed_empty_without_since(app_ctx):
    """Without since param, just_completed is always empty."""
    client, _, _ = app_ctx
    resp = client.get("/api/state")
    assert resp.get_json()["just_completed"] == []


# ---------------------------------------------------------------------------
# yield triggers poll
# ---------------------------------------------------------------------------

def test_flips_since_returns_true_after_yield_with_no_new_flip(app_ctx):
    """A yield completes a challenge; has_new must be True for clients that last saw
    a timestamp before the yield — even if no flip has been recorded since."""
    client, _, flip_off_service = app_ctx
    tap(client, UID_A_HEADS, 1, "heads")
    tap(client, UID_B, 2, "tails")
    cid = flip_off_service.create_challenge(COIN_A, COIN_B, 10)

    # ts is 1 second in the future — flips are before this, so has_flip_since=False
    ts = (datetime.utcnow() + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    # completed_at is 2 seconds in the future — strictly after ts
    completed_at = (datetime.utcnow() + timedelta(seconds=2)).strftime("%Y-%m-%d %H:%M:%S")

    # Precondition: nothing new after ts yet
    resp = client.get(f"/api/flips/since?ts={ts}")
    assert resp.get_json()["has_new"] is False, "precondition failed: expected no new events"

    # Simulate a yield by writing completed_at explicitly after ts
    with flip_off_service._get_conn() as conn:
        conn.execute(
            "UPDATE flip_off_challenges SET status='complete', winner_coin_name=?, "
            "completed_at=?, end_condition='yield' WHERE id=?",
            (COIN_B, completed_at, cid),
        )
        conn.commit()

    # Poll must now return True — yield's completed_at is after ts
    resp = client.get(f"/api/flips/since?ts={ts}")
    assert resp.get_json()["has_new"] is True


def test_flips_since_yield_before_ts_is_not_new(app_ctx):
    """A yield that completed before the client's ts must not trigger has_new."""
    client, _, flip_off_service = app_ctx
    tap(client, UID_A_HEADS, 1, "heads")
    tap(client, UID_B, 2, "tails")
    flip_off_service.create_challenge(COIN_A, COIN_B, 10)
    client.post("/challenge/yield", data={"coin_name": COIN_A})

    # ts is 1 second after everything — no flip or yield is newer than this
    after_all = (datetime.utcnow() + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    resp = client.get(f"/api/flips/since?ts={after_all}")
    assert resp.get_json()["has_new"] is False
