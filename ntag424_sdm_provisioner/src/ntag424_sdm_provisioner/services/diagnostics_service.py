import logging
from typing import Any

from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion, Ntag424VersionInfo
from ntag424_sdm_provisioner.commands.get_file_settings import FileSettingsResponse, GetFileSettings
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOReadBinary, ISOSelectFile
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.constants import FileNo, TagStatus
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.tools.tool_helpers import read_ndef_file
from ntag424_sdm_provisioner.uid_utils import UID


log = logging.getLogger(__name__)


class TagDiagnosticsService:
    """Service for retrieving diagnostic information from NTAG424 DNA tags.

    Provides methods to:
    - Check tag status (Factory/Provisioned)
    - Get chip version and manufacturing info
    - Get key versions (authenticated if keys available)
    - Get file settings (authenticated if keys available)
    - Read NDEF and CC files

    IMPORTANT: This service checks the key manager to avoid burning auth attempts.
    Commands are sent authenticated when keys are available, unauthenticated otherwise.
    """

    def __init__(self, card: NTag424CardConnection, key_mgr: CsvKeyManager):
        self.card = card
        self.key_mgr = key_mgr
        self._cached_keys: TagKeys | None = None
        self._keys_checked = False
        self._cached_uid: UID | None = None

    def _ensure_uid_and_keys_loaded(self) -> None:
        """Load UID and check key manager for available keys.

        CRITICAL: Always call this before attempting any operation that might
        require authentication to avoid burning auth attempts.
        """
        if self._keys_checked:
            return

        # Get UID
        if not self._cached_uid:
            try:
                version = self.card.send(GetChipVersion())
                self._cached_uid = version.uid  # Already a UID object
                log.info(f"Tag UID: {self._cached_uid.uid}")
            except Exception as e:
                log.error(f"Failed to get UID: {e}")
                self._keys_checked = True
                return

        # Check if we have keys for this UID
        try:
            # Convert bytes UID to hex string for key manager
            self._cached_keys = self.key_mgr.get_tag_keys(self._cached_uid)
            if self._cached_keys:
                log.info(f"Found keys in database (status={self._cached_keys.status})")
            else:
                log.info("No keys in database - tag may be factory or unprovisioned")
        except Exception:
            log.info("No keys in database - tag may be factory or unprovisioned")
            self._cached_keys = None

        self._keys_checked = True

    def get_tag_status(self) -> TagStatus:
        """Determine the status of the tag (Factory, Provisioned, or Unknown).

        Returns:
            TagStatus enum value.
        """
        try:
            # Try to read UID to ensure we are connected
            version = self.card.send(GetChipVersion())

            # Check if keys exist in our database
            try:
                # version.uid is already a UID object
                tag_keys = self.key_mgr.get_tag_keys(version.uid)
                if tag_keys and tag_keys.status != "factory":
                    return TagStatus.PROVISIONED
            except Exception:
                pass  # Not in DB or error reading DB

            # If not in DB, check if it behaves like a factory tag (Key 0 is default)
            # We can try to authenticate with default key 0, but that changes state.
            # A safer check is GetKeyVersion for Key 0. Factory tags usually have version 0 or 1.
            # But the most reliable "status" for our app is "Do we have keys for it?".

            return TagStatus.FACTORY

        except Exception as e:
            log.error(f"Error determining tag status: {e}")
            return TagStatus.UNKNOWN

    def get_chip_info(self) -> Ntag424VersionInfo | None:
        """Get chip hardware and software version information."""
        try:
            return self.card.send(GetChipVersion())  # type: ignore[no-any-return]
        except Exception as e:
            log.error(f"Failed to get chip version: {e}")
            return None

    def get_key_versions(self) -> dict[str, str]:
        """Get versions of all 5 keys.

        NOTE: GetKeyVersion doesn't require authentication on most tags.
        We still check key manager to provide better error messages.
        """
        self._ensure_uid_and_keys_loaded()

        versions = {}

        # GetKeyVersion works without authentication on most tags
        # Try reading all key versions directly
        log.info("Reading key versions (unauthenticated)")
        for key_no in range(5):
            try:
                key_ver = self.card.send(GetKeyVersion(key_no))
                versions[f"key_{key_no}"] = f"0x{key_ver.version:02X}"
            except Exception as e:
                error_str = str(e)
                # Check for expected errors on provisioned tags
                if "NO_SUCH_KEY" in error_str or "0x9140" in error_str:
                    versions[f"key_{key_no}"] = "not set"
                elif "PERMISSION_DENIED" in error_str or "0x919D" in error_str:
                    versions[f"key_{key_no}"] = "protected"
                else:
                    log.debug(f"Failed to get key {key_no} version: {e}")
                    versions[f"key_{key_no}"] = "error"

        return versions

    def get_file_settings(self, file_no: int) -> FileSettingsResponse | None:
        """Get settings for a specific file.

        NOTE: GetFileSettings typically works without authentication on factory tags,
        but may require authentication on provisioned tags depending on file ACLs.
        """
        self._ensure_uid_and_keys_loaded()

        # Try unauthenticated first (works on factory tags and some provisioned tags)
        log.info(f"Reading file {file_no} settings (unauthenticated)")
        try:
            return self.card.send(GetFileSettings(file_no))  # type: ignore[no-any-return]
        except Exception as e:
            error_str = str(e)
            # Check for expected errors on provisioned tags
            if "PERMISSION_DENIED" in error_str or "0x919D" in error_str:
                if self._cached_keys:
                    log.info(f"File {file_no} settings require authentication")
                else:
                    log.info(f"File {file_no} settings require authentication (no keys in DB)")
            elif "too short" in error_str:
                log.info(f"File {file_no} settings not readable")
            else:
                log.error(f"Failed to get file settings for file {file_no}: {e}")
            return None

    def read_cc_file(self) -> dict[str, Any]:
        """Read Capability Container (CC) file."""
        try:
            self.card.send(ISOSelectFile(ISOFileID.CC_FILE))
            cc_data = self.card.send(ISOReadBinary(0, 15))
            self.card.send(SelectPiccApplication())  # Reselect App

            return {
                "raw": cc_data.hex().upper(),
                "magic": f"0x{int.from_bytes(cc_data[0:2], 'big'):04X}",
                "version": f"{cc_data[2]}.{cc_data[3]}",
                "max_size": int.from_bytes(cc_data[11:13], "big"),
            }
        except Exception as e:
            log.error(f"Failed to read CC file: {e}")
            return {"error": str(e)}

    def read_ndef(self) -> dict[str, Any]:
        """Read NDEF message from File 02."""
        try:
            ndef_data = read_ndef_file(self.card)
            return {
                "length": len(ndef_data),
                "preview": ndef_data[:100].hex().upper(),
                "data": ndef_data,
            }
        except Exception as e:
            log.error(f"Failed to read NDEF: {e}")
            return {"error": str(e)}

    def get_full_diagnostics(self) -> dict[str, Any]:
        """Collect all diagnostic information.

        Runs both unauthenticated and authenticated diagnostics when keys are available.
        """
        # Load UID and check for keys FIRST to avoid burning auth attempts
        self._ensure_uid_and_keys_loaded()

        diagnostics: dict[str, Any] = {}

        # Add key availability info and database status
        if self._cached_keys:
            diagnostics["key_status"] = f"Available in database (status={self._cached_keys.status})"
            diagnostics["database_status"] = {
                "in_database": True,
                "status": self._cached_keys.status,
                "provisioned_date": self._cached_keys.provisioned_date,
                "notes": self._cached_keys.notes,
            }
        else:
            diagnostics["key_status"] = "Not in database (factory or unknown)"
            diagnostics["database_status"] = {
                "in_database": False,
            }

        # === UNAUTHENTICATED COMMANDS ===
        log.info("Running unauthenticated diagnostics...")

        # Chip Info
        version = self.get_chip_info()
        if version:
            diagnostics["chip"] = {
                "uid": version.uid,
                "hw_version": f"{version.hw_major_version}.{version.hw_minor_version}",
                "sw_version": f"{version.sw_major_version}.{version.sw_minor_version}",
                "hw_storage": version.hw_storage_size,
                "batch": version.batch_no.hex().upper(),
                "fab_date": f"Week {version.fab_week}, 20{version.fab_year}",
            }
        else:
            diagnostics["chip"] = {"error": "Failed to read chip version"}

        # Key Versions (unauthenticated)
        diagnostics["key_versions_unauth"] = self.get_key_versions()

        # File Settings (NDEF) - unauthenticated
        settings = self.get_file_settings(FileNo.NDEF_FILE)
        if settings:
            diagnostics["file_settings_unauth"] = str(settings)
        else:
            diagnostics["file_settings_unauth"] = "Permission denied or not available"

        # CC File
        diagnostics["cc_file"] = self.read_cc_file()

        # NDEF
        diagnostics["ndef"] = self.read_ndef()

        # GetFileIds - list all files (UNAUTHENTICATED, must run before auth session)
        # NOTE: Not supported on all NTAG424 DNA tags
        try:
            from ntag424_sdm_provisioner.commands.get_file_ids import GetFileIds

            log.debug("Getting file IDs (unauthenticated)...")
            file_ids_response = self.card.send(GetFileIds())
            diagnostics["file_ids"] = [f"0x{fid:02X}" for fid in file_ids_response]
        except Exception as e:
            error_str = str(e)
            if "ILLEGAL_COMMAND" in error_str or "0x911C" in error_str:
                log.debug("GetFileIds not supported on this tag")
                diagnostics["file_ids"] = "Not supported"
            else:
                log.debug(f"GetFileIds error: {e}")
                diagnostics["file_ids"] = None

        # GetFileCounters - SDM read counter (UNAUTHENTICATED, must run before auth session)
        # NOTE: Only works when SDM is enabled
        try:
            from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters

            log.debug("Getting SDM file counters (unauthenticated)...")
            counter = GetFileCounters(file_no=FileNo.NDEF_FILE).execute(self.card)
            diagnostics["sdm_read_counter"] = counter
        except Exception as e:
            error_str = str(e)
            if "ILLEGAL_COMMAND" in error_str or "0x911C" in error_str:
                log.debug("GetFileCounters not supported (SDM may not be enabled)")
                diagnostics["sdm_read_counter"] = None
            else:
                log.debug(f"GetFileCounters error: {e}")
                diagnostics["sdm_read_counter"] = None

        # === PHONE TAP SIMULATION ===
        # Simulate what happens when a phone taps the tag
        diagnostics["sdm_validation"] = self._simulate_phone_tap()

        # === AUTHENTICATED COMMANDS (if keys available) ===
        # NOTE: No authenticated diagnostics needed currently since all commands
        # have been moved to unauthenticated section above
        if self._cached_keys:
            log.info("Authenticated diagnostics: skipped (no auth-only commands)")
            diagnostics["authenticated"] = "Available but not needed"
        else:
            diagnostics["authenticated"] = "No keys available"

        return diagnostics

    def _simulate_phone_tap(self) -> dict[str, Any]:
        """Simulate a phone tap by reading the NDEF URL and validating SDM.

        This reads the current NDEF content from the tag and validates the SDM
        parameters (if present) using the key manager.

        Returns:
            Dict with phone tap simulation results and Android NFC detection checks
        """
        log.info("=" * 70)
        log.info("[PHONE TAP SIMULATION] Starting Android tap simulation")
        log.info("=" * 70)

        result: dict[str, Any] = {
            "has_url": False,
            "url": None,
            "has_sdm": False,
            "validation": None,
            "android_nfc_checks": {
                "condition_1_read_access_free": False,
                "condition_2_ndef_format": False,
                "condition_3_cc_file_valid": False,
                "condition_4_offsets_valid": False,
                "all_conditions_pass": False,
            }
        }

        try:
            # Read NDEF data
            log.info("[PHONE TAP] Step 1: Reading NDEF file from tag...")
            ndef_info = self.read_ndef()
            ndef_data = ndef_info["data"]
            log.info(f"[PHONE TAP]   NDEF length: {len(ndef_data)} bytes")
            log.info(f"[PHONE TAP]   NDEF raw hex: {ndef_data.hex().upper()}")

            # Extract SDM configuration from NDEF
            log.info("[PHONE TAP] Step 2: Parsing NDEF to extract SDM URL...")
            from ntag424_sdm_provisioner.constants import SDMConfiguration

            sdm_config = SDMConfiguration.from_ndef_data(ndef_data)

            if not sdm_config or not sdm_config.sdm_url:
                result["error"] = "Could not extract URL from NDEF"
                log.info("[PHONE TAP]   ✗ URL extraction failed")
                return result

            result["has_url"] = True
            result["url"] = sdm_config.url
            result["sdm_config"] = sdm_config
            log.info("[PHONE TAP]   ✓ URL extracted successfully")
            log.info(f"[PHONE TAP]   Full URL: {sdm_config.url}")

            # Check if URL has SDM parameters
            result["has_sdm"] = sdm_config.has_sdm_parameters
            log.info("[PHONE TAP] Step 3: Checking for SDM parameters...")
            log.info(f"[PHONE TAP]   Has SDM parameters: {sdm_config.has_sdm_parameters}")

            if not sdm_config.has_sdm_parameters:
                result["info"] = "URL does not contain SDM parameters"
                log.info("[PHONE TAP]   (No SDM validation needed)")
            else:
                # Log the parsed SDM parameters
                log.info("[PHONE TAP] Step 4: SDM Parameters extracted from URL:")
                log.info(f"[PHONE TAP]   UID:     {sdm_config.uid}")
                log.info(f"[PHONE TAP]   Counter: {sdm_config.counter} (decimal)")
                log.info(f"[PHONE TAP]   Counter: {sdm_config.counter:06X} (hex)")
                log.info(f"[PHONE TAP]   CMAC:    {sdm_config.cmac}")

                # Log offset information if available
                if sdm_config.offsets:
                    log.info("[PHONE TAP]   SDM Offsets in NDEF file:")
                    log.info(f"[PHONE TAP]     UID offset:     {sdm_config.offsets.uid_offset}")
                    log.info(f"[PHONE TAP]     Counter offset: {sdm_config.offsets.read_ctr_offset}")
                    log.info(f"[PHONE TAP]     CMAC offset:    {sdm_config.offsets.mac_offset}")

                # Validate SDM using key manager
                log.info("[PHONE TAP] Step 5: Validating SDM CMAC...")
                # Convert string UID to UID object for validate_sdm_url
                uid_obj = UID(sdm_config.uid)
                validation = self.key_mgr.validate_sdm_url(uid_obj, sdm_config.counter, sdm_config.cmac)
                result["validation"] = validation

                # Log validation summary
                log.info("[PHONE TAP] Step 6: Validation result summary:")
                log.info(f"[PHONE TAP]   Valid:           {validation.get('valid', False)}")
                log.info(f"[PHONE TAP]   CMAC received:   {validation.get('cmac_received', 'N/A')}")
                log.info(f"[PHONE TAP]   CMAC calculated: {validation.get('cmac_calculated', 'N/A')}")
                if validation.get('sv2'):
                    log.info(f"[PHONE TAP]   SV2 used:        {validation.get('sv2')}")
                if validation.get('session_key'):
                    log.info(f"[PHONE TAP]   Session key:     {validation.get('session_key')}")

            # === ANDROID NFC DETECTION CHECKS ===
            log.info("[PHONE TAP] Step 7: Running Android NFC detection checks...")
            result["android_nfc_checks"] = self._check_android_nfc_conditions(ndef_data, sdm_config)

        except Exception as e:
            log.exception(f"[PHONE TAP] ✗ Simulation failed with exception: {e}")
            result["error"] = str(e)

        log.info("=" * 70)
        log.info(f"[PHONE TAP SIMULATION] Complete - has_url={result.get('has_url')}, has_sdm={result.get('has_sdm')}")
        log.info("=" * 70)
        return result

    def _check_android_nfc_conditions(self, ndef_data: bytes, sdm_config: Any) -> dict[str, Any]:
        """Check all 4 conditions required for Android NFC detection.

        Args:
            ndef_data: Raw NDEF file bytes
            sdm_config: SDMConfiguration object

        Returns:
            Dict with check results for each condition
        """
        from ntag424_sdm_provisioner.constants import (
            AccessRight,
            CCFileTLV,
            parse_ndef_file_data,
            validate_ndef_uri_record,
        )

        checks = {
            "condition_1_read_access_free": False,
            "condition_2_ndef_format": False,
            "condition_3_cc_file_valid": False,
            "condition_4_offsets_valid": False,
            "all_conditions_pass": False,
            "details": {}
        }

        # CONDITION 1: File 2 Read Access = FREE (0x00 or 0x0E)
        try:
            from ntag424_sdm_provisioner.constants import AccessRights

            file_settings = self.get_file_settings(FileNo.NDEF_FILE)
            if file_settings and file_settings.access_rights:
                # Parse raw bytes into AccessRights object
                access_rights = AccessRights.from_bytes(file_settings.access_rights)
                read_access = access_rights.read
                checks["condition_1_read_access_free"] = (read_access == AccessRight.FREE)
                # Use enum name for better readability
                checks["details"]["read_access"] = f"{read_access.name} (0x{read_access:02X})"
            else:
                checks["details"]["read_access"] = "Could not read file settings"
        except Exception as e:
            log.debug(f"Condition 1 check error: {e}", exc_info=True)
            checks["details"]["read_access"] = f"Error: {e}"

        # CONDITION 2: NDEF Format (supports both Type 4 new and old formats)
        # Type 4 new: [NLEN (2 bytes)] + [D1 01 XX 55 04 ...]
        # Type 4 old: [NLEN (2 bytes)] + [03] [Len] [D1 01 XX 55 04 ...] [FE]
        try:
            # Use shared helper functions for DRY parsing
            ndef_record, parse_info = parse_ndef_file_data(ndef_data)

            if parse_info["valid"] and len(ndef_record) >= 5:
                # Validate the NDEF URI record structure
                validation = validate_ndef_uri_record(ndef_record)

                checks["condition_2_ndef_format"] = validation["valid"]
                checks["details"]["ndef_format"] = {
                    "detected_format": parse_info["format"],
                    "nlen": f"0x{parse_info['nlen']:04X}" if parse_info["nlen"] else "N/A",
                    "has_tlv_wrapper": "Yes" if parse_info["has_tlv"] else "No",
                    "ndef_header": f"0x{validation['ndef_header']['value']:02X} {'✓' if validation['ndef_header']['valid'] else '✗'}" if validation['ndef_header']['value'] is not None else "N/A",
                    "type_length": f"0x{validation['type_length']['value']:02X} {'✓' if validation['type_length']['valid'] else '✗'}" if validation['type_length']['value'] is not None else "N/A",
                    "uri_type": f"0x{validation['uri_type']['value']:02X} {'✓' if validation['uri_type']['valid'] else '✗'}" if validation['uri_type']['value'] is not None else "N/A",
                    "uri_prefix": f"0x{validation['uri_prefix']['value']:02X} {'✓' if validation['uri_prefix']['valid'] else '✗'}" if validation['uri_prefix']['value'] is not None else "N/A",
                }
            else:
                error_msg = parse_info.get("error", "NDEF record too short or invalid")
                checks["details"]["ndef_format"] = f"Invalid: {error_msg}"
        except Exception as e:
            checks["details"]["ndef_format"] = f"Error: {e}"

        # CONDITION 3: CC File Valid (E1 04 marker)
        try:
            cc_info = self.read_cc_file()
            if "error" not in cc_info:
                # Parse CC file to check for NDEF File Control TLV and Tag File Control TLV
                self.card.send(ISOSelectFile(ISOFileID.CC_FILE))
                cc_full = self.card.send(ISOReadBinary(0, 23))  # Read full 23 bytes
                self.card.send(SelectPiccApplication())

                # CC File Structure (23 bytes):
                # Bytes 0-6:   CC Header (00 17 20 01 00 00 FF)
                # Bytes 7-14:  NDEF File Control TLV (Tag 0x04)
                # Bytes 15-22: Tag File Control TLV (Tag 0x05) - Optional but recommended

                # Check NDEF File Control TLV at bytes 7-14
                ndef_tlv_tag = cc_full[7]
                ndef_tlv_len = cc_full[8]
                ndef_file_id = (cc_full[9] << 8) | cc_full[10]
                ndef_read_access = cc_full[13]

                # Check Tag File Control TLV at bytes 15-22 (optional)
                has_tag_file_tlv = False
                tag_file_tlv_valid = False
                if len(cc_full) >= 23:
                    tag_tlv_tag = cc_full[15]
                    tag_tlv_len = cc_full[16]
                    if tag_tlv_tag == CCFileTLV.PROPRIETARY_FILE_CONTROL and tag_tlv_len == 0x06:
                        has_tag_file_tlv = True
                        tag_file_id = (cc_full[17] << 8) | cc_full[18]
                        # Tag File Control TLV is valid if File ID is E1 05 (File 3)
                        tag_file_tlv_valid = (tag_file_id == 0xE105)

                # Android requires:
                # 1. NDEF File Control TLV (Tag 0x04) present
                # 2. NDEF File ID = 0xE104 (File 2)
                # 3. NDEF Read Access = 0x00 (FREE)
                # Tag File Control TLV is optional but good practice
                cc_valid = (
                    ndef_tlv_tag == CCFileTLV.NDEF_FILE_CONTROL and  # NDEF File Control TLV
                    ndef_tlv_len == 0x06 and                          # Length = 6 bytes
                    ndef_file_id == 0xE104 and                        # File ID = 0xE104
                    ndef_read_access == 0x00                          # Read Access = FREE
                )

                checks["condition_3_cc_file_valid"] = cc_valid
                checks["details"]["cc_file"] = {
                    "ndef_tlv_tag": f"{CCFileTLV(ndef_tlv_tag).name if ndef_tlv_tag in CCFileTLV._value2member_map_ else 'UNKNOWN'} (0x{ndef_tlv_tag:02X}) {'✓' if ndef_tlv_tag == CCFileTLV.NDEF_FILE_CONTROL else '✗'}",
                    "ndef_tlv_len": f"0x{ndef_tlv_len:02X} {'✓' if ndef_tlv_len == 0x06 else '✗'}",
                    "ndef_file_id": f"File 2 (0x{ndef_file_id:04X}) {'✓' if ndef_file_id == 0xE104 else '✗'}",
                    "ndef_read_access": f"FREE (0x{ndef_read_access:02X}) {'✓' if ndef_read_access == 0x00 else '✗'}",
                    "has_tag_file_tlv": has_tag_file_tlv,
                    "tag_file_tlv_valid": f"{'✓' if tag_file_tlv_valid else '✗'}" if has_tag_file_tlv else "N/A",
                    "cc_length": len(cc_full),
                }
            else:
                checks["details"]["cc_file"] = f"Error reading CC file: {cc_info['error']}"
        except Exception as e:
            checks["details"]["cc_file"] = f"Error: {e}"

        # CONDITION 4: SDM Offsets Valid (no overlap, within bounds)
        try:
            if sdm_config and hasattr(sdm_config, 'offsets') and sdm_config.offsets:
                offsets = sdm_config.offsets
                file_size = len(ndef_data)

                # Check for overlaps and bounds
                uid_end = offsets.uid_offset + 14  # UID is 14 bytes
                ctr_end = offsets.read_ctr_offset + 6  # Counter is 6 bytes
                cmac_end = offsets.mac_offset + 16  # CMAC is 16 bytes

                no_uid_ctr_overlap = uid_end <= offsets.read_ctr_offset
                no_ctr_cmac_overlap = ctr_end <= offsets.mac_offset
                within_bounds = cmac_end <= file_size

                offsets_valid = no_uid_ctr_overlap and no_ctr_cmac_overlap and within_bounds

                checks["condition_4_offsets_valid"] = offsets_valid
                checks["details"]["sdm_offsets"] = {
                    "uid_offset": offsets.uid_offset,
                    "uid_end": uid_end,
                    "ctr_offset": offsets.read_ctr_offset,
                    "ctr_end": ctr_end,
                    "cmac_offset": offsets.mac_offset,
                    "cmac_end": cmac_end,
                    "file_size": file_size,
                    "no_uid_ctr_overlap": no_uid_ctr_overlap,
                    "no_ctr_cmac_overlap": no_ctr_cmac_overlap,
                    "within_bounds": within_bounds,
                }
            else:
                checks["details"]["sdm_offsets"] = "No SDM configuration"
                checks["condition_4_offsets_valid"] = True  # Not applicable if no SDM
        except Exception as e:
            checks["details"]["sdm_offsets"] = f"Error: {e}"

        # Overall result
        checks["all_conditions_pass"] = (
            checks["condition_1_read_access_free"] and
            checks["condition_2_ndef_format"] and
            checks["condition_3_cc_file_valid"] and
            checks["condition_4_offsets_valid"]
        )

        return checks

    def _get_authenticated_diagnostics(self) -> dict[str, Any]:
        """Run additional commands when keys are available.

        NOTE: Most NTAG424 query commands (GetFileIds, GetFileSettings, GetFileCounters)
        use the ApduCommand interface and DON'T support AuthenticatedConnection.send()
        because they don't implement get_command_byte(), get_p1(), etc.

        These commands work the same with or without authentication, so we run them
        unauthenticated using the regular connection.

        Returns:
            Dictionary with additional diagnostic results
        """
        auth_diag: dict[str, Any] = {}

        if not self._cached_keys:
            return {"error": "No keys available"}

        # GetFileIds - list all files in application
        # Uses ApduCommand interface (build_apdu/parse_response), NOT AuthApduCommand
        # NOTE: Not supported on all NTAG424 DNA tags
        try:
            from ntag424_sdm_provisioner.commands.get_file_ids import GetFileIds

            log.info("Getting file IDs...")
            file_ids_response = self.card.send(GetFileIds())
            auth_diag["file_ids"] = [f"0x{fid:02X}" for fid in file_ids_response]
        except Exception as e:
            error_str = str(e)
            if "ILLEGAL_COMMAND" in error_str or "0x911C" in error_str:
                log.info("GetFileIds not supported on this tag (ILLEGAL_COMMAND)")
                auth_diag["file_ids"] = "Not supported on this tag"
            else:
                log.error(f"Failed to get file IDs: {e}")
                auth_diag["file_ids"] = f"Error: {e}"

        # GetFileCounters - SDM read counter (only works if SDM is enabled)
        # Uses .execute() method, NOT connection.send() or auth_conn.send()
        # NOTE: Not supported on all tags, and only works when SDM is enabled
        try:
            from ntag424_sdm_provisioner.commands.get_file_counters import GetFileCounters

            log.info("Getting SDM file counters...")
            counter = GetFileCounters(file_no=FileNo.NDEF_FILE).execute(self.card)
            auth_diag["sdm_read_counter"] = counter
        except Exception as e:
            error_str = str(e)
            # GetFileCounters only works when SDM is enabled on the file
            if "ILLEGAL_COMMAND" in error_str or "0x911C" in error_str:
                log.info("GetFileCounters not supported (SDM not enabled or command not available)")
                auth_diag["sdm_read_counter"] = "N/A (not supported)"
            else:
                log.error(f"Failed to get file counters: {e}")
                auth_diag["sdm_read_counter"] = f"Error: {e}"

        auth_diag["status"] = "Complete"
        return auth_diag
