"""Diagnostics Tool - Collect complete tag information."""

from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_file_settings import GetFileSettings
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOReadBinary, ISOSelectFile
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import TagState, ToolResult
from ntag424_sdm_provisioner.tools.tool_helpers import read_ndef_file
from ntag424_sdm_provisioner.uid_utils import UID


class DiagnosticsTool:
    """Collect complete tag diagnostics.

    Read-only tool that gathers all tag information for troubleshooting.
    """

    name = "Show Diagnostics"
    description = "Display complete tag information (chip, keys, NDEF)"

    def is_available(self, _tag_state: TagState) -> bool:
        """Always available."""
        return True

    def get_confirmation_request(self, _tag_state: TagState) -> None:
        """No confirmation needed for read-only diagnostics."""
        return None

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, _key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Collect all diagnostic information - no I/O!"""
        diagnostics = {}

        # Chip information
        try:
            version_info = card.send(GetChipVersion())
            diagnostics["chip"] = {
                "uid": version_info.uid.uid,  # version_info.uid is already a UID object
                "hw_version": f"{version_info.hw_major_version}.{version_info.hw_minor_version}",
                "sw_version": f"{version_info.sw_major_version}.{version_info.sw_minor_version}",
                "hw_storage": version_info.hw_storage_size,
                "batch": version_info.batch_no.hex().upper(),
                "fab_date": f"Week {version_info.fab_week}, 20{version_info.fab_year}",
            }
        except Exception as e:
            diagnostics["chip"] = {"error": str(e)}

        # Database status
        if tag_state.in_database and tag_state.keys:
            diagnostics["database"] = {
                "status": tag_state.keys.status,
                "provisioned_date": tag_state.keys.provisioned_date,
                "notes": tag_state.keys.notes or "None",
                "picc_key_preview": tag_state.keys.picc_master_key[:16] + "...",
            }
        else:
            diagnostics["database"] = {"status": "NOT IN DATABASE"}

        # Key versions
        key_versions = {}
        for key_no in range(5):
            try:
                key_ver = card.send(GetKeyVersion(key_no))
                key_versions[f"key_{key_no}"] = f"0x{key_ver.version:02X}"
            except Exception:
                key_versions[f"key_{key_no}"] = "error"
        diagnostics["key_versions"] = key_versions

        # File settings (File 02 - NDEF)
        try:
            settings = card.send(GetFileSettings(0x02))
            diagnostics["file_settings"] = {"settings": str(settings)}
        except Exception as e:
            diagnostics["file_settings"] = {"error": f"Error: {e}"}

        # CC File
        try:
            card.send(ISOSelectFile(ISOFileID.CC_FILE))
            cc_data = card.send(ISOReadBinary(0, 15))
            card.send(SelectPiccApplication())

            diagnostics["cc_file"] = {
                "raw": cc_data.hex().upper(),
                "magic": f"0x{int.from_bytes(cc_data[0:2], 'big'):04X}",
                "version": f"{cc_data[2]}.{cc_data[3]}",
                "max_size": int.from_bytes(cc_data[11:13], "big"),
            }
        except Exception as e:
            diagnostics["cc_file"] = {"error": str(e)}

        # NDEF File
        try:
            ndef_data = read_ndef_file(card)
            diagnostics["ndef"] = {
                "length": len(ndef_data),
                "preview": ndef_data[:100].hex().upper(),
            }
        except Exception as e:
            diagnostics["ndef"] = {"error": str(e)}

        return ToolResult(success=True, message="Diagnostics collected", details=diagnostics)
