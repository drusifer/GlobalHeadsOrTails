"""Configure SDM Tool - Enable Secure Dynamic Messaging on provisioned tags."""

from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOSelectFile
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import ConfirmationRequest, TagState, ToolResult
from ntag424_sdm_provisioner.tools.tool_helpers import (
    build_sdm_url_template,
    configure_sdm_with_offsets,
)
from ntag424_sdm_provisioner.trace_util import trace_block


class ConfigureSdmTool:
    """Configure Secure Dynamic Messaging on a provisioned tag.

    Authenticates with PICC Master Key and configures SDM with:
    - UID mirroring
    - Read counter
    - CMAC for authentication
    """

    name = "Configure SDM"
    description = "Enable/configure Secure Dynamic Messaging (requires auth)"

    def __init__(self, base_url: str):
        self.base_url = base_url

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """SDM config requires tag to be provisioned with known keys."""
        if not tag_state.in_database:
            return False, "tag not in database (run Provision first)"
        if not tag_state.keys:
            return False, "no keys available"
        return True

    def get_confirmation_request(self, tag_state: TagState) -> ConfirmationRequest:
        """Request confirmation before configuring SDM."""
        return ConfirmationRequest(
            title=f"Configure SDM on {tag_state.uid}",
            items=[
                f"Base URL: {self.base_url[:60]}{'...' if len(self.base_url) > 60 else ''}",
                "Enable UID mirroring",
                "Enable read counter",
                "Enable CMAC authentication",
                "Authenticate with PICC Master Key",
                "Write NDEF with SDM placeholders",
            ],
            default_yes=False,
        )

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Configure SDM - pure business logic, no I/O.

        Returns structured result for runner to display.
        """
        # Build URL template
        template = build_sdm_url_template(self.base_url)
        url_template = template.build_url()

        # Authenticate and configure SDM
        with trace_block("Configure SDM"):
            # TagKeys normalizes bytes to string in __post_init__
            tag_keys = key_mgr.get_tag_keys(tag_state.uid)
            picc_key = tag_keys.get_picc_master_key_bytes()

            with AuthenticateEV2(picc_key, key_no=0x00)(card) as auth_conn:
                # Configure SDM file settings
                sdm_config = configure_sdm_with_offsets(auth_conn, template)

                # Update NDEF while session remains authenticated
                ndef_record = build_ndef_uri_record(url_template)
                card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
                card.send(WriteNdefMessage(ndef_record))

        # Return structured result
        return ToolResult(
            success=True,
            message="SDM Configuration Complete!",
            details={
                "asset_tag": tag_state.uid.asset_tag,
                "url_template": url_template,
                "template_length": len(url_template),
                "uid_offset": sdm_config.offsets.uid_offset,
                "ctr_offset": sdm_config.offsets.read_ctr_offset,
                "mac_offset": sdm_config.offsets.mac_offset,
            },
        )
