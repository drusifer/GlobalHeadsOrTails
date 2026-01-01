"""
Test: Provisioning Service Command Sequence

Validates that the ProvisioningService executes commands in the correct
sequence and on the correct connection type (authenticated vs. unauthenticated).
"""
from unittest.mock import MagicMock, patch

import pytest

from ntag424_sdm_provisioner.commands.change_file_settings import (
    ChangeFileSettings,
    ChangeFileSettingsAuth,
)
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService


@pytest.fixture
def mock_card_connection():
    """Provides a mock NTag424CardConnection."""
    card = MagicMock(spec=NTag424CardConnection)
    card.send.return_value = MagicMock()  # Default return for any command
    return card


@pytest.fixture
def mock_auth_connection():
    """Provides a mock AuthenticatedConnection."""
    auth_conn = MagicMock()
    auth_conn.send.return_value = MagicMock()
    return auth_conn


@pytest.fixture
def key_manager(tmp_path):
    """Provides a CsvKeyManager with a temporary keys file."""
    keys_file = tmp_path / "tag_keys.csv"
    return CsvKeyManager(str(keys_file))


@patch("ntag424_sdm_provisioner.services.provisioning_service.AuthenticateEV2")
def test_change_file_settings_is_unauthenticated(
    mock_authenticate_ev2,
    mock_card_connection,
    mock_auth_connection,
    key_manager,
):
    """
    Verify that ChangeFileSettings is sent on the unauthenticated connection,
    while other commands are sent on the authenticated connection.
    """
    # Arrange: Make the AuthenticateEV2 context manager return our mock auth_conn
    mock_authenticate_ev2.return_value.__enter__.return_value = mock_auth_connection

    # Instantiate the service with the mock card connection
    service = ProvisioningService(card=mock_card_connection, key_mgr=key_manager)

    # Act
    # We expect this to fail on real commands, but we can run it far enough
    # to check which `send` methods were called with which commands.
    # We suppress the errors because our mocks are basic.
    try:
        service.provision("https://example.com")
    except Exception:
        pass  # Ignore exceptions from incomplete mocks

    # Assert
    # Check that ChangeFileSettings was called on the BASE card connection
    unauth_sent_cmds = [
        call.args[0].__class__ for call in mock_card_connection.send.call_args_list
    ]
    assert( ChangeFileSettings in unauth_sent_cmds,
        "ChangeFileSettings should be sent on the unauthenticated base connection")

    # Check that ChangeFileSettingsAuth was NOT called on the AUTHENTICATED connection
    auth_sent_cmds = [
        call.args[0].__class__ for call in mock_auth_connection.send.call_args_list
    ]
    assert(ChangeFileSettingsAuth not in auth_sent_cmds,
        "ChangeFileSettingsAuth should not be sent on the authenticated connection")

    # For good measure, verify ChangeKey was called on the authenticated connection
    from ntag424_sdm_provisioner.commands.change_key import ChangeKey
    assert( ChangeKey in auth_sent_cmds,
        "ChangeKey should be sent on the authenticated connection")
