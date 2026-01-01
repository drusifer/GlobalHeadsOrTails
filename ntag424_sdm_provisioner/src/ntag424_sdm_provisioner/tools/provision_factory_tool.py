"""Provision Factory Tool - Initial provisioning of factory tags."""

from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOSelectFile
from ntag424_sdm_provisioner.commands.sdm_helpers import build_ndef_uri_record
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import ConfirmationRequest, TagState, ToolResult
from ntag424_sdm_provisioner.tools.tool_helpers import (
    build_sdm_url_template,
    configure_sdm_with_offsets,
)
from ntag424_sdm_provisioner.trace_util import trace_block


class ProvisionFactoryTool:
    """Initial provisioning of factory-default tags."""

    name = "Provision Factory Tag"
    description = "Initial provision with random keys and SDM"

    def __init__(self, base_url: str):
        self.base_url = base_url

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """Available only for factory/unknown tags."""
        if tag_state.in_database and tag_state.keys and tag_state.keys.status == "provisioned":
            return False, "tag already provisioned (use Re-provision instead)"
        return True

    def get_confirmation_request(self) -> ConfirmationRequest:
        """Confirm full provisioning."""
        return ConfirmationRequest(
            title="Provision Factory Tag",
            items=[
                "Generate random keys (5 keys)",
                "Change all keys from factory defaults",
                "Configure SDM with UID + Counter + CMAC",
                f"Set base URL: {self.base_url[:60]}...",
                "Write NDEF with SDM placeholders",
                "Save keys to database",
            ],
            default_yes=False,
        )

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Provision factory tag with random keys and SDM."""
        url_template = ""
        with trace_block("Provision Factory Tag"):
            with key_mgr.provision_tag(tag_state.uid, url=self.base_url) as staged_keys:
                picc_key = staged_keys.get_picc_master_key_bytes()
                app_read_key = staged_keys.get_app_read_key_bytes()
                sdm_mac_key = staged_keys.get_sdm_mac_key_bytes()

                with AuthenticateEV2(FACTORY_KEY, key_no=0x00)(card) as auth_conn:
                    auth_conn.send(ChangeKey(0, picc_key, FACTORY_KEY, key_version=0x00))

                with AuthenticateEV2(picc_key, key_no=0x00)(card) as auth_conn:
                    auth_conn.send(ChangeKey(1, app_read_key, FACTORY_KEY, key_version=0x00))
                    auth_conn.send(ChangeKey(2, app_read_key, FACTORY_KEY, key_version=0x00))
                    auth_conn.send(ChangeKey(3, sdm_mac_key, FACTORY_KEY, key_version=0x00))
                    auth_conn.send(ChangeKey(4, sdm_mac_key, FACTORY_KEY, key_version=0x00))

                    template = build_sdm_url_template(self.base_url)
                    configure_sdm_with_offsets(auth_conn, template)

                    url_template = template.build_url()
                    ndef_record = build_ndef_uri_record(url_template)
                    card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
                    card.send(WriteNdefMessage(ndef_record))

        return ToolResult(
            success=True,
            message="Factory Tag Provisioned",
            details={"keys_generated": 5, "sdm_enabled": True, "url": url_template[:80] + "..."},
        )
