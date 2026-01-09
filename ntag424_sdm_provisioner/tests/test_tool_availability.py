"""Unit tests for tool availability logic.

Tests each tool's is_available() method with various tag states.
"""

import pytest

from ntag424_sdm_provisioner.csv_key_manager import TagKeys
from ntag424_sdm_provisioner.tools.base import TagState
from ntag424_sdm_provisioner.tools.configure_sdm_tool import ConfigureSdmTool
from ntag424_sdm_provisioner.tools.diagnostics_tool import DiagnosticsTool
from ntag424_sdm_provisioner.tools.provision_factory_tool import ProvisionFactoryTool
from ntag424_sdm_provisioner.tools.read_url_tool import ReadUrlTool
from ntag424_sdm_provisioner.tools.reprovision_tool import ReprovisionTool
from ntag424_sdm_provisioner.tools.restore_backup_tool import RestoreBackupTool
from ntag424_sdm_provisioner.tools.update_url_tool import UpdateUrlTool


# Default test URL for tools that require it
TEST_BASE_URL = "https://example.com/verify"


# Test fixtures for different tag states

@pytest.fixture
def factory_tag_not_in_db():
    """Factory tag not in database (brand new)."""
    return TagState(
        uid=bytes.fromhex("04123456789ABC"),
        in_database=False,
        keys=None,
        has_ndef=False,
        backup_count=0
    )


@pytest.fixture
def factory_tag_in_db():
    """Factory tag in database with factory status."""
    keys = TagKeys(
        uid="04123456789ABC",
        picc_master_key="00" * 16,
        app_read_key="00" * 16,
        sdm_mac_key="00" * 16,
        status="factory",
        provisioned_date="",
        notes="Factory default keys"
    )
    return TagState(
        uid=bytes.fromhex("04123456789ABC"),
        in_database=True,
        keys=keys,
        has_ndef=False,
        backup_count=0
    )


@pytest.fixture
def provisioned_tag_with_ndef():
    """Provisioned tag with NDEF content."""
    keys = TagKeys(
        uid="04123456789ABC",
        picc_master_key="11" * 16,
        app_read_key="22" * 16,
        sdm_mac_key="33" * 16,
        status="provisioned",
        provisioned_date="2025-11-11T12:00:00",
        notes="https://example.com"
    )
    return TagState(
        uid=bytes.fromhex("04123456789ABC"),
        in_database=True,
        keys=keys,
        has_ndef=True,
        backup_count=2
    )


@pytest.fixture
def failed_tag_with_backups():
    """Tag with failed provisioning but has backups."""
    keys = TagKeys(
        uid="04123456789ABC",
        picc_master_key="11" * 16,
        app_read_key="22" * 16,
        sdm_mac_key="33" * 16,
        status="failed",
        provisioned_date="2025-11-11T12:00:00",
        notes="Provisioning failed"
    )
    return TagState(
        uid=bytes.fromhex("04123456789ABC"),
        in_database=True,
        keys=keys,
        has_ndef=False,
        backup_count=3
    )


# DiagnosticsTool Tests

def test_diagnostics_always_available(factory_tag_not_in_db, provisioned_tag_with_ndef):
    """DiagnosticsTool should always be available."""
    tool = DiagnosticsTool()
    
    assert tool.is_available(factory_tag_not_in_db) is True
    assert tool.is_available(provisioned_tag_with_ndef) is True


# ReadUrlTool Tests

def test_read_url_available_with_ndef(provisioned_tag_with_ndef):
    """ReadUrlTool available when NDEF content exists."""
    tool = ReadUrlTool()
    assert tool.is_available(provisioned_tag_with_ndef) is True


def test_read_url_unavailable_without_ndef(factory_tag_not_in_db):
    """ReadUrlTool unavailable when no NDEF content."""
    tool = ReadUrlTool()
    result = tool.is_available(factory_tag_not_in_db)
    
    assert result is not True
    is_available, reason = result
    assert is_available is False
    assert "NDEF content" in reason


# UpdateUrlTool Tests

def test_update_url_available_with_ndef(provisioned_tag_with_ndef):
    """UpdateUrlTool available when NDEF content exists."""
    tool = UpdateUrlTool(TEST_BASE_URL)
    assert tool.is_available(provisioned_tag_with_ndef) is True


def test_update_url_unavailable_without_ndef(factory_tag_not_in_db):
    """UpdateUrlTool unavailable when no NDEF content."""
    tool = UpdateUrlTool(TEST_BASE_URL)
    result = tool.is_available(factory_tag_not_in_db)
    
    assert result is not True
    is_available, reason = result
    assert is_available is False
    assert "NDEF content" in reason


# ConfigureSdmTool Tests

def test_configure_sdm_available_with_keys(provisioned_tag_with_ndef):
    """ConfigureSdmTool available when keys are known."""
    tool = ConfigureSdmTool(TEST_BASE_URL)
    assert tool.is_available(provisioned_tag_with_ndef) is True


def test_configure_sdm_unavailable_without_keys(factory_tag_not_in_db):
    """ConfigureSdmTool unavailable when keys unknown."""
    tool = ConfigureSdmTool(TEST_BASE_URL)
    result = tool.is_available(factory_tag_not_in_db)
    
    assert result is not True
    is_available, reason = result
    assert is_available is False
    assert "not in database" in reason.lower() or "keys" in reason.lower()


# RestoreBackupTool Tests

def test_restore_available_with_backups(failed_tag_with_backups):
    """RestoreBackupTool available when backups exist."""
    tool = RestoreBackupTool()
    assert tool.is_available(failed_tag_with_backups) is True


def test_restore_unavailable_without_backups(factory_tag_not_in_db):
    """RestoreBackupTool unavailable when no backups."""
    tool = RestoreBackupTool()
    result = tool.is_available(factory_tag_not_in_db)
    
    assert result is not True
    is_available, reason = result
    assert is_available is False
    assert "backup" in reason.lower()


# ReprovisionTool Tests

def test_reprovision_available_with_keys(provisioned_tag_with_ndef):
    """ReprovisionTool available when keys are known."""
    tool = ReprovisionTool()
    assert tool.is_available(provisioned_tag_with_ndef) is True


def test_reprovision_unavailable_without_keys(factory_tag_not_in_db):
    """ReprovisionTool unavailable when keys unknown."""
    tool = ReprovisionTool()
    result = tool.is_available(factory_tag_not_in_db)
    
    assert result is not True
    is_available, reason = result
    assert is_available is False
    assert "not in database" in reason.lower() or "keys" in reason.lower()


# ProvisionFactoryTool Tests

def test_provision_factory_available_not_in_db(factory_tag_not_in_db):
    """ProvisionFactoryTool available for tags not in database."""
    tool = ProvisionFactoryTool(TEST_BASE_URL)
    assert tool.is_available(factory_tag_not_in_db) is True


def test_provision_factory_available_with_factory_status(factory_tag_in_db):
    """ProvisionFactoryTool available for factory status tags."""
    tool = ProvisionFactoryTool(TEST_BASE_URL)
    assert tool.is_available(factory_tag_in_db) is True


def test_provision_factory_unavailable_already_provisioned(provisioned_tag_with_ndef):
    """ProvisionFactoryTool unavailable for already provisioned tags."""
    tool = ProvisionFactoryTool(TEST_BASE_URL)
    result = tool.is_available(provisioned_tag_with_ndef)
    
    assert result is not True
    is_available, reason = result
    assert is_available is False
    assert "provisioned" in reason.lower()
    assert "re-provision" in reason.lower()


# Edge Cases

def test_multiple_tools_with_same_state(provisioned_tag_with_ndef):
    """Verify multiple tools can check same state independently."""
    diagnostics = DiagnosticsTool()
    read_url = ReadUrlTool()
    update_url = UpdateUrlTool(TEST_BASE_URL)
    configure_sdm = ConfigureSdmTool(TEST_BASE_URL)
    reprovision = ReprovisionTool()
    
    # All should be available for provisioned tag with NDEF
    assert diagnostics.is_available(provisioned_tag_with_ndef) is True
    assert read_url.is_available(provisioned_tag_with_ndef) is True
    assert update_url.is_available(provisioned_tag_with_ndef) is True
    assert configure_sdm.is_available(provisioned_tag_with_ndef) is True
    assert reprovision.is_available(provisioned_tag_with_ndef) is True


def test_provision_factory_with_failed_status(failed_tag_with_backups):
    """ProvisionFactoryTool behavior with failed status tag."""
    tool = ProvisionFactoryTool(TEST_BASE_URL)
    result = tool.is_available(failed_tag_with_backups)
    
    # Failed status tags can be re-provisioned using factory tool
    # (they're not "provisioned" status, so tool allows it)
    assert result is True


def test_all_tools_return_correct_type():
    """Verify all tools return correct types from is_available()."""
    tag_state = TagState(
        uid=bytes.fromhex("04123456789ABC"),
        in_database=False,
        keys=None,
        has_ndef=False,
        backup_count=0
    )
    
    tools = [
        DiagnosticsTool(),
        ReadUrlTool(),
        UpdateUrlTool(TEST_BASE_URL),
        ConfigureSdmTool(TEST_BASE_URL),
        RestoreBackupTool(),
        ReprovisionTool(),
        ProvisionFactoryTool(TEST_BASE_URL),
    ]
    
    for tool in tools:
        result = tool.is_available(tag_state)
        # Must be either True or (False, str)
        if result is True:
            assert result is True
        else:
            assert isinstance(result, tuple)
            assert len(result) == 2
            is_available, reason = result
            assert is_available is False
            assert isinstance(reason, str)
            assert len(reason) > 0  # Must have a reason

