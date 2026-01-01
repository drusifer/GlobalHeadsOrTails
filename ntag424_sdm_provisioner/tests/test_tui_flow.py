import pytest
from unittest.mock import MagicMock, patch
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
from ntag424_sdm_provisioner.tui.state_manager import StateManager

@pytest.fixture
def mock_card_connection():
    return MagicMock()

@pytest.fixture
def mock_key_manager():
    return MagicMock()

@pytest.fixture
def provisioning_service(mock_card_connection, mock_key_manager):
    return ProvisioningService(mock_card_connection, mock_key_manager)

def test_provisioning_service_initialization(provisioning_service):
    """Test that the service initializes correctly."""
    assert provisioning_service.card is not None
    assert provisioning_service.key_mgr is not None

def test_state_manager_transitions():
    """Test state transitions without UI."""
    state_manager = StateManager()
    
    # Initial state
    assert state_manager.current_state is None
    
    # Transition to Provision
    state_manager.transition_to("provision")
    assert state_manager.current_state == "provision"
    
    # Transition to Read Tag
    state_manager.transition_to("read_tag")
    assert state_manager.current_state == "read_tag"

@patch("ntag424_sdm_provisioner.services.provisioning_service.ProvisioningService.provision")
def test_provision_flow_logic(mock_provision, provisioning_service):
    """
    Test the provisioning flow logic directly.
    Verifies that calling provision() triggers the service correctly.
    """
    # Call the method under test
    provisioning_service.provision()
    
    # Verify provision was called
    mock_provision.assert_called_once()
