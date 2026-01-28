from unittest.mock import patch

import pytest

# No path hacking needed if running via python -m pytest from root
# But we need to import from the package
from ntag424_sdm_provisioner.server.app import app
from ntag424_sdm_provisioner.server.game_state_manager import TagGameState


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_managers():
    with patch('ntag424_sdm_provisioner.server.app.key_manager') as mock_km, \
         patch('ntag424_sdm_provisioner.server.app.game_manager') as mock_gm:
        yield mock_km, mock_gm

def test_missing_params(client):
    """Test that missing parameters return an error."""
    response = client.get('/')
    assert b"Missing Parameters" in response.data

def test_valid_request(client, mock_managers):
    """Test a valid request flow."""
    mock_km, mock_gm = mock_managers
    
    # Mock Key Manager Validation
    mock_km.validate_sdm_url.return_value = {
        "valid": True, 
        "uid": "048E684A2F7080", 
        "counter": 28
    }
    
    # Mock Game State (First time, outcome empty)
    mock_gm.get_state.return_value = TagGameState(uid="048E684A2F7080", last_counter=0)
    
    # Request
    uid = "048E684A2F7080"
    ctr = "1C" # 28
    cmac = "9F5430D0B4ACB13A"
    response = client.get(f'/?uid={uid}&ctr={ctr}&cmac={cmac}')
    
    # Verification
    assert response.status_code == 200
    assert b"Heads" in response.data or b"Tails" in response.data
    
    # Verify State Update Called
    mock_gm.update_state.assert_called_once()
    args = mock_gm.update_state.call_args
    assert args[0][0] == uid
    assert args[0][1] == 28 # Counter int

def test_replay_attack(client, mock_managers):
    """Test that reusing a counter fails."""
    mock_km, mock_gm = mock_managers

    # Mock Validation (still valid crypto)
    mock_km.validate_sdm_url.return_value = {"valid": True}

    # Mock State (Already saw counter 100)
    mock_gm.get_state.return_value = TagGameState(
        uid="04AE664A2F7080",
        last_counter=100,
        outcome="Heads"
    )

    # Request with OLD counter (100 -> 0x64)
    response = client.get('/?uid=04AE664A2F7080&ctr=64&cmac=SIG')

    assert b"Replay Detected" in response.data
    assert b"Heads" in response.data # Shows previous outcome

    # Verify NO update
    mock_gm.update_state.assert_not_called()

def test_invalid_cmac(client, mock_managers):
    """Test that invalid CMAC is rejected."""
    mock_km, _mock_gm = mock_managers

    mock_km.validate_sdm_url.return_value = {"valid": False}

    response = client.get('/?uid=04AE664A2F7080&ctr=1&cmac=BAD')

    assert b"CMAC Verification Failed" in response.data


# --- Coin Naming Tests ---

def test_coin_name_in_tag_game_state():
    """TagGameState should include coin_name field."""
    state = TagGameState(
        uid="049120E2151990",
        outcome="tails",
        last_counter=5,
        coin_name="HANDSOME-HERON-201"
    )
    assert state.coin_name == "HANDSOME-HERON-201"


def test_game_manager_stores_coin_name(tmp_path):
    """Game manager should persist coin_name in scan_logs."""
    from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager

    db_file = tmp_path / "test.db"
    manager = SqliteGameStateManager(db_path=str(db_file))

    # Update state with coin_name
    manager.update_state(
        uid="049120E2151990",
        counter=1,
        outcome="tails",
        coin_name="HANDSOME-HERON-201",
        cmac="ABC123"
    )

    # Retrieve state
    state = manager.get_state("049120E2151990")
    assert state.coin_name == "HANDSOME-HERON-201"
    assert state.outcome == "tails"


def test_get_totals_counts_unique_coins(tmp_path):
    """get_totals() should count unique coins, not individual scans."""
    from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager

    db_file = tmp_path / "test.db"
    manager = SqliteGameStateManager(db_path=str(db_file))

    # Scan coin 1 (heads) twice
    manager.update_state("UID1", 1, "heads", coin_name="COIN-A", cmac="X")
    manager.update_state("UID1", 2, "heads", coin_name="COIN-A", cmac="Y")

    # Scan coin 1 (tails) once
    manager.update_state("UID2", 1, "tails", coin_name="COIN-A", cmac="Z")

    # Scan coin 2 (heads) once
    manager.update_state("UID3", 1, "heads", coin_name="COIN-B", cmac="W")

    # Should count: COIN-A (1 heads + 1 tails), COIN-B (1 heads)
    # Total: 2 heads coins, 1 tails coin
    totals = manager.get_totals()

    assert totals["heads"] == 2  # COIN-A heads, COIN-B heads
    assert totals["tails"] == 1  # COIN-A tails


def test_get_totals_by_coin_aggregates_correctly(tmp_path):
    """get_totals_by_coin() should return per-coin statistics."""
    from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager

    db_file = tmp_path / "test.db"
    manager = SqliteGameStateManager(db_path=str(db_file))

    # Coin A: 3 heads scans, 2 tails scans
    manager.update_state("UID1", 1, "heads", coin_name="COIN-A", cmac="1")
    manager.update_state("UID1", 2, "heads", coin_name="COIN-A", cmac="2")
    manager.update_state("UID1", 3, "heads", coin_name="COIN-A", cmac="3")
    manager.update_state("UID2", 1, "tails", coin_name="COIN-A", cmac="4")
    manager.update_state("UID2", 2, "tails", coin_name="COIN-A", cmac="5")

    # Coin B: 1 heads scan
    manager.update_state("UID3", 1, "heads", coin_name="COIN-B", cmac="6")

    by_coin = manager.get_totals_by_coin()

    assert by_coin["COIN-A"]["heads"] == 3
    assert by_coin["COIN-A"]["tails"] == 2
    assert by_coin["COIN-B"]["heads"] == 1
    assert by_coin["COIN-B"]["tails"] == 0


def test_app_passes_coin_name_to_game_manager(client, mock_managers):
    """App should retrieve coin_name from key_manager and pass to game_manager."""
    from ntag424_sdm_provisioner.csv_key_manager import Outcome, TagKeys
    from ntag424_sdm_provisioner.uid_utils import UID

    mock_km, mock_gm = mock_managers

    # Mock key manager to return tag_keys with coin_name
    mock_km.validate_sdm_url.return_value = {"valid": True}
    mock_km.get_tag_keys.return_value = TagKeys(
        uid=UID("049120E2151990"),
        picc_master_key="abc123",
        app_read_key="def456",
        sdm_mac_key="ghi789",
        provisioned_date="2026-01-08",
        status="provisioned",
        outcome=Outcome.TAILS,
        coin_name="HANDSOME-HERON-201"
    )

    # Mock game state
    mock_gm.get_state.return_value = TagGameState(
        uid="049120E2151990",
        last_counter=0,
        coin_name="HANDSOME-HERON-201"
    )

    # Request
    _response = client.get('/?uid=049120E2151990&ctr=1&cmac=ABC')

    # Verify update_state called with coin_name
    mock_gm.update_state.assert_called_once()
    args = mock_gm.update_state.call_args
    # Should include coin_name parameter
    assert args[1].get("coin_name") == "HANDSOME-HERON-201"


# --- Counter Validation Per-Tag Tests ---

def test_counter_validation_is_per_tag_not_per_coin(tmp_path):
    """
    CRITICAL: Counter validation must be per-tag (UID), not per-coin.

    Coins have 2 tags (HEADS + TAILS). Each tag has its own counter.
    If counter validation was per-coin, scanning the TAILS tag would fail
    after scanning the HEADS tag with a higher counter.

    This test proves: Counter check uses the specific tag's UID, not coin_name.
    """
    from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager

    db_file = tmp_path / "test.db"
    manager = SqliteGameStateManager(db_path=str(db_file))

    # Same coin, two different tags (HEADS and TAILS)
    COIN_NAME = "TEST-COIN-001"
    HEADS_UID = "04HEADS0001"
    TAILS_UID = "04TAILS0001"

    # Scan HEADS tag with counter=100
    manager.update_state(HEADS_UID, 100, "heads", coin_name=COIN_NAME, cmac="MAC1")

    # Get state for TAILS tag (should be independent of HEADS)
    tails_state = manager.get_state(TAILS_UID)

    # CRITICAL ASSERTION: TAILS tag should have its own counter (0), not HEADS' counter (100)
    assert tails_state.last_counter == 0, (
        f"TAILS tag counter should be 0 (first scan), not {tails_state.last_counter}. "
        "Counter validation must be per-tag (UID), not per-coin!"
    )

    # Now scan TAILS with counter=5 (lower than HEADS' 100, but valid for TAILS)
    manager.update_state(TAILS_UID, 5, "tails", coin_name=COIN_NAME, cmac="MAC2")

    # Verify TAILS scan succeeded (counter is now 5)
    tails_state_after = manager.get_state(TAILS_UID)
    assert tails_state_after.last_counter == 5, "TAILS scan should succeed with counter=5"

    # Verify HEADS counter is still 100 (independent)
    heads_state = manager.get_state(HEADS_UID)
    assert heads_state.last_counter == 100, "HEADS counter should remain 100"


def test_replay_detection_is_per_tag(tmp_path):
    """
    Replay detection must reject reused counters only for the SAME tag.

    Scanning TAILS tag with counter=5 after HEADS had counter=100
    should NOT trigger replay detection.
    """
    from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager

    db_file = tmp_path / "test.db"
    manager = SqliteGameStateManager(db_path=str(db_file))

    COIN_NAME = "REPLAY-TEST-COIN"
    HEADS_UID = "04REPLAYH001"
    TAILS_UID = "04REPLAYT001"

    # Scan HEADS with counter=50
    manager.update_state(HEADS_UID, 50, "heads", coin_name=COIN_NAME, cmac="M1")

    # Get TAILS state - should be fresh (counter=0)
    tails_state = manager.get_state(TAILS_UID)

    # Simulate replay check for TAILS with counter=10
    new_counter = 10
    is_replay = new_counter <= tails_state.last_counter

    assert is_replay is False, (
        f"Counter {new_counter} should NOT be a replay for TAILS (last_counter={tails_state.last_counter}). "
        "Replay check must be per-tag, not per-coin!"
    )

    # Now simulate actual replay for TAILS (counter 10 seen, try 5)
    manager.update_state(TAILS_UID, 10, "tails", coin_name=COIN_NAME, cmac="M2")
    tails_state_after = manager.get_state(TAILS_UID)

    replay_counter = 5
    is_actual_replay = replay_counter <= tails_state_after.last_counter

    assert is_actual_replay is True, "Counter 5 should be a replay for TAILS (last_counter=10)"
