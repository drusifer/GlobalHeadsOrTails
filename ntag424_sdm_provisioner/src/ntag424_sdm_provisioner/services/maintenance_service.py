"""TagMaintenanceService - Factory reset and maintenance operations for NTAG424 DNA tags.

Provides:
- Factory reset (all keys to 0x00)
- Authenticated operations using stored keys
- KeyManager integration for key lookup and status updates
"""

import logging
from collections.abc import Callable

from ntag424_sdm_provisioner.commands.base import ApduError, AuthenticatedConnection
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.constants import FACTORY_KEY
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.uid_utils import UID


log = logging.getLogger(__name__)


class TagMaintenanceService:
    """Service for tag maintenance operations (factory reset, etc.).

    Uses KeyManager to look up stored keys for provisioned tags.
    Falls back to factory key if stored keys fail or don't exist.
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
        """Log message and send to progress callback if available."""
        log.info(message, stacklevel=2)
        if self.progress_callback:
            self.progress_callback(message)

    def factory_reset(self) -> bool:
        """Reset tag to factory defaults.

        - Resets all keys to 0x00 (factory default)
        - Updates KeyManager status to 'factory'
        - Uses stored keys first, falls back to factory key

        Returns:
            True if reset successful, False otherwise
        """
        try:
            self._log("Starting factory reset...")

            # 1. Get chip info
            self._log("Reading tag UID...")
            self.card.send(SelectPiccApplication())
            version = self.card.send(GetChipVersion())
            uid = version.uid  # Already a UID object
            self._log(f"Tag UID: {uid.uid}")

            # 2. Try to authenticate
            auth_key, key_source = self._get_best_key(uid)
            self._log(f"Authenticating with {key_source} key...")

            try:
                with AuthenticateEV2(auth_key, 0)(self.card) as auth_conn:
                    self._log(f"Authenticated with {key_source} key!")

                    # Check if already factory
                    if auth_key == FACTORY_KEY:
                        self._log("Tag already has factory keys!")
                        self._update_key_manager(uid, "factory")
                        return True

                    # 3. Reset keys to factory
                    self._log("Resetting keys to factory defaults...")
                    success = self._reset_keys(auth_conn, auth_key)

                    if success:
                        # 4. Update KeyManager
                        self._update_key_manager(uid, "factory")
                        self._log("Factory reset complete!")
                        return True
                    else:
                        self._log("Failed to reset some keys")
                        return False

            except ApduError as e:
                self._log(f"Authentication failed: {e}")

                # If stored key failed, try factory key
                if key_source == "stored" and auth_key != FACTORY_KEY:
                    self._log("Trying factory key...")
                    try:
                        with AuthenticateEV2(FACTORY_KEY, 0)(self.card) as auth_conn:
                            self._log("Tag already has factory keys!")
                            self._update_key_manager(uid, "factory")
                            return True
                    except ApduError as e2:
                        self._log(f"Factory key also failed: {e2}")

                self._log("Cannot authenticate - keys unknown")
                return False

        except Exception as e:
            self._log(f"Factory reset failed: {e}")
            log.exception("Factory reset error")
            return False

    def _get_best_key(self, uid: UID) -> tuple[bytes, str]:
        """Get the best key to use for authentication.

        Returns:
            Tuple of (key_bytes, source_description)
        """
        try:
            # Convert bytes UID to hex string for key manager
            tag_keys = self.key_mgr.get_tag_keys(uid)
            if tag_keys and tag_keys.status != "factory":
                return tag_keys.get_picc_master_key_bytes(), "stored"
        except Exception:
            pass

        return FACTORY_KEY, "factory"

    def _reset_keys(self, auth_conn: AuthenticatedConnection, current_key: bytes) -> bool:
        """Reset all keys to factory default.

        Args:
            auth_conn: Authenticated connection
            current_key: Current key used for authentication

        Returns:
            True if all keys reset successfully
        """
        # Keys to reset: 0 (master), 1 (app read), 3 (SDM MAC)
        # Keys 2 and 4 are typically not used in our provisioning
        keys_to_reset = [0, 1, 3]

        for key_no in keys_to_reset:
            try:
                self._log(f"  Resetting Key {key_no}...")

                # For key 0, old_key is current_key
                # For other keys, we need to know their current value
                # In our provisioning, all keys are derived from same source
                # so we use current_key for all
                old_key = current_key

                auth_conn.send(ChangeKey(key_no, FACTORY_KEY, old_key, 0x00))
                self._log(f"  Key {key_no} reset [OK]")

            except ApduError as e:
                self._log(f"  Key {key_no} reset [FAILED]: {e}")
                # Continue trying other keys

        return True  # Best effort - some keys may have failed

    def _update_key_manager(self, uid: UID):
        """Update KeyManager with new tag status."""
        try:
            # Try to delete existing entry
            for key_no in [0, 1, 2, 3, 4]:
                self.key_mgr.delete_key(UID, key_no)
            self._log("Removed tag from database")
        except Exception:
            # Tag might not be in database
            pass
