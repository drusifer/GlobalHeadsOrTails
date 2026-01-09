"""Reprovision Tool - Change keys on already-provisioned tag."""

import secrets

from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import ConfirmationRequest, TagState, ToolResult
from ntag424_sdm_provisioner.trace_util import trace_block


class ReprovisionTool:
    """Change all keys on a provisioned tag."""

    name = "Re-provision (Change Keys)"
    description = "Change keys on provisioned tag (requires old keys)"

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """Available if tag is provisioned with known keys."""
        if not tag_state.in_database:
            return False, "tag not in database"
        if not tag_state.keys:
            return False, "no keys available"
        return True

    def get_confirmation_request(self) -> ConfirmationRequest:
        """Confirm key change."""
        return ConfirmationRequest(
            title="Re-provision Tag (Change All Keys)",
            items=[
                "Generate new random keys (5 keys)",
                "Authenticate with current PICC Master Key",
                "Change all keys to new values",
                "Update database with new keys",
                "Backup old keys",
            ],
            default_yes=False,
        )

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Change all keys to new random values."""
        # Generate new keys
        new_keys = {i: secrets.token_bytes(16) for i in range(5)}
        old_keys = key_mgr.get_tag_keys(tag_state.uid)

        # Authenticate with old PICC key and change all keys
        with trace_block("Change Keys"):
            picc_key = old_keys.get_picc_master_key_bytes()

            with AuthenticateEV2(picc_key, key_no=0x00)(card) as auth_conn:
                for key_no in range(5):
                    old_key_bytes = getattr(
                        old_keys,
                        f"get_app_key_{key_no}_bytes"
                        if key_no > 0
                        else "get_picc_master_key_bytes",
                    )()
                    auth_conn.send(
                        ChangeKey(
                            key_no_to_change=key_no,
                            new_key=new_keys[key_no],
                            old_key=old_key_bytes,
                            key_version=0x01,
                        )
                    )

        # Save new keys

        new_tag_keys = TagKeys(
            uid=tag_state.uid,
            picc_master_key=new_keys[0].hex(),
            app_read_key=new_keys[1].hex(),
            sdm_mac_key=new_keys[3].hex(),
            provisioned_date=old_keys.provisioned_date,
            status="reprovisioned",
            notes="Keys changed",
        )
        key_mgr.save_tag_keys(new_tag_keys)

        return ToolResult(
            success=True,
            message="Tag Re-provisioned",
            details={"keys_changed": 5, "new_version": "0x01"},
        )
