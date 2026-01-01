"""DEPRECATED: This module has been refactored into individual command files.

For new code, import directly from command modules:
  - from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
  - from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
  - from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
  - etc.

This file provides backwards-compatible re-exports for existing code.
"""

# Re-export all commands from their new individual files
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters
from ntag424_sdm_provisioner.commands.get_file_ids import GetFileIds
from ntag424_sdm_provisioner.commands.get_file_settings import GetFileSettings
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import (
    AuthenticateEV2,
    AuthenticateEV2First,
    AuthenticateEV2Second,
)


__all__ = [
    "AuthenticateEV2",
    "AuthenticateEV2First",
    "AuthenticateEV2Second",
    "GetChipVersion",
    "GetFileCounters",
    "GetFileIds",
    "GetFileSettings",
    "GetKeyVersion",
    "SelectPiccApplication",
]
