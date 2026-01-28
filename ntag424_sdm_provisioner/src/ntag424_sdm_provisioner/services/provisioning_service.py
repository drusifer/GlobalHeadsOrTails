import logging
import traceback
from collections.abc import Callable

from ntag424_sdm_provisioner.commands.change_file_settings import (
    ChangeFileSettingsAuth,
)
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_file_settings import GetFileSettings
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOSelectFile
from ntag424_sdm_provisioner.commands.sdm_helpers import calculate_sdm_offsets
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.sun_commands import build_ndef_uri_record
from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.constants import (
    GAME_COIN_BASE_URL,
    AccessRight,
    AccessRights,
    AccessRightsPresets,
    CommMode,
    FileOption,
    SDMConfiguration,
    SDMUrlTemplate,
)
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, Outcome, TagKeys
from ntag424_sdm_provisioner.hal import NTag424CardConnection


log = logging.getLogger(__name__)


class ProvisioningService:
    """Core business logic for provisioning NTAG424 DNA tags.

    UI-agnostic: uses callbacks for progress updates.

    CORRECT SEQUENCE (per SUCCESSFUL_PROVISION_FLOW.md):
    1. SelectPiccApplication
    2. GetChipVersion (get UID)
    3. Generate new keys, save with status='pending'
    4. Session 1: Auth with current Key 0, ChangeKey 0 → session invalidates
    5. Session 2: Auth with NEW Key 0, ChangeKey 1 & 3
    6. Still in Session 2: Configure SDM + Write NDEF
    7. Update status='provisioned'
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

    def _is_factory_state(self, key0_ver: int, key1_ver: int, key3_ver: int) -> bool:
        """Detect if tag is in factory state based on key versions.

        Factory tags have all key versions = 0x00.
        Provisioned tags have key versions > 0x00 (typically 0x01).
        """
        return key0_ver == 0x00 and key1_ver == 0x00 and key3_ver == 0x00

    def provision_keys(self) -> bool:
        """Phase 1: Set cryptographic keys on tag (factory → keys_configured).

        This is separate from URL configuration to avoid burning through keys
        on URL-related failures. After this completes, the tag has:
        - Custom PICC Master Key (Key 0)
        - Custom App Read Key (Key 1)
        - Custom SDM MAC Key (Key 3)
        - Status: 'keys_configured'

        The tag is ready for provision_url() but SDM is not yet enabled.
        """
        try:
            self._log("Starting key provisioning (Phase 1)...")

            # STEP 1: GET TAG STATUS
            self._log("[Step 1] Selecting PICC application...")
            self.card.send(SelectPiccApplication())

            self._log("[Step 1] Reading tag UID...")
            version = self.card.send(GetChipVersion())
            self._log(f"  Tag UID: {version.uid}")

            # Check key versions
            self._log("[Step 1] Reading key versions...")
            key0_resp = self.card.send(GetKeyVersion(key_no=0))
            key1_resp = self.card.send(GetKeyVersion(key_no=1))
            key3_resp = self.card.send(GetKeyVersion(key_no=3))
            self._log(f"  Key Versions - 0:{key0_resp}, 1:{key1_resp}, 3:{key3_resp}")

            # Check database state
            self._log("[Step 1] Checking key state in database...")
            uid = version.uid  # Already a UID object
            try:
                current_keys = self.key_mgr.get_tag_keys(uid)
                self._log(f"  {uid.uid} Found in database (status={current_keys.status}): {current_keys=}")
            except Exception:
                current_keys = None
                self._log(f"  {uid.uid} Not in database - assuming factory state")

            # Detect tag state - HARDWARE IS SOURCE OF TRUTH
            is_factory = self._is_factory_state(
                key0_resp.version, key1_resp.version, key3_resp.version
            )
            self._log(f"[Step 1] Tag state: {'FACTORY' if is_factory else 'PROVISIONED'}")

            # Validate state consistency
            if current_keys:
                # Check if we have a verified PICC Master Key
                picc_is_set = current_keys.picc_master_key != "00000000000000000000000000000000"

                # If we have a real PICC key in DB, tag is NOT factory even if versions are 0x00
                # Key version 0x00 just means version hasn't been incremented, NOT that key is factory
                db_is_factory = current_keys.status in ("factory", "reformatted", "pending") and not picc_is_set

                if is_factory != db_is_factory:
                    if picc_is_set:
                        # We have a verified PICC key - override hardware "factory" detection
                        self._log(
                            "  INFO: Hardware shows key versions 0x00 but DB has verified PICC Master Key"
                        )
                        self._log(f"  DB status: {current_keys.status}")
                        self._log("  Key version 0x00 doesn't mean factory - it means version not incremented")
                        is_factory = False  # Override: tag is NOT factory if we have working PICC key
                    else:
                        self._log(
                            f"  WARNING: Tag/DB state mismatch - Tag={'FACTORY' if is_factory else 'PROVISIONED'}, DB status={current_keys.status}"
                        )
                        self._log("  TRUSTING TAG HARDWARE (key versions are source of truth)")

            # Determine current PICC master key - ALWAYS USE KEY MANAGER KEYS
            # ONLY use factory keys if tag is NOT in key manager
            if not current_keys:
                # Tag not in database - ONLY THEN try factory keys
                if is_factory:
                    current_picc_key = bytes(16)  # Factory key (all zeros)
                    old_keys = None
                    self._log("  Tag not in database AND hardware shows factory state")
                    self._log("  Using factory keys (all zeros)")
                else:
                    raise ValueError(
                        "Tag is provisioned (key versions > 0) but not in database! "
                        "Cannot authenticate. Use Key Recovery to find the correct keys."
                    )
            else:
                # Tag IS in database - ALWAYS use database keys
                current_picc_key = current_keys.get_picc_master_key_bytes()
                old_keys = current_keys
                self._log(f"  Tag found in database (status={current_keys.status})")
                self._log("  Using PICC Master Key from database for authentication")

                # Check if we have incomplete keys (e.g., from log file recovery)
                app_read_is_zero = current_keys.app_read_key == "00000000000000000000000000000000"
                sdm_mac_is_zero = current_keys.sdm_mac_key == "00000000000000000000000000000000"

                if app_read_is_zero or sdm_mac_is_zero:
                    self._log("  ⚠ WARNING: Partial key set detected (App Read or SDM MAC is all zeros)")
                    self._log("  Will attempt ChangeKey assuming old App/SDM keys are factory (all zeros)")
                    self._log("")
                    self._log("  ⚠⚠⚠ IMPORTANT ⚠⚠⚠")
                    self._log("  If ChangeKey fails with INTEGRITY_ERROR (0x911E):")
                    self._log("    - Keys 1/3 are NOT factory - they are unknown custom keys")
                    self._log("    - Use Key Recovery to find the actual App Read and SDM MAC keys")
                    self._log("    - You cannot proceed without all 3 keys")
                    self._log("")
                else:
                    self._log("  Complete key set found - will use ChangeKey with existing keys")

            # STEP 2: SET KEYS
            self._log("[Step 2] Starting key provisioning...")

            with self.key_mgr.provision_tag(version.uid, url=None) as new_keys:
                self._log("  New keys generated (status='pending')")
                self._log(f"  PICC Master: {new_keys.picc_master_key[:16]}...")
                self._log(f"  App Read:    {new_keys.app_read_key[:16]}...")
                self._log(f"  SDM MAC:     {new_keys.sdm_mac_key[:16]}...")

                # SESSION 1: Change Key 0
                self._log("[SESSION 1] Changing PICC Master Key (Key 0)...")
                try:
                    self._change_key_0(current_picc_key, new_keys)
                    self._log("  Key 0 changed → session invalidated")
                except Exception as e:
                    error_str = str(e)
                    # Check for authentication error (0x91AE) - tag not in expected state
                    if "AUTHENTICATION_ERROR" in error_str or "0x91AE" in error_str:
                        self._log("✗ AUTHENTICATION FAILED (0x91AE)")
                        self._log("")
                        self._log("This means the tag is NOT in the expected state:")
                        if is_factory:
                            self._log("  • Database thinks tag is FACTORY, but authentication with factory keys failed")
                            self._log("  • Tag may have been partially provisioned or keys were changed")
                        else:
                            self._log("  • Database has custom keys, but they don't match the tag")
                            self._log("  • Keys may have been lost or database is out of sync")
                        self._log("")
                        self._log("SOLUTION: Use 'Key Recovery' tool to:")
                        self._log("  1. Scan backup files for this tag's UID")
                        self._log("  2. Test candidate keys against the physical tag")
                        self._log("  3. Restore working keys to the database")

                        # Mark tag as needing recovery in database
                        new_keys.status = "needs_recovery"
                        new_keys.notes = f"Auth failed (0x91AE) - expected state: {'factory' if is_factory else 'provisioned'}"
                        raise ValueError(
                            "Authentication failed - tag state doesn't match database. Use Key Recovery tool."
                        ) from e
                    else:
                        # Re-raise other errors
                        raise

                # SESSION 2: Re-auth with NEW Key 0, change Keys 1 & 3
                self._log("[SESSION 2] Re-authenticating with NEW Key 0...")
                new_picc_key = new_keys.get_picc_master_key_bytes()

                with AuthenticateEV2(new_picc_key, key_no=0)(self.card) as auth_conn:
                    self._log("  Authenticated with NEW Key 0")

                    # Determine old Key 1 (App Read Key)
                    # Use factory key (all zeros) if not in database OR if database has all zeros
                    if old_keys:
                        old_key_1_bytes = old_keys.get_app_read_key_bytes()
                        # Check if it's all zeros (incomplete recovery from log)
                        if old_key_1_bytes == bytes(16):
                            self._log("  Old App Read Key is all zeros (factory/unknown) - using factory key for ChangeKey")
                    else:
                        old_key_1_bytes = bytes(16)  # Factory key
                        self._log("  No old keys in database - using factory key for ChangeKey")

                    auth_conn.send(
                        ChangeKey(
                            key_no_to_change=1,
                            new_key=new_keys.get_app_read_key_bytes(),
                            old_key=old_key_1_bytes,
                        )
                    )
                    self._log("  Key 1 changed")

                    # Determine old Key 3 (SDM MAC Key)
                    # Use factory key (all zeros) if not in database OR if database has all zeros
                    if old_keys:
                        old_key_3_bytes = old_keys.get_sdm_mac_key_bytes()
                        # Check if it's all zeros (incomplete recovery from log)
                        if old_key_3_bytes == bytes(16):
                            self._log("  Old SDM MAC Key is all zeros (factory/unknown) - using factory key for ChangeKey")
                    else:
                        old_key_3_bytes = bytes(16)  # Factory key
                        self._log("  No old keys in database - using factory key for ChangeKey")

                    auth_conn.send(
                        ChangeKey(
                            key_no_to_change=3,
                            new_key=new_keys.get_sdm_mac_key_bytes(),
                            old_key=old_key_3_bytes,
                        )
                    )
                    self._log("  Key 3 changed")

                self._log("  SESSION 2 complete - Keys 0, 1, 3 changed")

            # Context manager updates status to 'keys_configured' on success
            self._log("Key provisioning complete! Tag status: keys_configured")
            self._log("Next: Use provision_url() to configure SDM and NDEF")
            return True

        except Exception as e:
            self._log(f"Error: {e}")
            log.error(traceback.format_exc())
            return False

    def provision_url(self, base_url: str = GAME_COIN_BASE_URL) -> bool:
        """Phase 2: Configure SDM and NDEF URL (keys_configured → provisioned).

        Prerequisites:
        - Tag must have custom keys (status='keys_configured' or 'provisioned')
        - Keys must be in database

        This configures:
        - SDM settings on NDEF file
        - NDEF URL record with placeholders
        - Status: 'provisioned'
        """
        try:
            self._log("Starting URL provisioning (Phase 2)...")

            # STEP 1: GET TAG STATUS
            self._log("[Step 1] Selecting PICC application...")
            self.card.send(SelectPiccApplication())

            self._log("[Step 1] Reading tag UID...")
            version = self.card.send(GetChipVersion())
            uid = version.uid  # Already a UID object
            self._log(f"  Tag UID: {uid.uid}")

            # Get keys from database
            self._log("[Step 1] Loading keys from database...")
            try:
                current_keys = self.key_mgr.get_tag_keys(uid)
                self._log(f"  Found in database (status={current_keys.status})")
                # DEBUG: Log all keys that will be used
                self._log("[URL PROVISIONING] Keys loaded from database:")
                self._log(f"  PICC Master Key: {current_keys.picc_master_key}")
                self._log(f"  App Read Key: {current_keys.app_read_key}")
                self._log(f"  SDM MAC Key (Key 3): {current_keys.sdm_mac_key}")
                self._log(f"  Database path: {self.key_mgr.csv_path}")
            except Exception as e:
                raise ValueError("Tag not in database! Run provision_keys() or key recovery first.") from e

            config = SDMConfiguration(
                file_no=0x02,
                comm_mode=CommMode.MAC,
                access_rights=AccessRightsPresets.FREE_READ_KEY0_WRITE,
                enable_sdm=True,
                sdm_options=FileOption.UID_MIRROR | FileOption.READ_COUNTER,
                sdm_url=SDMUrlTemplate(base_url=base_url)
            )
            
            self._log(f"Calculated SDM offsets...{config.offsets}")
            template = config.sdm_url
            offsets = config.offsets
            ndef_message = config.build_ndef_record()
            self._log(f"  Generated NDEF URL template: {template}")
            self._log(f"  Offsets are :{offsets}")
            self._log(f"  NDEF is :{ndef_message}")

            # STEP 3: CONFIGURE SDM THEN WRITE NDEF
            # FIX (2025-12-12): Write NDEF *BEFORE* Configuring SDM
            # We write NDEF using plain ISO commands while Write Access is still FREE.
            # This avoids "Reference before Content" issues and SMConfig limitations.
            self._log("[Step 3] Writing NDEF then Configuring SDM...")
            picc_key = current_keys.get_picc_master_key_bytes()

            self._log("  Writing NDEF message (Plain/Unauthenticated)...")
            self._write_ndef(ndef_message)
            self._log("  NDEF written.")

            with AuthenticateEV2(picc_key, key_no=0)(self.card) as auth_conn:
                self._log("  Authenticated with PICC Master Key")

                # Configure SDM
                self._log("  Configuring SDM...")
                self._log(f"  SDM Offsets: UID={offsets.uid_offset}, CTR={offsets.read_ctr_offset}, CMAC={offsets.mac_offset}")
                self._log(f"  SDM Offsets: mac_input_offset={offsets.mac_input_offset}, picc_data_offset={offsets.picc_data_offset}")
                self._configure_sdm(auth_conn, config)
                self._log("  SDM configured.")

            self._log("  Session ended.")

            # Update URL and status in database
            current_keys.status = "provisioned"
            current_keys.notes = base_url
            self.key_mgr.save_tag_keys(current_keys)

            self._log("URL provisioning complete! Tag status: provisioned")
            return True

        except Exception as e:
            self._log(f"Error: {e}")
            log.error(traceback.format_exc())
            return False

    def provision(
        self,
        base_url: str = GAME_COIN_BASE_URL,
        coin_name: str = "",
        outcome: Outcome = Outcome.INVALID,
    ) -> bool:
        """Execute complete provisioning workflow with 3-session approach.

        CORRECT SEQUENCE (per SDM_SETUP_SEQUENCE.md):
        STEP 1: Get tag status (SelectPiccApplication, GetChipVersion, GetFileSettings, GetKeyVersion)
        STEP 2: If factory → Set keys
          SESSION 1: Auth factory Key 0 → ChangeKey(0) → session invalidates
          SESSION 2: Auth NEW Key 0 → ChangeKey(1, 3)
        STEP 3: If keys set → Write NDEF then Configure SDM
          SESSION 3: Auth NEW Key 0 → Write NDEF → ChangeFileSettings

        CRITICAL: NDEF must be written BEFORE ChangeFileSettings because:
        - SDM offsets reference positions in file content
        - Empty file causes PARAMETER_ERROR (0x919E)
        - Spec Section 9.3.6: "placeholder within the file"

        Args:
            base_url: Base URL for SDM configuration
            coin_name: Optional coin identifier (e.g., "SWIFT-FALCON-42")
            outcome: Optional outcome (HEADS | TAILS | INVALID for unassigned)
        """
        try:
            self._log("Starting provisioning...")

            # STEP 1: GET TAG STATUS
            # 1a. Select PICC Application (MUST BE FIRST!)
            self._log("[Step 1] Selecting PICC application...")
            self.card.send(SelectPiccApplication())

            # 1b. Get Chip Info (UID)
            self._log("[Step 1] Reading tag UID...")
            version = self.card.send(GetChipVersion())
            uid = version.uid  # Already a UID object
            self._log(f"  Tag UID: {uid.uid}")

            # 1c. Get File Settings (detect current SDM configuration)
            self._log("[Step 1] Reading file settings...")
            file_settings = self.card.send(GetFileSettings(file_no=0x02))
            self._log(f"  File 0x02 CommMode: {file_settings.get_comm_mode()}")

            # 1d. Get Key Versions (detect factory vs provisioned)
            self._log("[Step 1] Reading key versions...")
            key0_resp = self.card.send(GetKeyVersion(key_no=0))
            key1_resp = self.card.send(GetKeyVersion(key_no=1))
            key3_resp = self.card.send(GetKeyVersion(key_no=3))
            self._log(f"  Key Versions - 0:{key0_resp}, 1:{key1_resp}, 3:{key3_resp}")

            # 1e. Check Key State in database
            self._log("[Step 1] Checking key state in database...")
            try:
                current_keys = self.key_mgr.get_tag_keys(uid)
                self._log(f"  Found in database (status={current_keys.status})")
            except Exception:
                current_keys = None
                self._log("  Not in database - assuming factory state")

            # 1f. Detect tag state (factory vs provisioned) - HARDWARE IS SOURCE OF TRUTH
            is_factory = self._is_factory_state(
                key0_resp.version, key1_resp.version, key3_resp.version
            )
            self._log(f"[Step 1] Tag state: {'FACTORY' if is_factory else 'PROVISIONED'}")

            # Validate state consistency with database
            if current_keys:
                db_is_factory = current_keys.status in ("factory", "reformatted", "pending", "failed")
                if is_factory != db_is_factory:
                    self._log(
                        f"  WARNING: Tag/DB state mismatch - Tag={'FACTORY' if is_factory else 'PROVISIONED'}, DB status={current_keys.status}"
                    )
                    self._log("  TRUSTING TAG HARDWARE (key versions are source of truth)")

            # Determine current PICC master key based on ACTUAL TAG STATE (not DB)
            if is_factory:
                # Tag has factory keys (all key versions = 0x00) - use factory key
                current_picc_key = bytes(16)  # Factory key (all zeros)
                old_keys = None
                self._log("  Using factory keys (all zeros)")
            else:
                # Tag has custom keys (key versions > 0x00) - use keys from database
                if not current_keys:
                    raise ValueError(
                        "Tag is provisioned (key versions > 0) but not in database! Cannot authenticate."
                    )
                current_picc_key = current_keys.get_picc_master_key_bytes()
                old_keys = current_keys  # For XOR calculation on Keys 1, 3
                self._log(f"  Using custom keys from database (status={current_keys.status})")

            # 4. Calculate SDM offsets and build NDEF
            self._log("Calculating SDM offsets...")
            template = SDMUrlTemplate(
                base_url=base_url,
                uid_placeholder="00000000000000",
                cmac_placeholder="0000000000000000",
                read_ctr_placeholder="000000",
                enc_placeholder=None,
            )
            offsets = calculate_sdm_offsets(template)
            url_template = template.generate_url(
                uid="00000000000000", read_ctr=0, cmac="0000000000000000"
            )
            ndef_message = build_ndef_uri_record(url_template)

            # STEP 2: IF FACTORY → SET KEYS
            self._log("[Step 2] Starting two-phase key provisioning...")

            with self.key_mgr.provision_tag(
                version.uid, url=base_url, coin_name=coin_name, outcome=outcome
            ) as new_keys:
                self._log("  New keys generated (status='pending')")
                if coin_name:
                    self._log(f"  Coin: {coin_name} ({outcome.value})")
                self._log(f"  PICC Master: {new_keys.picc_master_key[:16]}...")
                self._log(f"  App Read:    {new_keys.app_read_key[:16]}...")
                self._log(f"  SDM MAC:     {new_keys.sdm_mac_key[:16]}...")

                # SESSION 1: Change Key 0 (invalidates session!)
                self._log("[SESSION 1] Changing PICC Master Key (Key 0)...")
                try:
                    self._change_key_0(current_picc_key, new_keys)
                    self._log("  Key 0 changed → session invalidated")
                except Exception as e:
                    error_str = str(e)
                    # Check for authentication error (0x91AE) - tag not in expected state
                    if "AUTHENTICATION_ERROR" in error_str or "0x91AE" in error_str:
                        self._log("✗ AUTHENTICATION FAILED (0x91AE)")
                        self._log("")
                        self._log("This means the tag is NOT in the expected state:")
                        if is_factory:
                            self._log("  • Database thinks tag is FACTORY, but authentication with factory keys failed")
                            self._log("  • Tag may have been partially provisioned or keys were changed")
                        else:
                            self._log("  • Database has custom keys, but they don't match the tag")
                            self._log("  • Keys may have been lost or database is out of sync")
                        self._log("")
                        self._log("SOLUTION: Use 'Key Recovery' tool to:")
                        self._log("  1. Scan backup files for this tag's UID")
                        self._log("  2. Test candidate keys against the physical tag")
                        self._log("  3. Restore working keys to the database")

                        # Mark tag as needing recovery in database
                        new_keys.status = "needs_recovery"
                        new_keys.notes = f"Auth failed (0x91AE) - expected state: {'factory' if is_factory else 'provisioned'}"
                        raise ValueError(
                            "Authentication failed - tag state doesn't match database. Use Key Recovery tool."
                        ) from e
                    else:
                        # Re-raise other errors
                        raise

                # SESSION 2: Re-auth with NEW Key 0, change Keys 1 & 3 ONLY
                self._log("[SESSION 2] Re-authenticating with NEW Key 0...")
                new_picc_key = new_keys.get_picc_master_key_bytes()

                with AuthenticateEV2(new_picc_key, key_no=0)(self.card) as auth_conn:
                    self._log("  Authenticated with NEW Key 0")

                    # Change Key 1 (App Read)
                    old_key_1 = old_keys.get_app_read_key_bytes() if old_keys else bytes(16)
                    auth_conn.send(
                        ChangeKey(
                            key_no_to_change=1,
                            new_key=new_keys.get_app_read_key_bytes(),
                            old_key=old_key_1,
                        )
                    )
                    self._log("  Key 1 changed")

                    # Change Key 3 (SDM MAC)
                    old_key_3 = old_keys.get_sdm_mac_key_bytes() if old_keys else bytes(16)
                    auth_conn.send(
                        ChangeKey(
                            key_no_to_change=3,
                            new_key=new_keys.get_sdm_mac_key_bytes(),
                            old_key=old_key_3,
                        )
                    )
                    self._log("  Key 3 changed")

                self._log("  SESSION 2 complete - Keys 1 & 3 changed")

                # STEP 3: IF KEYS SET → CONFIGURE SDM THEN WRITE NDEF
                # CRITICAL: The order of operations must be:
                # 1. Authenticate with PICC Master Key.
                # 2. Use the authenticated session to send ChangeFileSettings. This command
                #    MUST be sent authenticated to change the file access rights.
                # 3. End the session.
                # 4. Write the NDEF file using unauthenticated ISOUpdateBinary commands.
                # FIX (2025-12-12): Write NDEF *BEFORE* Configuring SDM
                # If we configure SDM first, it sets Write Access to Key 0.
                # We must write the NDEF while Write Access is still FREE (Factory state).
                self._log("  Writing NDEF message (Plain/Unauthenticated)...")
                self._write_ndef(ndef_message)
                self._log("  NDEF written.")

                self._log("[SESSION 3] Re-authenticating for SDM config...")
                with AuthenticateEV2(new_picc_key, key_no=0)(self.card) as auth_conn:
                    self._log("  Authenticated with NEW Key 0")

                    # Configure SDM FIRST to change file permissions to allow plain writes
                    self._log("  Configuring SDM...")
                    self._configure_sdm(auth_conn, offsets)

                self._log("  Session ended. SDM configured.")

                self._log("  SESSION 3 complete - NDEF written, SDM configured")
                self._log("[Step 3] All configuration complete!")

            # Context manager updates status to 'provisioned' on success
            self._log("Provisioning complete!")
            return True

        except Exception as e:
            self._log(f"Error: {e}")
            log.error(traceback.format_exc())
            return False

    def _change_key_0(self, current_picc_key: bytes, new_keys: TagKeys):
        """Session 1: Change PICC Master Key (Key 0). Session invalidates after this!"""
        with AuthenticateEV2(current_picc_key, key_no=0)(self.card) as auth_conn:
            auth_conn.send(
                ChangeKey(
                    key_no_to_change=0,
                    new_key=new_keys.get_picc_master_key_bytes(),
                    old_key=bytes(16),
                )
            )

    def _configure_sdm(self, auth_conn, config: SDMConfiguration):
        """Configure SDM settings on NDEF file.

        CRITICAL FIX (2025-12-07):
        ChangeFileSettings MUST be sent authenticated (encrypted + CMAC) per NXP spec,
        even when the file's 'change' access right is FREE. The previous implementation
        was sending it PLAIN which caused LENGTH_ERROR (0x917E).

        Reference: CHANGEFILESETTINGS_AUTH_FIX.md, tui_20251207_182114.log line 261-263
        """
        access_rights = AccessRights(
            read=AccessRight.FREE,
            write=AccessRight.KEY_0,
            read_write=AccessRight.FREE,
            change=AccessRight.FREE,
        )
        config.access_rights = access_rights

        # CRITICAL: Use ChangeFileSettingsAuth to send encrypted + CMAC
        # The command MUST be authenticated even though the file's change access is FREE
        auth_conn.send(ChangeFileSettingsAuth(config))

    def _write_ndef(self, ndef_message: bytes):
        """Write NDEF message using chunked unauthenticated ISO writes.

        This should be called *after* ChangeFileSettings has been used to set
        the NDEF file's Write access right to FREE. This method uses ISOUpdateBinary
        (0xD6), which is always sent in CommMode.PLAIN (unauthenticated).
        """
        self.card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
        self.card.send(WriteNdefMessage(ndef_data=ndef_message))
        self.card.send(SelectPiccApplication())
