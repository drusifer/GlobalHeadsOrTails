"""Service for formatting (factory reset) NTAG424 DNA tags."""

import logging
from collections.abc import Callable

from ntag424_sdm_provisioner.commands.format_picc import FormatPICC
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection


log = logging.getLogger(__name__)


class FormatService:
    """Service for formatting tags to factory defaults.

    WARNING: FormatPICC is destructive and cannot be undone!
    """

    def __init__(
        self,
        card: NTag424CardConnection,
        key_mgr: CsvKeyManager,
        progress_callback: Callable[[str], None] | None = None,
    ):
        self.card = card
        self.key_mgr = key_mgr
        self.progress_callback = progress_callback

    def _log(self, message: str):
        log.info(message, stacklevel=2)
        if self.progress_callback:
            self.progress_callback(message)

    def format_tag(self, picc_master_key: bytes) -> bool:
        """Format tag to factory defaults using FormatPICC command.

        Args:
            picc_master_key: Current PICC Master Key (Key 0) for authentication

        Returns:
            True if successful, raises exception on failure

        Raises:
            Exception if formatting fails
        """
        try:
            self._log("⚠⚠⚠ WARNING: Starting FORMAT PICC ⚠⚠⚠")
            self._log("This will ERASE all data and reset ALL keys to factory!")

            # Debug: Log PICC Master Key (first 8 bytes only for security)
            log.debug(f"PICC Master Key (first 8 bytes): {picc_master_key[:8].hex()}", stacklevel=2)

            # STEP 1: GET TAG UID
            self._log("[Step 1] Selecting PICC application...")
            self.card.send(SelectPiccApplication())
            log.debug("SelectPiccApplication completed", stacklevel=2)

            self._log("[Step 1] Reading tag UID...")
            version = self.card.send(GetChipVersion())
            self._log(f"  Tag UID: {version.uid}")
            log.debug(f"Full version info: {version}", stacklevel=2)

            # STEP 2: PRE-FLIGHT AUTH TEST
            self._log("[Step 2] Testing PICC Master Key authentication...")
            log.debug("Pre-flight: Testing authentication with Key 0", stacklevel=2)

            # Test authentication WITHOUT executing FormatPICC
            # If this fails, we stop before any destructive operation
            try:
                with AuthenticateEV2(picc_master_key, key_no=0)(self.card):
                    self._log("  ✓ Authentication test PASSED - key is correct")
                    log.debug("Pre-flight auth test successful", stacklevel=2)
            except Exception as auth_error:
                error_str = str(auth_error)
                if "AUTHENTICATION_ERROR" in error_str or "0x91AE" in error_str:
                    self._log("  ✗ Authentication test FAILED - wrong key")
                    raise ValueError(
                        "PICC Master Key authentication failed. "
                        "The key in the database does not match this tag. "
                        "Use Key Recovery to find the correct key first."
                    ) from auth_error
                else:
                    raise

            # STEP 3: AUTHENTICATE AND FORMAT
            self._log("[Step 3] Authenticating for FormatPICC command...")
            log.debug("Starting AuthenticateEV2 for FormatPICC", stacklevel=2)

            with AuthenticateEV2(picc_master_key, key_no=0)(self.card) as auth_conn:
                self._log("  ✓ Authenticated successfully")
                log.debug("AuthenticateEV2 session established", stacklevel=2)

                # STEP 4: SEND FORMAT PICC COMMAND
                self._log("[Step 4] Sending FORMAT PICC command (0xFC)...")
                self._log("  ⚠ This will reset the tag NOW - cannot be undone!")
                log.debug("About to send FormatPICC command", stacklevel=2)

                response = auth_conn.send(FormatPICC())
                log.debug(f"FormatPICC response: {response}", stacklevel=2)

                self._log("  ✓ Format command succeeded")

            # STEP 5: UPDATE DATABASE
            self._log("[Step 5] Updating database...")
            uid = version.uid  # Already a UID object
            log.debug(f"Attempting to update database for UID: {uid.uid}", stacklevel=2)
            try:
                # Try to get existing entry
                existing_keys = self.key_mgr.get_tag_keys(uid)
                log.debug(f"Found existing entry with status: {existing_keys.status}", stacklevel=2)

                # Update to reformatted status
                existing_keys.picc_master_key = "00000000000000000000000000000000"
                existing_keys.app_read_key = "00000000000000000000000000000000"
                existing_keys.sdm_mac_key = "00000000000000000000000000000000"
                existing_keys.status = "reformatted"
                existing_keys.notes = "Factory reset via FormatPICC - all keys now 0x00*16"

                self.key_mgr.save_tag_keys(existing_keys)
                log.debug("Database save completed successfully", stacklevel=2)
                self._log("  ✓ Database updated - tag marked as reformatted")
            except Exception as e:
                # Tag not in database - no update needed
                log.debug(f"Tag not in database (exception: {e})", stacklevel=2)
                self._log("  Tag not in database - no update needed")

            self._log("")
            self._log("✓✓✓ FORMAT COMPLETE ✓✓✓")
            self._log("Tag has been reset to factory defaults:")
            self._log("  - All keys: 0x00000000000000000000000000000000")
            self._log("  - All files reset")
            self._log("  - SDM disabled")
            self._log("  - All data erased")
            self._log("")
            self._log("You can now provision this tag from factory state.")

            return True

        except ValueError as e:
            # Pre-flight authentication test failed - clean error message
            error_str = str(e)
            self._log(f"✗ {error_str}")
            self._log("")
            self._log("⚠⚠⚠ WRONG PICC MASTER KEY ⚠⚠⚠")
            self._log("")
            self._log("The PICC Master Key in the database does NOT match this tag.")
            self._log("")
            self._log("To fix this:")
            self._log("  1. Go back to Main Menu")
            self._log("  2. Select 'Recover Lost Keys'")
            self._log("  3. Scan this tag to find candidate keys")
            self._log("  4. Test keys until you find one that works")
            self._log("  5. Click 'Restore Key' to save it to database")
            self._log("  6. Return to Format PICC and try again")
            self._log("")
            self._log("✓ IMPORTANT: The SAME key that works for Key Recovery")
            self._log("             WILL work for Format PICC.")
            self._log("")
            log.error(f"Format failed - wrong PICC Master Key (pre-flight test): {e}")
            raise

        except Exception as e:
            error_str = str(e)

            # Check for authentication errors during FormatPICC execution
            if "AUTHENTICATION_ERROR" in error_str or "0x91AE" in error_str:
                self._log(f"✗ Format failed: {e}")
                self._log("")
                self._log("⚠⚠⚠ AUTHENTICATION FAILED ⚠⚠⚠")
                self._log("")
                self._log("The PICC Master Key authentication failed.")
                self._log("This should NOT happen if the pre-flight test passed!")
                self._log("")
                self._log("Please report this issue with the log file.")
                self._log("")
                log.error(f"Format failed - unexpected auth failure after pre-flight: {e}", exc_info=True)
            elif "AUTHENTICATION_DELAY" in error_str or "0x91AD" in error_str:
                self._log(f"✗ Format failed: {e}")
                self._log("")
                self._log("⚠⚠⚠ TAG IN LOCKOUT MODE ⚠⚠⚠")
                self._log("")
                self._log("Too many failed authentication attempts.")
                self._log("The tag is temporarily locked.")
                self._log("")
                self._log("Please wait 30 seconds and try again.")
                self._log("")
                log.error(f"Format failed - authentication delay: {e}", exc_info=True)
            elif "ILLEGAL_COMMAND" in error_str or "0x911C" in error_str:
                self._log(f"✗ Format failed: {e}")
                self._log("")
                self._log("⚠⚠⚠ FORMAT PICC DISABLED ON THIS TAG ⚠⚠⚠")
                self._log("")
                self._log("This tag has FormatPICC permanently disabled.")
                self._log("This is a security feature to prevent factory reset attacks.")
                self._log("")
                self._log("You CANNOT factory reset this tag.")
                self._log("")
                self._log("Alternative recovery options:")
                self._log("  1. Use Key Recovery to find Keys 1 and 3")
                self._log("  2. Use Configure Keys to change keys (non-destructive)")
                self._log("  3. Use Setup URL to reconfigure SDM provisioning")
                self._log("")
                self._log("The tag remains fully functional - just cannot be reset.")
                self._log("")
                log.error(f"Format failed - FormatPICC disabled on tag: {e}", exc_info=True)
            else:
                self._log(f"✗ Format failed: {e}")
                log.error(f"Format failed: {e}", exc_info=True)

            raise
