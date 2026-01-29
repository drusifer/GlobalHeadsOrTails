import pytest
from unittest.mock import patch, MagicMock

from ntag424_sdm_provisioner.server.app import app, init_managers
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys, Outcome
from ntag424_sdm_provisioner.uid_utils import UID

@pytest.fixture
def integration_client(tmp_path):
    key_file = tmp_path / "keys.csv"
    db_file = tmp_path / "app.db"
    
    with open(key_file, "w") as f:
        f.write("uid,picc_master_key,app_read_key,sdm_mac_key,outcome,coin_name,provisioned_date,status,notes,last_used_date\n")

    app.config['TESTING'] = True
    init_managers(app, str(key_file), str(db_file))
    
    with app.test_client() as client:
        yield client

def test_full_flow_with_real_managers(integration_client, tmp_path):
    """
    This is an integration test that uses the real CsvKeyManager and SqliteGameStateManager.
    """
    # 1. Setup: Get the real managers from the app
    key_manager = app.key_manager
    game_manager = app.game_manager

    # 2. Setup: Create a test tag in the key manager
    uid_str = "04112233445566"
    uid = UID(uid_str)
    coin_name = "TEST-COIN"
    tag_keys = TagKeys.from_factory_keys(uid)
    tag_keys.coin_name = coin_name
    tag_keys.outcome = Outcome.HEADS
    key_manager.save_tag_keys(tag_keys)

    # 3. Action: Simulate a valid request
    with patch.object(key_manager, 'validate_sdm_url', return_value={'valid': True}):
        response = integration_client.get(f'/?uid={uid_str}&ctr=1&cmac=ABC')

    # 4. Assertions
    assert response.status_code == 200
    assert b"TEST-COIN" in response.data
    assert b"HEADS" in response.data

    # Check the database directly
    state = game_manager.get_state(uid_str)
    assert state.coin_name == coin_name
    assert state.outcome == "heads"
    assert state.last_counter == 1
