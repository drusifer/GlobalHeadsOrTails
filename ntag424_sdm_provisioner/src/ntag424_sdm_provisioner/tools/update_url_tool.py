"""Update URL Tool - Change NDEF URL without modifying keys."""

from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOSelectFile
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessageAuth
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import ConfirmationRequest, TagState, ToolResult
from ntag424_sdm_provisioner.tools.tool_helpers import read_ndef_file


class UpdateUrlTool:
    """Change NDEF URL without modifying cryptographic keys."""

    name = "Update URL"
    description = "Change URL without modifying keys (simple NDEF write)"

    def __init__(self, default_base_url: str):
        self.default_base_url = default_base_url

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """Available if tag has NDEF content."""
        if not tag_state.has_ndef:
            return False, "no NDEF content on tag"
        return True

    def get_confirmation_request(self) -> ConfirmationRequest:
        """Request new URL from user."""
        return ConfirmationRequest(
            title="Update URL",
            items=["Write new NDEF URL to tag", "Keys and SDM settings unchanged"],
            default_yes=False,
        )

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Update URL - business logic only."""
        # Read current URL
        current_ndef = read_ndef_file(card)
        current_url = self._extract_url(current_ndef)

        # Use default URL (in real impl, runner would ask user)
        new_url = self.default_base_url

        # Write new NDEF
        ndef_record = build_ndef_uri_record(new_url)
        tag_keys = key_mgr.get_tag_keys(tag_state.uid)
        picc_key = tag_keys.get_picc_master_key_bytes()
        card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
        with AuthenticateEV2(picc_key, key_no=0x00)(card) as auth_conn:
            auth_conn.send(WriteNdefMessageAuth(ndef_record))

        return ToolResult(
            success=True,
            message="URL Updated",
            details={
                "old_url": current_url[:80] + ("..." if len(current_url) > 80 else ""),
                "new_url": new_url[:80] + ("..." if len(new_url) > 80 else ""),
            },
        )

    def _extract_url(self, ndef_data: bytes) -> str:
        """Extract URL from NDEF data."""
        # Simplified - reuse from ReadUrlTool if needed
        try:
            # Find D1 01 pattern
            for i in range(len(ndef_data) - 1):
                if ndef_data[i] == 0xD1 and ndef_data[i + 1] == 0x01:
                    payload_len = ndef_data[i + 2]
                    prefix_code = ndef_data[i + 4]
                    uri_bytes = ndef_data[i + 5 : i + 5 + payload_len - 1]

                    prefixes = {0x00: "", 0x03: "http://", 0x04: "https://"}
                    prefix = prefixes.get(prefix_code, "")
                    uri = uri_bytes.decode("utf-8", errors="replace").rstrip("\xfe")

                    return prefix + uri
        except Exception:
            pass

        return "(unable to parse)"
