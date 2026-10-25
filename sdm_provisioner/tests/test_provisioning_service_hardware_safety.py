"""Test: Provisioning Service Hardware Safety Rules

Validates that ProvisioningService strictly enforces real persistent ServiceKeyManager
when interacting with real hardware HAL, and that simulation flags allow mock/test managers.
"""
import os
from unittest.mock import MagicMock

import pytest

from sdm_provisioner.csv_key_manager import CsvKeyManager
from sdm_provisioner.hal import NTag424CardConnection
from sdm_provisioner.service_key_manager import ServiceKeyManager
from sdm_provisioner.services.provisioning_service import ProvisioningService


def test_hardware_with_service_key_manager_initializes_cleanly():
    """Verify that real hardware HAL card (is_simulation=False) initializes cleanly with ServiceKeyManager."""
    card = MagicMock(spec=NTag424CardConnection)
    card.is_simulation = False

    service_km = MagicMock(spec=ServiceKeyManager)

    # Must not raise NameError (missing os) or RuntimeError (invalid key store)
    service = ProvisioningService(card=card, key_mgr=service_km)
    assert service.key_mgr is service_km


def test_hardware_with_csv_key_manager_raises_runtime_error(tmp_path):
    """Verify that real hardware HAL card (is_simulation=False) strictly rejects CsvKeyManager."""
    card = MagicMock(spec=NTag424CardConnection)
    card.is_simulation = False

    csv_km = CsvKeyManager(str(tmp_path / "keys.csv"))

    with pytest.raises(RuntimeError, match="CRITICAL HARDWARE KEY SAFETY RULE"):
        ProvisioningService(card=card, key_mgr=csv_km)


def test_simulation_flag_allows_mock_key_manager():
    """Verify that setting is_simulation=True allows non-ServiceKeyManager."""
    card = MagicMock(spec=NTag424CardConnection)
    card.is_simulation = True

    mock_km = MagicMock()
    service = ProvisioningService(card=card, key_mgr=mock_km)
    assert service.key_mgr is mock_km


def test_env_simulation_flag_allows_mock_key_manager(monkeypatch):
    """Verify that setting NTAG_SIMULATION=1 in environment allows non-ServiceKeyManager even if card.is_simulation is False."""
    card = MagicMock(spec=NTag424CardConnection)
    card.is_simulation = False

    monkeypatch.setenv("NTAG_SIMULATION", "1")
    mock_km = MagicMock()
    service = ProvisioningService(card=card, key_mgr=mock_km)
    assert service.key_mgr is mock_km
