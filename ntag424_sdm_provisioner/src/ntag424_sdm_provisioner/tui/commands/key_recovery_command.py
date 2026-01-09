"""Key Recovery Command - NFCCommand for recovering lost keys."""

import logging
from typing import Any

from ntag424_sdm_provisioner.card_factory import CardConnectionFactory
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.constants import StatusWord
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger
from ntag424_sdm_provisioner.services.key_recovery_service import (
    KeyRecoveryCandidate,
    KeyRecoveryService,
)
from ntag424_sdm_provisioner.tui.nfc_command import NFCCommand
from ntag424_sdm_provisioner.uid_utils import UID


log = logging.getLogger(__name__)


class KeyRecoveryCommand(NFCCommand):
    """Recover lost keys by scanning backup files and testing against tag."""

    def __init__(
        self,
        recovery_service: KeyRecoveryService,
        key_manager: CsvKeyManager,
        selected_candidate: KeyRecoveryCandidate | None = None,
    ):
        self.recovery_service = recovery_service
        self.key_manager = key_manager
        self.selected_candidate = selected_candidate

    @property
    def timeout_seconds(self) -> int:
        return 60  # Recovery can take a while if testing many candidates

    @property
    def operation_name(self) -> str:
        return "Key Recovery"

    def execute(self) -> dict[str, Any]:
        """Execute key recovery process - TEST ONLY (no automatic database save).

        Strategy:
        1. User selects a candidate key from backups
        2. Test authentication with the selected key
        3. Return results WITHOUT saving to database
        4. User must manually click "Restore Key" to save (separate operation)
        """
        results: dict[str, Any] = {
            "recovered": False,
            "is_factory": False,
            "uid": None,
            "files_searched": 0,
            "candidates_found": 0,
            "candidates_tested": 0,
            "candidate": None,
            "auth_delay": False,
            "keys_synced": False,
        }

        with CardConnectionFactory.create(sequence_logger=SequenceLogger()) as connection:
            log.info("Connected to tag")

            # Select PICC application
            connection.send(SelectPiccApplication())

            # Get tag UID
            version_info = connection.send(GetChipVersion())
            uid = version_info.uid.uid  # version_info.uid is already a UID object
            results["uid"] = uid
            log.info(f"Tag UID: {uid}")

            # User must select a candidate to test
            if not self.selected_candidate:
                log.error("No candidate selected - user must choose a key from backups to test")
                results["error"] = "No candidate selected"
                return results

            log.info(f"Testing user-selected key from {self.selected_candidate.source_file}")
            results["candidates_found"] = 1
            results["files_searched"] = 1
            results["candidates_tested"] = 1

            # Test the selected candidate (NO AUTOMATIC SAVE)
            try:
                if self.recovery_service.test_key_candidate(self.selected_candidate, connection):
                    log.info("✓ Selected key works!")
                    results["recovered"] = True
                    results["candidate"] = {
                        "source_file": self.selected_candidate.source_file,
                        "status": self.selected_candidate.status,
                        "provisioned_date": self.selected_candidate.provisioned_date,
                        "notes": self.selected_candidate.notes,
                        "picc_master_key": self.selected_candidate.picc_master_key.hex(),
                        "app_read_key": self.selected_candidate.app_read_key.hex(),
                        "sdm_file_read_key": self.selected_candidate.sdm_file_read_key.hex(),
                    }

                    # DO NOT save to database automatically
                    # User must click "Restore Key" button to save
                    log.info("Key test successful - waiting for user to click 'Restore Key'")
                    results["keys_synced"] = False

                    return results
                else:
                    log.warning("Selected key did not work")
                    results["recovered"] = False
                    return results

            except Exception as e:
                error_str = str(e)
                # Check for both AUTHENTICATION_DELAY (0x91AD) and AUTHENTICATION_ERROR (0x91AE)
                if (
                    "AUTHENTICATION_DELAY" in error_str
                    or hex(StatusWord.NTAG_AUTHENTICATION_DELAY) in error_str
                    or hex(StatusWord.NTAG_AUTHENTICATION_ERROR) in error_str
                ):
                    log.warning("Authentication error - tag may be in lockout mode (too many failed attempts)")
                    results["auth_delay"] = True
                else:
                    log.error(f"Error testing key: {e}")
                    results["error"] = str(e)
                return results

    def _sync_keys_to_tag(self, uid_bytes: bytes, old_keys, connection) -> None:
        """Generate new keys and write them to tag using Configure Keys.

        Args:
            uid_bytes: Tag UID
            old_keys: Current keys that work for authentication
            connection: Card connection
        """
        from ntag424_sdm_provisioner.commands.change_key import ChangeKey
        from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2

        log.info("Generating new random keys...")

        # Generate new random keys - wrap bytes UID in UID class for key manager
        uid = UID(uid_bytes)
        with self.key_manager.provision_tag(uid) as new_keys:
            # Keep status and notes
            new_keys.status = "keys_configured"
            new_keys.notes = f"Keys synced via recovery at {self._clock.now()}"

        # Now write the new keys to the tag
        log.info("Writing new keys to tag...")

        # Authenticate with current working key
        with AuthenticateEV2(old_keys.get_picc_master_key_bytes(), key_no=0)(connection) as auth_conn:
            # Change Key 0 (PICC Master Key)
            auth_conn.send(
                ChangeKey(
                    key_no_to_change=0,
                    new_key=new_keys.get_picc_master_key_bytes(),
                    old_key=old_keys.get_picc_master_key_bytes(),
                )
            )
            log.info("  Key 0 changed")

            # Change Key 1 (App Read Key)
            auth_conn.send(
                ChangeKey(
                    key_no_to_change=1,
                    new_key=new_keys.get_app_read_key_bytes(),
                    old_key=old_keys.get_app_read_key_bytes(),
                )
            )
            log.info("  Key 1 changed")

            # Change Key 3 (SDM MAC Key)
            auth_conn.send(
                ChangeKey(
                    key_no_to_change=3,
                    new_key=new_keys.get_sdm_mac_key_bytes(),
                    old_key=old_keys.get_sdm_mac_key_bytes(),
                )
            )
            log.info("  Key 3 changed")

        log.info("All keys successfully written to tag")
