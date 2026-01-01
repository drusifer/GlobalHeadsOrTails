"""DEPRECATED: Legacy imports for backwards compatibility.

This module re-exports commands from their new individual files.
New code should import directly from command modules:
  - from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
  - from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
  - etc.

This file exists only for backwards compatibility with existing examples.
"""

# Re-export all commands from their new locations
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
