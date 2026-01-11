import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        uid="TEST_UID", 
        last_counter=100, 
        outcome="Heads"
    )
    
    # Request with OLD counter (100 -> 0x64)
    response = client.get('/?uid=TEST_UID&ctr=64&cmac=SIG')
    
    assert b"Replay Detected" in response.data
    assert b"Heads" in response.data # Shows previous outcome
    
    # Verify NO update
    mock_gm.update_state.assert_not_called()

def test_invalid_cmac(client, mock_managers):
    """Test that invalid CMAC is rejected."""
    mock_km, mock_gm = mock_managers
    
    mock_km.validate_sdm_url.return_value = {"valid": False}
    
    response = client.get('/?uid=UID&ctr=1&cmac=BAD')
    
    assert b"CMAC Verification Failed" in response.data
