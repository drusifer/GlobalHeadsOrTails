"""Restore Backup Tool - Restore keys from backup history."""

import time

from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.base import ConfirmationRequest, TagState, ToolResult


class RestoreBackupTool:
    """Restore keys from backup when database is corrupted."""

    name = "Restore from Backup"
    description = "Cycle through backups until authentication succeeds"
    RATE_LIMIT_SECONDS = 0.75

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """Available if tag has backups."""
        if tag_state.backup_count == 0:
            return False, "no backups available for this tag"
        return True

    def get_confirmation_request(self, tag_state: TagState) -> ConfirmationRequest:
        """Confirm restoration."""
        return ConfirmationRequest(
            title="Restore Keys from Backup",
            items=[
                f"Test {tag_state.backup_count} backup snapshot(s) against the tag",
                "Stop after the first successful authentication",
                "Persist the matching keys back into tag_keys.csv",
            ],
            default_yes=False,
        )

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Iterate through backup snapshots until authentication succeeds."""
        # tag_state.uid is already a UID object
        backups: list[TagKeys] = key_mgr.get_backup_entries(tag_state.uid)
        if not backups:
            return ToolResult(success=False, message="No backups found for this tag", details={})

        attempt_log = []
        restored_entry: TagKeys | None = None

        for index, entry in enumerate(backups, start=1):
            attempt_info = {
                "index": index,
                "timestamp": entry.timestamp.isoformat(),
                "status": entry.keys.status,
                "notes": entry.keys.notes[:80],
            }

            try:
                card.send(SelectPiccApplication())
            except Exception as select_exc:
                attempt_info["result"] = "select_failed"
                attempt_info["error"] = str(select_exc)
                attempt_log.append(attempt_info)
                time.sleep(self.RATE_LIMIT_SECONDS)
                continue

            try:
                with AuthenticateEV2(entry.keys.get_picc_master_key_bytes(), key_no=0x00)(card):
                    attempt_info["result"] = "success"
                    restored_entry = entry
                    attempt_log.append(attempt_info)
                    break
            except Exception as auth_exc:
                attempt_info["result"] = "failed"
                attempt_info["error"] = str(auth_exc)
                attempt_log.append(attempt_info)
                time.sleep(self.RATE_LIMIT_SECONDS)

        if not restored_entry:
            return ToolResult(
                success=False,
                message="Unable to authenticate with any backup snapshot",
                details={"attempts": attempt_log, "tested_backups": len(attempt_log)},
            )

        # Persist the matching keys back into the primary CSV
        key_mgr.save_tag_keys(restored_entry.keys)

        return ToolResult(
            success=True,
            message="Keys restored from backup",
            details={
                "restored_timestamp": restored_entry.timestamp.isoformat(),
                "restored_status": restored_entry.keys.status,
                "attempts": attempt_log,
                "tested_backups": len(attempt_log),
            },
        )
