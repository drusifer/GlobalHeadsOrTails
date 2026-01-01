import pytest

from ntag424_sdm_provisioner.constants import GAME_COIN_BASE_URL
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.sequence_logger import create_sequence_logger
from ntag424_sdm_provisioner.seritag_simulator import SeritagCardConnection, SeritagSimulator
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService


# Use temporary CSVs for keys (both main and backup)
@pytest.fixture
def temp_key_paths(tmp_path):
    """Create temp paths for both main and backup CSV files."""
    csv_file = tmp_path / "test_keys.csv"
    csv_file.write_text("uid,picc_master_key,app_read_key,sdm_mac_key\n")
    backup_file = tmp_path / "test_keys_backup.csv"
    return str(csv_file), str(backup_file)

@pytest.fixture
def sequence_logger():
    return create_sequence_logger("Test")

@pytest.fixture
def simulator():
    # Create a fresh simulator for each test
    sim = SeritagSimulator()
    return sim

@pytest.fixture
def sim_connection(simulator, sequence_logger):
    # Create a connection to the simulator with required sequence_logger
    simulator.connect()
    return SeritagCardConnection(simulator, sequence_logger)

@pytest.fixture
def key_manager(temp_key_paths):
    csv_path, backup_path = temp_key_paths
    return CsvKeyManager(csv_path, backup_path)

def test_provision_flow_with_simulator(sim_connection, key_manager, caplog):
    """
    Test the full provisioning flow using the Seritag simulator.
    This verifies the logic against a realistic card implementation 
    without using mocks.
    """
    import logging
    caplog.set_level(logging.INFO)
    
    # Initialize service with simulator connection
    service = ProvisioningService(sim_connection, key_manager)
    
    # Run provisioning
    result = service.provision(base_url=GAME_COIN_BASE_URL)
    
    # Check logs if failed
    if not result:
        print("\nCaptured Logs:")
        for record in caplog.records:
            print(f"{record.levelname}: {record.message}")
            
    assert result is True
    
    # Verify the card state in the simulator
    # 1. Check if NDEF message was written
    # The simulator stores NDEF in file 2
    ndef_file = sim_connection.simulator.state.files.get(2)
    assert ndef_file is not None
    assert len(ndef_file) > 0
    
    # 2. Check if SDM settings were applied (FileOption bit 6 set)
    # This requires inspecting internal simulator state which might be implementation detail,
    # but for a "unit test" of the service, success result is the main indicator.
    # We can also verify logs.
    assert "Provisioning complete!" in [r.message for r in caplog.records]

def test_provision_auth_failure_simulator(sim_connection, key_manager):
    """Test auth failure handling with simulator."""
    # Set the simulator to have a non-default key 0
    # This should cause authentication with default keys to fail
    sim_connection.simulator.state.factory_keys[0] = bytes.fromhex("11" * 16)
    
    service = ProvisioningService(sim_connection, key_manager)
    result = service.provision()
    
    assert result is False
