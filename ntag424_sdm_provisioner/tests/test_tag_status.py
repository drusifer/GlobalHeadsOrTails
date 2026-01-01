import pytest
from unittest.mock import MagicMock, patch
from ntag424_sdm_provisioner.tui.commands.tag_status_command import TagStatusCommand
from ntag424_sdm_provisioner.constants import FACTORY_KEY

class TestTagStatusCommand:
    
    @pytest.fixture
    def mock_connection(self):
        conn = MagicMock()
        return conn
        
    @pytest.fixture
    def mock_factory(self, mock_connection):
        # Patch where it is IMPORTED/USED, not where it is defined
        with patch('ntag424_sdm_provisioner.tui.commands.tag_status_command.CardConnectionFactory.create') as mock:
            mock.return_value.__enter__.return_value = mock_connection
            yield mock
            
    @pytest.fixture
    def mock_key_manager(self):
        with patch('ntag424_sdm_provisioner.tui.commands.tag_status_command.CsvKeyManager') as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_auth_ev2(self):
        with patch('ntag424_sdm_provisioner.tui.commands.tag_status_command.AuthenticateEV2') as mock:
            yield mock

    def test_factory_state(self, mock_factory, mock_connection, mock_key_manager, mock_auth_ev2):
        # Setup
        cmd = TagStatusCommand()
        
        # Mock Version
        mock_version = MagicMock()
        mock_version.uid = bytes.fromhex("04000000000000")
        mock_connection.send.return_value = mock_version
        
        # Mock Auth Success for Factory Key
        # AuthenticateEV2(key, key_no)(connection) -> returns context manager or connection
        mock_auth_instance = mock_auth_ev2.return_value
        mock_auth_instance.return_value = MagicMock() # The result of calling the instance
        
        # Execute
        result = cmd.execute()
        
        # Verify
        assert result['status'] == "Factory New"
        assert result['key_state'] == "Default Keys"
        assert result['uid'] == "04000000000000"
        
        # Verify Auth was called with Factory Key
        mock_auth_ev2.assert_called_with(FACTORY_KEY, 0)
        mock_auth_instance.assert_called_with(mock_connection)
        
    def test_provisioned_state(self, mock_factory, mock_connection, mock_key_manager, mock_auth_ev2):
        # Setup
        cmd = TagStatusCommand()
        
        # Mock Version
        mock_version = MagicMock()
        mock_version.uid = bytes.fromhex("04000000000000")
        mock_connection.send.return_value = mock_version
        
        # Mock Auth Fail (Factory) -> Success (Provisioned)
        mock_auth_instance = mock_auth_ev2.return_value
        
        # First call (Factory) raises Exception, Second call (Provisioned) succeeds
        def side_effect(conn):
            # Check which key was used to initialize the auth instance
            # This is tricky with mocks because return_value is shared.
            # Easier way: check call args of the CLASS
            if mock_auth_ev2.call_args[0][0] == FACTORY_KEY:
                raise Exception("Auth Failed")
            return MagicMock()
            
        mock_auth_instance.side_effect = side_effect
        
        # Mock Key Manager
        mock_key_manager.get_tag_keys.return_value.status = "provisioned"
        mock_key_manager.get_tag_keys.return_value.get_picc_master_key_bytes.return_value = b'1'*16
        
        # Execute
        result = cmd.execute()
        
        # Verify
        assert result['status'] == "Provisioned"
        assert result['key_state'] == "Registered Keys"
        
    def test_unknown_state(self, mock_factory, mock_connection, mock_key_manager, mock_auth_ev2):
        # Setup
        cmd = TagStatusCommand()
        
        # Mock Version
        mock_version = MagicMock()
        mock_version.uid = bytes.fromhex("04000000000000")
        mock_connection.send.return_value = mock_version
        
        # Mock Auth Fail (Factory) -> Fail (Provisioned)
        mock_auth_instance = mock_auth_ev2.return_value
        mock_auth_instance.side_effect = Exception("Auth Failed")
        
        # Mock Key Manager
        mock_key_manager.get_tag_keys.return_value.status = "provisioned"
        mock_key_manager.get_tag_keys.return_value.get_picc_master_key_bytes.return_value = b'1'*16
        
        # Execute
        result = cmd.execute()
        
        # Verify
        assert result['status'] == "Unknown / Locked"
