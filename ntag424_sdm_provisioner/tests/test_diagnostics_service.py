from unittest.mock import MagicMock

import pytest

from ntag424_sdm_provisioner.constants import TagStatus
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.sequence_logger import create_sequence_logger
from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager
from ntag424_sdm_provisioner.services.diagnostics_service import TagDiagnosticsService
from natag424_sdm_provisioner.uid_utils import UID


class TestTagDiagnosticsService:
    
    @pytest.fixture
    def mock_key_mgr(self):
        return MagicMock(spec=CsvKeyManager)
    
    @pytest.fixture
    def sequence_logger(self):
        return create_sequence_logger("Test")
        
    @pytest.fixture
    def simulator(self, sequence_logger):
        return SeritagCardManager(sequence_logger)
        
    def test_get_chip_info(self, simulator, mock_key_mgr):
        """Test retrieving chip info from simulator."""
        with simulator as card:
            service = TagDiagnosticsService(card, mock_key_mgr)
            info = service.get_chip_info()
            
            assert info is not None
            assert info.uid == UID("043F684A2F7080")  # SeritagSimulator UID
            assert info.hw_storage_size == 416
            
    def test_get_tag_status_factory(self, simulator, mock_key_mgr):
        """Test tag status detection for factory tag (not in DB)."""
        # Setup mock to raise error (simulating not found)
        mock_key_mgr.get_tag_keys.side_effect = Exception("Not found")
        
        with simulator as card:
            service = TagDiagnosticsService(card, mock_key_mgr)
            status = service.get_tag_status()
            
            assert status == TagStatus.FACTORY
            
    def test_get_tag_status_provisioned(self, simulator, mock_key_mgr):
        """Test tag status detection for provisioned tag (in DB)."""
        # Setup mock to return keys
        mock_keys = MagicMock(spec=TagKeys)
        mock_keys.status = 'provisioned'
        mock_key_mgr.get_tag_keys.return_value = mock_keys
        
        with simulator as card:
            service = TagDiagnosticsService(card, mock_key_mgr)
            status = service.get_tag_status()
            
            assert status == TagStatus.PROVISIONED
            
    def test_get_key_versions(self, simulator, mock_key_mgr):
        """Test retrieving key versions."""
        with simulator as card:
            service = TagDiagnosticsService(card, mock_key_mgr)
            versions = service.get_key_versions()
            
            assert len(versions) == 5
            assert versions['key_0'] == "0x00" # Simulator returns 0x00 by default
            
    def test_get_full_diagnostics(self, simulator, mock_key_mgr):
        """Test full diagnostics collection."""
        with simulator as card:
            service = TagDiagnosticsService(card, mock_key_mgr)
            diag = service.get_full_diagnostics()

            assert 'chip' in diag
            assert 'key_versions_unauth' in diag  # Current API uses key_versions_unauth
            assert 'file_settings_unauth' in diag  # Current API uses file_settings_unauth
            assert 'cc_file' in diag
            assert 'ndef' in diag

            assert diag['chip']['uid'] == "043F684A2F7080"  # SeritagSimulator UID
