"""Unit tests for NtagProvisionerApp wiring and fail-fast startup."""

from unittest.mock import MagicMock, patch
import pytest

from sdm_provisioner.service_key_manager import ServiceKeyManager
from sdm_provisioner.tui.app import NtagProvisionerApp
from tag_validator.client import TagValidatorClient


def test_tui_app_init_with_custom_key_manager(tmp_path):
    mock_km = MagicMock(spec=ServiceKeyManager)
    mock_km.list_tags.return_value = []
    log_file = str(tmp_path / "test_tui.log")

    app = NtagProvisionerApp(log_file=log_file, key_manager=mock_km)
    assert app.key_manager is mock_km


def test_tui_app_default_instantiates_service_key_manager(tmp_path):
    log_file = str(tmp_path / "test_tui.log")
    with patch("sdm_provisioner.service_key_manager.TagValidatorClient.is_healthy", return_value=True), \
         patch("sdm_provisioner.service_key_manager.TagValidatorClient.list_keys", return_value=[]):
        app = NtagProvisionerApp(log_file=log_file, strict=True)
        assert isinstance(app.key_manager, ServiceKeyManager)


def test_tui_app_strict_mode_unreachable_raises_connection_error(tmp_path):
    log_file = str(tmp_path / "test_tui.log")
    with patch("sdm_provisioner.service_key_manager.TagValidatorClient.is_healthy", return_value=False):
        with pytest.raises(ConnectionError, match="make run-tag-validator"):
            NtagProvisionerApp(log_file=log_file, strict=True)
