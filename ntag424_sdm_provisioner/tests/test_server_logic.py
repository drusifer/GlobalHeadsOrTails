import pytest
from pathlib import Path
import shutil

from ntag424_sdm_provisioner.server.app import create_app
from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, Outcome, TagKeys, UID


@pytest.fixture
def test_client():
    """Create a test client for the Flask app with a temporary database."""
    temp_dir = Path("test_temp_data")
    temp_dir.mkdir(exist_ok=True)
    db_path = temp_dir / "test_app.db"
    key_csv_path = temp_dir / "test_keys.csv"

    # Clean up old test data
    if db_path.exists():
        db_path.unlink()
    if key_csv_path.exists():
        key_csv_path.unlink()

    # Create a dummy key manager file
    key_manager = CsvKeyManager(csv_path=str(key_csv_path))
    key_manager.save_tag_keys(TagKeys(
        uid=UID("0401000000001A"), outcome=Outcome.HEADS, coin_name="HANDSOME-HERON", picc_master_key="0"*32, app_read_key="0"*32, sdm_mac_key="0"*32
    ))
    key_manager.save_tag_keys(TagKeys(
        uid=UID("0401000000001B"), outcome=Outcome.TAILS, coin_name="HANDSOME-HERON", picc_master_key="0"*32, app_read_key="0"*32, sdm_mac_key="0"*32
    ))
    key_manager.save_tag_keys(TagKeys(
        uid=UID("0402000000002A"), outcome=Outcome.TAILS, coin_name="SWIFT-FALCON", picc_master_key="0"*32, app_read_key="0"*32, sdm_mac_key="0"*32
    ))
    key_manager.save_tag_keys(TagKeys(
        uid=UID("0402000000002B"), outcome=Outcome.TAILS, coin_name="SWIFT-FALCON", picc_master_key="0"*32, app_read_key="0"*32, sdm_mac_key="0"*32
    ))


    app = create_app(key_csv_path=str(key_csv_path), db_path=str(db_path))
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            # Yield the client and the game manager for direct manipulation
            yield client, app.game_manager

    # Teardown: remove the temporary directory
    shutil.rmtree(temp_dir)


def populate_test_data(game_manager: SqliteGameStateManager):
    """Add sample scan data for testing."""
    # Coin 1: HANDSOME-HERON
    game_manager.update_state("0401000000001A", 1, "heads", "HANDSOME-HERON")
    game_manager.update_state("0401000000001B", 1, "tails", "HANDSOME-HERON")
    game_manager.update_state("0401000000001A", 2, "heads", "HANDSOME-HERON")
    game_manager.update_state("0401000000001A", 3, "heads", "HANDSOME-HERON")

    # Coin 2: SWIFT-FALCON
    game_manager.update_state("0402000000002A", 1, "tails", "SWIFT-FALCON")
    game_manager.update_state("0402000000002B", 1, "tails", "SWIFT-FALCON")

    # Unnamed coin
    game_manager.update_state("04030000000003", 1, "heads", "")

    # Test data
    game_manager.update_state("04040000000004", 1, "heads", "TEST-COIN", is_test=True)


def test_get_totals_correctly_counts_flips(test_client):
    """Verify get_totals() counts all flips, not unique coins."""
    client, game_manager = test_client
    populate_test_data(game_manager)

    # Should count all flips, excluding test data by default
    totals = game_manager.get_totals(include_test=False)
    assert totals["heads"] == 4  # 3 from HERON, 1 from unnamed
    assert totals["tails"] == 3  # 1 from HERON, 2 from FALCON

    # Should include test data when requested
    totals_with_test = game_manager.get_totals(include_test=True)
    assert totals_with_test["heads"] == 5
    assert totals_with_test["tails"] == 3


def test_leaderboard_groups_by_coin_name(test_client):
    """Verify leaderboard stats are calculated per coin."""
    client, game_manager = test_client
    populate_test_data(game_manager)

    leaderboard = game_manager.get_leaderboard_stats(include_test=False)

    # Should only include named coins
    assert len(leaderboard) == 2

    heron_stats = next((c for c in leaderboard if c['coin_name'] == 'HANDSOME-HERON'), None)
    falcon_stats = next((c for c in leaderboard if c['coin_name'] == 'SWIFT-FALCON'), None)

    assert heron_stats is not None
    assert falcon_stats is not None

    # Verify stats for HANDSOME-HERON
    assert heron_stats['total_bits'] == 4
    assert heron_stats['total_heads'] == 3
    assert heron_stats['total_tails'] == 1

    # Verify stats for SWIFT-FALCON
    assert falcon_stats['total_bits'] == 2
    assert falcon_stats['total_heads'] == 0
    assert falcon_stats['total_tails'] == 2


def test_global_analysis_returns_correct_aggregates(test_client):
    """Verify the main analysis function returns correct global stats."""
    client, game_manager = test_client
    populate_test_data(game_manager)

    # Analyze without test data
    stats = game_manager.analyze_flip_sequence_randomness(include_test=False)

    assert stats['total_coins'] == 2  # Only counts named coins
    assert stats['total_bits'] == 7   # All non-test flips (4+2+1)
    assert stats['total_heads'] == 4
    assert stats['total_tails'] == 3


def test_api_recent_flips_returns_correct_totals(test_client):
    """Verify the API endpoint for real-time updates returns correct totals."""
    client, game_manager = test_client
    populate_test_data(game_manager)

    response = client.get('/api/recent_flips')
    assert response.status_code == 200
    json_data = response.get_json()

    assert 'totals' in json_data
    assert json_data['totals']['heads'] == 4
    assert json_data['totals']['tails'] == 3

    # Verify with test mode enabled in query
    response_test = client.get('/api/recent_flips?drew_test_outcome=heads')
    json_data_test = response_test.get_json()
    assert json_data_test['totals']['heads'] == 5
    assert json_data_test['totals']['tails'] == 3