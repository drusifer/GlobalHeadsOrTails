"""CSV-based key manager for NTAG424 DNA tags.

Stores tag keys in a simple CSV file for persistence across sessions.
Implements the KeyManager protocol for compatibility with provisioning flow.
"""

import csv
import json
import logging
import secrets
import shutil
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import ClassVar
import coolname
from enum import Enum, StrEnum
import json

from ntag424_sdm_provisioner.crypto.crypto_primitives import calculate_cmac_full, truncate_cmac
from ntag424_sdm_provisioner.key_manager_interface import KEY_DEFAULT_FACTORY
from ntag424_sdm_provisioner.uid_utils import UID


log = logging.getLogger(__name__)

def generate_coin_name() -> str:
    """Generate a unique, memorable coin name.

    Uses coolname library if available, otherwise generates a simple name.
    Format: "ADJECTIVE-NOUN-NUMBER" (e.g., "SWIFT-FALCON-42")

    Returns:
        A unique coin name string
    """
    # Generate 2-word name with number suffix (e.g., "swift-falcon-42")
    name = coolname.generate_slug(2)
    # Add random number suffix for uniqueness
    suffix = secrets.randbelow(1000)
    return f"{name}-{suffix}".upper()

class Outcome(StrEnum):
    HEADS = "heads"
    TAILS = "tails"
    INVALID = "invalid"

@dataclass
class TagKeys:
    """Keys and metadata for a single NTAG424 DNA tag.

    Attributes:
        uid: Tag UID (UID object)
        picc_master_key: Key 0 (hex string, 32 chars)
        app_read_key: Key 1 (hex string, 32 chars)
        sdm_mac_key: Key 3 (hex string, 32 chars)
        outcome: Tag side (HEADS | TAILS | INVALID)
        coin_name: Name of the coin this tag belongs to (empty string if unassigned)
        provisioned_date: ISO format timestamp
        status: 'factory', 'provisioned', 'locked', 'error'
        notes: Optional notes
        last_used_date: ISO format timestamp of last use
    """

    uid: UID  # UID object
    picc_master_key: str  # Key 0 (hex string, 32 chars)
    app_read_key: str  # Key 1 (hex string, 32 chars)
    sdm_mac_key: str  # Key 3 (hex string, 32 chars)
    outcome: Outcome = Outcome.INVALID  # heads or tails (defaults to INVALID)
    coin_name: str = ""  # Coin identifier (defaults to unassigned)
    provisioned_date: str = ""  # ISO format timestamp
    status: str = "factory"  # 'factory', 'provisioned', 'locked', 'error'
    notes: str = ""
    last_used_date: str = ""  # ISO format timestamp of last use

    def __post_init__(self):
        """Convert string UID to UID object and normalize outcome if needed."""
        if isinstance(self.uid, str):
            self.uid = UID(self.uid)
        # Convert string outcome to Outcome enum if needed (for CSV compatibility)
        if isinstance(self.outcome, str):
            self.outcome = Outcome(self.outcome)

    def get_picc_master_key_bytes(self) -> bytes:
        """Get PICC master key as bytes."""
        return bytes.fromhex(self.picc_master_key)

    def get_app_read_key_bytes(self) -> bytes:
        """Get app read key as bytes."""
        return bytes.fromhex(self.app_read_key)

    def get_sdm_mac_key_bytes(self) -> bytes:
        """Get SDM MAC key as bytes."""
        return bytes.fromhex(self.sdm_mac_key)

    def get_asset_tag(self) -> str:
        """Get short asset tag code from UID."""
        return self.uid.asset_tag

    def __str__(self) -> str:
        """Format TagKeys for display."""
        asset_tag = self.get_asset_tag()
        coin_display = f"Coin: {self.coin_name}" if self.coin_name else "Unassigned"
        return (
            f"TagKeys(\n"
            f"  UID: {self.uid} [Tag: {asset_tag}]\n"
            f"  {coin_display} ({self.outcome.value})\n"
            f"  PICC Master Key: {self.picc_master_key}\n"
            f"  App Read Key: {self.app_read_key}\n"
            f"  SDM MAC Key: {self.sdm_mac_key}\n"
            f"  Provisioned: {self.provisioned_date}\n"
            f"  Status: {self.status}\n"
            f"  Notes: {self.notes[:50]}{'...' if len(self.notes) > 50 else ''}\n"
            f"  Last Used: {self.last_used_date}\n"
            f")"
        )

    @staticmethod
    def from_factory_keys(uid: UID) -> "TagKeys":
        """Create TagKeys entry with factory default keys."""
        factory_key = "00000000000000000000000000000000"
        return TagKeys(
            uid=uid,
            picc_master_key=factory_key,
            app_read_key=factory_key,
            sdm_mac_key=factory_key,
            outcome=Outcome.INVALID,
            coin_name="",  # Factory keys are unassigned
            provisioned_date=datetime.now().isoformat(),
            status="factory",
            notes="Factory default keys",
            last_used_date="",
        )

def build_system_vector(uid: UID, ctr: int) -> bytes:
    """Constructs the 16-byte System Vector for NTAG 424 DNA SDM.

    Per NXP AN12196 Section 9.3.9.1 line 898:
    SV2 = 3Ch || C3h || 00h || 01h || 00h || 80h || UID || SDMReadCtr

    Args:
        uid_str: The 14-char hex string UID from URL (e.g., "04AE664A2F7080")
        ctr: Counter value as integer (e.g., 130)

    Returns:
        bytes: The 16-byte System Vector ready for CMAC calculation.
    """
    # SV2 header per NXP spec: 3C C3 00 01 00 80
    sv_header_hex = "3CC300010080"
    ctr_str = f"{ctr:06X}"
    # Counter is little-endian in the SV (LSB first)
    ctr_bytes_le = bytes.fromhex(ctr_str)[::-1]

    full_vec: bytes = (bytes.fromhex(sv_header_hex) + uid.bytes + ctr_bytes_le)

    log.info("[SV2 BUILD] System Vector construction:")
    log.info(f"  Input UID (hex):     {uid.uid}")
    log.info(f"  Input Counter (dec): {ctr}")
    log.info(f"  Counter (hex BE):    {ctr_str}")
    log.info(f"  Counter (hex LE):    {ctr_bytes_le.hex().upper()}")
    log.info(f"  SV2 Header:          {sv_header_hex}")
    log.info("  SV2 = Header || UID || Counter(LE)")
    log.info(f"  SV2 = {sv_header_hex} || {uid.uid} || {ctr_bytes_le.hex().upper()}")
    log.info(f"  SV2 Final (16 bytes): {full_vec.hex().upper()}")

    # Sanity Check: SV must be exactly 16 bytes for standard SDM
    if len(full_vec) != 16:
        raise ValueError(f"Invalid SV length: {len(full_vec)}. Expected 16. Hex: {full_vec.hex().upper()}, "
                         f"uid: {uid.uid}, ctr: {ctr_str}")

    return full_vec

class CsvKeyManager:
    """CSV-based key manager implementing the KeyManager protocol.

    Keys are stored in a primary CSV file (tag_keys.csv) and backed up
    to a backup file (tag_keys_backup.csv) before any changes.

    This provides:
    - Persistent storage of unique keys per tag
    - Automatic backup before key changes
    - Factory key fallback for new tags
    - Compatible with KeyManager protocol
    """

    FIELDNAMES: ClassVar[list[str]] = [f.name for f in fields(TagKeys)]

    def __init__(
        self,
        csv_path: str = "test_tag_keys.csv",
        backup_path: str = "test_tag_keys_backup.csv",
        timestamped_backup_dir: str = "test_tag_keys_backups",
    ):
        """Initialize key manager.

        Args:
            csv_path: Path to main keys CSV file
            backup_path: Path to backup CSV file
            timestamped_backup_dir: Directory for timestamped backup files
        """
        self.csv_path = Path(csv_path)
        self.backup_path = Path(backup_path)
        self.timestamped_backup_dir = Path(timestamped_backup_dir)
        log.info(f"[CSV MANAGER] Initialized with csv_path: {self.csv_path.absolute()}")
        log.info(f"[CSV MANAGER] Backup path: {self.backup_path.absolute()}")
        log.info(f"[CSV MANAGER] Timestamped backup dir: {self.timestamped_backup_dir.absolute()}")
        self._ensure_csv_exists()
        self._ensure_backup_dir_exists()

    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist."""
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            print(f"[INFO] Created new key database: {self.csv_path}")

        if not self.backup_path.exists():
            with self.backup_path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            print(f"[INFO] Created backup database: {self.backup_path}")

    def _ensure_backup_dir_exists(self):
        """Create timestamped backup directory if it doesn't exist."""
        if not self.timestamped_backup_dir.exists():
            self.timestamped_backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created timestamped backup directory: {self.timestamped_backup_dir}")

    def get_key(self, uid: UID, key_no: int) -> bytes:
        """Get key for a specific tag and key number (implements KeyManager protocol).

        Args:
            uid: Tag UID as bytes
            key_no: Key number (0 = PICC Master, 1 = App Read, 2 = SDM MAC)

        Returns:
            16-byte AES-128 key

        Raises:
            ValueError: If key_no is invalid
        """
        if key_no < 0 or key_no > 4:
            raise ValueError(f"Key number must be 0-4, got {key_no}")

        tag_keys = self.get_tag_keys(uid)

        # Map key_no to the appropriate key
        if key_no == 0:
            return tag_keys.get_picc_master_key_bytes()
        elif key_no == 1:
            return tag_keys.get_app_read_key_bytes()
        elif key_no == 2:
            return tag_keys.get_sdm_mac_key_bytes()
        else:
            # For other key numbers, return factory key (we don't use them yet)
            return KEY_DEFAULT_FACTORY

    def get_outcome(self, uid: UID) -> Outcome:
        """Get the outcome for a specific tag UID.

        Args:
            uid: Tag UID as bytes       
        Returns:
            Outcome enum value
        """
        tag_keys = self.get_tag_keys(uid)
        log.debug(f"[GET OUTCOME] UID: {uid}, Outcome: {tag_keys.outcome}, Keys: {tag_keys}")
        return tag_keys.outcome
    
    def get_tag_keys(self, uid: UID) -> TagKeys:
        """Get all keys for a specific tag UID.

        Searches:
        1. Main CSV (tag_keys.csv)
        2. Backup CSV (tag_keys_backup.csv) - for historical keys

        Any status (provisioned, failed, pending) counts as having keys.
        Only returns factory keys if UID is truly not found anywhere.

        Args:
            uid: Tag UID as bytes

        Returns:
            TagKeys object with tag's keys
        """
        # 1. Search main CSV first
        if self.csv_path.exists():
            log.debug(f"[CSV READ] Reading from: {self.csv_path.absolute()}")
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f, fieldnames=self.FIELDNAMES)
                for row in reader:
                    if row["uid"].upper() == uid.uid:
                        print(
                            f"[OK] Found keys for {uid.uid} in main database ({json.dumps(row)})"
                        )
                        row["outcome"] = Outcome(row.get("outcome", "invalid"))
                        return TagKeys(**row)

        print(f"[WARNING] UID {uid} not found in database") 
        print("[INFO] Using factory default keys")
        return TagKeys.from_factory_keys(uid)
        
    def search_for_tag_keys(self, uid: UID) -> TagKeys:
        """Search for tag keys in main and backup CSV files."""
        # 2. Search backup CSV for historical keys
        if self.backup_path.exists():
            best_match = None
            best_date = None

            with self.backup_path.open(newline="") as f:
                reader = csv.DictReader(f, fieldnames=self.FIELDNAMES)
                for row in reader:
                    if row["uid"].upper() == uid.uid:
                        # Get the most recent entry for this UID
                        date_str = row.get("backup_timestamp") or row.get("provisioned_date", "")
                        if best_match is None or date_str > (best_date or ""):
                            best_match = row
                            best_date = date_str

            if best_match:
                status = best_match.get("status", "unknown")
                print(f"[OK] Found keys for {uid} in BACKUP (status={status})")
                # Remove backup_timestamp field if present (not in TagKeys)
                clean_row = {k: v for k, v in best_match.items() if k != "backup_timestamp"}
                return TagKeys(**clean_row)

        # 3. UID not found anywhere - return factory keys
        print(f"[WARNING] UID {uid} not found in database OR backup")
        print("[INFO] Using factory default keys")
        return TagKeys.from_factory_keys(uid.uid)

    def validate_sdm_url(self, uid: UID, counter: int, cmac: str) -> dict:
        """Validate an SDM cmac the CMAC values from the parsed configuration.

        This simulates what a server does when it verifies a request from a tag.

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "uid": UID,
                "counter": int,
                "cmac_received": str,
                "cmac_calculated": str (if validation attempted),
                "error": str (if validation failed)
            }
        """
        log.info("=" * 70)
        log.info("[SDM VALIDATION] Starting CMAC validation for Android tap")
        log.info("=" * 70)

        result = {
            "valid": False,
            "uid": uid,
            "counter": counter,
            "cmac_received": cmac,
            "cmac_calculated": None,
            "error": None,
        }

        log.info("[STEP 1] Input parameters from tag URL:")
        log.info(f"  UID (from URL):     {uid}")
        log.info(f"  Counter (decimal):  {counter}")
        log.info(f"  Counter (hex):      {counter:06X}")
        log.info(f"  CMAC (from URL):    {cmac}")

        log.info("[STEP 2] Building System Vector (SV2)...")
        sv_bytes = build_system_vector(uid, counter)
        result["sv2"] = sv_bytes.hex().upper()

        log.info("[STEP 3] Loading keys from database...")
        keys: TagKeys = self.get_tag_keys(uid)
        log.info(f"  Database path:      {self.csv_path}")
        log.info(f"  Key status:         {keys.status}")
        log.info(f"  PICC Master Key:    {keys.picc_master_key}")
        log.info(f"  App Read Key:       {keys.app_read_key}")
        log.info(f"  SDM MAC Key (K3):   {keys.sdm_mac_key}")

        sdm_mac_key_bytes = keys.get_sdm_mac_key_bytes()
        log.info("[STEP 4] Deriving Session MAC Key...")
        log.info(f"  SDM MAC Key (bytes): {sdm_mac_key_bytes.hex().upper()}")
        log.info(f"  SV2 (bytes):         {sv_bytes.hex().upper()}")
        log.info("  Session Key = CMAC(SV2, SDM_MAC_Key)")

        # Derive session MAC key using SDM MAC key (Key 3), not App Read key (Key 1)
        session_key = calculate_cmac_full(sv_bytes, sdm_mac_key_bytes)
        log.info(f"  Session Key:         {session_key.hex().upper()}")
        result["session_key"] = session_key.hex().upper()

        # Build CMAC message: UID&ctr=COUNTER&cmac=
        # Counter must be formatted as 6-character hex string (uppercase)
        counter_hex = f"{counter:06X}"
        cmac_message = f"{uid.uid}&ctr={counter_hex}&cmac=".encode('ascii')
        log.info("[STEP 5] Building CMAC input message...")
        log.info("  Message format:      UID&ctr=COUNTER&cmac=")
        log.info(f"  Message (ASCII):     {cmac_message.decode('ascii')}")
        log.info(f"  Message (hex):       {cmac_message.hex().upper()}")
        log.info(f"  Message length:      {len(cmac_message)} bytes")
        result["cmac_message"] = cmac_message.decode('ascii')
        result["cmac_message_hex"] = cmac_message.hex().upper()

        # Calculate CMAC over the message
        log.info("[STEP 6] Calculating full CMAC...")
        log.info("  Full CMAC = CMAC(message, session_key)")
        full_cmac = calculate_cmac_full(cmac_message, session_key)
        log.info(f"  Full CMAC (16 bytes): {full_cmac.hex().upper()}")
        result["full_cmac"] = full_cmac.hex().upper()

        # SDM uses special truncation: take every other byte starting at index 1
        # Indices: 1, 3, 5, 7, 9, 11, 13, 15 (per AN12196)
        log.info("[STEP 7] Truncating CMAC (AN12196 spec)...")
        log.info("  NXP 'even-numbered bytes' (1-indexed) = indices 1,3,5,7,9,11,13,15")
        log.info(f"  Full CMAC bytes:  {' '.join(f'{b:02X}' for b in full_cmac)}")
        log.info(f"  Byte positions:   {' '.join(f'{i:2d}' for i in range(16))}")
        log.info(f"  Selected (odd idx): {full_cmac[1]:02X} {full_cmac[3]:02X} {full_cmac[5]:02X} {full_cmac[7]:02X} {full_cmac[9]:02X} {full_cmac[11]:02X} {full_cmac[13]:02X} {full_cmac[15]:02X}")

        calc_mac = truncate_cmac(full_cmac)
        log.info(f"  Truncated CMAC:     {calc_mac.hex().upper()}")
        result["cmac_calculated"] = calc_mac.hex().upper()

        log.info("[STEP 8] Comparing CMACs...")
        log.info(f"  CMAC from URL:      {cmac.upper()}")
        log.info(f"  CMAC calculated:    {calc_mac.hex().upper()}")

        result["valid"] = (calc_mac.hex().upper() == cmac.upper())

        if result["valid"]:
            log.info("  ✓ MATCH - Validation PASSED")
        else:
            log.info("  ✗ MISMATCH - Validation FAILED")
            # Show byte-by-byte comparison for debugging
            received_bytes = bytes.fromhex(cmac) if len(cmac) == 16 else b''
            if len(received_bytes) == 8:
                log.info("  Byte comparison:")
                for i in range(8):
                    match = "✓" if received_bytes[i] == calc_mac[i] else "✗"
                    log.info(f"    [{i}] received={received_bytes[i]:02X} calc={calc_mac[i]:02X} {match}")

        log.info("=" * 70)
        log.info(f"[SDM VALIDATION] Result: {'VALID' if result['valid'] else 'INVALID'}")
        log.info("=" * 70)

        return result

    def _find_all_sdm_keys_in_backups(self) -> list[str]:
        """Find all unique SDM MAC keys from backup CSV files.

        Returns:
            List of unique SDM MAC keys as hex strings
        """
        unique_keys = set()

        # Search in multiple backup locations
        search_paths = [
            Path(self.csv_path).parent / "tag_keys_backups",
            Path(self.csv_path).parent / ".history",
            Path(self.csv_path).parent.parent / "tag_keys_backups",
            Path(self.csv_path).parent.parent / ".history",
        ]

        # Also include the main CSV file's directory
        if Path(self.csv_path).parent.exists():
            search_paths.insert(0, Path(self.csv_path).parent)

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for csv_file in search_path.glob("*.csv"):
                try:
                    with csv_file.open(encoding='utf-8') as f:
                        reader = csv.DictReader(f, fieldnames=self.FIELDNAMES)
                        for row in reader:
                            # Handle both column name variants
                            sdm_key = row.get("sdm_mac_key") or row.get("sdm_file_read_key", "")
                            if sdm_key and sdm_key != "00000000000000000000000000000000":
                                unique_keys.add(sdm_key.lower())
                except Exception:
                    pass

        return sorted(list(unique_keys))

    def save_tag_keys(self, keys: TagKeys):
        """Save or update all keys for a tag.

        Args:
            keys: TagKeys object to save
        """
        # Backup existing keys before updating
        self._create_timestamped_backup()

        # Read all rows
        rows = []
        found = False

        # Get UID string for comparison and storage
        uid_str = keys.uid.uid if hasattr(keys.uid, 'uid') else str(keys.uid)

        if self.csv_path.exists():
            log.debug(f"[CSV READ] Reading from: {self.csv_path.absolute()}")
            with self.csv_path.open(newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["uid"].upper() == uid_str.upper():
                        # Update existing row - convert TagKeys to dict with string UID
                        log.debug(f"[CSV UPDATE] Updating existing row for UID {uid_str}: {keys=}")
                        row_dict = asdict(keys)
                        row_dict["uid"] = uid_str  # Ensure UID is string, not UID object
                        row_dict["outcome"] = keys.outcome.value  # Convert Outcome enum to string
                        rows.append(row_dict)
                        found = True
                    else:
                        rows.append(row)

        # Append new row if not found
        if not found:
            log.debug(f"[CSV INSERT] Adding new row for UID {uid_str}")
            new_row = asdict(keys)
            new_row["uid"] = uid_str  # Ensure UID is string, not UID object
            new_row["outcome"] = keys.outcome.value  # Convert Outcome enum to string
            rows.append(new_row)

        # Write back
        log.debug(f"[CSV WRITE] Writing to: {self.csv_path.absolute()}")
        with self.csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        log.info(f"[OK] Saved keys for UID {keys.uid} (status: {keys.status})")


    def _create_timestamped_backup(self):
        """Create a timestamped backup copy of the entire database.

        Creates a full copy of tag_keys.csv with a timestamp in the filename.
        Format: tag_keys_YYYYMMDD_HHMMSS.csv

        This is called every time the database state changes to provide
        point-in-time snapshots of the entire database.
        """
        if not self.csv_path.exists():
            return

        # Generate timestamp filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"tag_keys_{timestamp}.csv"
        backup_filepath = self.timestamped_backup_dir / backup_filename

        # Copy the current database file to the timestamped backup
        shutil.copy2(self.csv_path, backup_filepath)

        log.info(f"Created timestamped backup: {backup_filepath}")

    def _load_backups_for_uid(self, uid: UID) -> list[TagKeys]:
        """Load all backup entries for the given UID (newest first)."""
        entries: list[TagKeys] = []

        if not self.backup_path.exists():
            return entries

        with self.backup_path.open(newline="") as f:
            fieldnames = [field.name for field in fields(TagKeys)]
            reader = csv.DictReader(f, fieldnames=fieldnames )
            for row in reader:
                if row.get("uid", "").upper() != uid.uid:
                    continue

                data = {field: row.get(field, "") for field in self.FIELDNAMES}
                entry_keys = TagKeys(**data)
                entries.append(entry_keys)

        entries.sort(key=lambda entry: entry.timestamp, reverse=True)
        return entries

    def get_backup_entries(self, uid: UID) -> list[TagKeys]:
        """Return backup entries for the UID, sorted newest first."""
        return self._load_backups_for_uid(uid)

    def restore_from_backup(self, uid: UID) -> TagKeys | None:
        """Restore the most recent backup entry for the UID back into the main CSV.

        Args:
            uid: Tag UID

        Returns:
            TagKeys of restored entry if a backup exists, otherwise None.
        """
        backups = self.get_backup_entries(uid)
        if not backups:
            return None

        # Save restored keys back to primary CSV (this will backup current entry first)
        selected = backups[0]
        self.save_tag_keys(selected.keys)

        return selected.keys

    def list_tags(self) -> list[TagKeys]:
        """List all tags in the database.

        Returns:
            List of TagKeys objects
        """
        with self.csv_path.open(newline="") as f:
            reader = csv.DictReader(f)
            tags = [TagKeys(**row) for row in reader]

        return tags

    # ========================================================================
    # Coin Management API
    # ========================================================================

    def assign_coin_name(self, uid: UID, coin_name: str, outcome: Outcome):
        """Assign a coin name and outcome to a tag.

        Validates:
        - coin_name is not empty
        - outcome is HEADS or TAILS (not INVALID)
        - No duplicate outcome for the same coin_name

        Args:
            uid: Tag UID
            coin_name: Coin identifier (e.g., "SWIFT-FALCON-42")
            outcome: Must be Outcome.HEADS or Outcome.TAILS

        Raises:
            ValueError: If validation fails or duplicate outcome detected
        """
        # Validate inputs
        if not coin_name:
            raise ValueError("coin_name cannot be empty")

        if outcome not in (Outcome.HEADS, Outcome.TAILS):
            raise ValueError(f"outcome must be HEADS or TAILS, got {outcome}")

        # Check for duplicate outcome in the same coin
        existing_tags = self.list_tags()
        for tag in existing_tags:
            if tag.coin_name == coin_name and tag.outcome == outcome and tag.uid.uid != uid.uid:
                raise ValueError(
                    f"Coin '{coin_name}' already has a {outcome.value} tag "
                    f"(UID: {tag.uid.uid}). Cannot assign duplicate outcome."
                )

        # Get existing tag or create new entry
        tag_keys = self.get_tag_keys(uid)
        tag_keys.coin_name = coin_name
        tag_keys.outcome = outcome
        self.save_tag_keys(tag_keys)

        log.info(f"Assigned coin name '{coin_name}' ({outcome.value}) to UID {uid.uid}")

    def get_coin_tags(self, coin_name: str) -> dict[str, TagKeys | None]:
        """Get both tags for a coin.

        Args:
            coin_name: Coin identifier

        Returns:
            dict with keys 'heads' and 'tails', values are TagKeys or None if missing

        Example:
            {'heads': TagKeys(...), 'tails': TagKeys(...)}
            {'heads': TagKeys(...), 'tails': None}  # Incomplete coin
        """
        result: dict[str, TagKeys | None] = {'heads': None, 'tails': None}

        tags = self.list_tags()
        for tag in tags:
            if tag.coin_name == coin_name:
                if tag.outcome == Outcome.HEADS:
                    result['heads'] = tag
                elif tag.outcome == Outcome.TAILS:
                    result['tails'] = tag

        return result

    def validate_coin(self, coin_name: str) -> dict:
        """Validate coin completeness.

        Args:
            coin_name: Coin identifier

        Returns:
            {
                'complete': bool,  # True if both heads and tails exist
                'heads': TagKeys | None,
                'tails': TagKeys | None,
                'issues': list[str]  # ["Missing tails tag", "Heads tag not provisioned"]
            }
        """
        coin_tags = self.get_coin_tags(coin_name)
        heads = coin_tags['heads']
        tails = coin_tags['tails']

        issues = []
        if heads is None:
            issues.append("Missing heads tag")
        elif heads.status not in ('provisioned', 'keys_configured'):
            issues.append(f"Heads tag not provisioned (status: {heads.status})")

        if tails is None:
            issues.append("Missing tails tag")
        elif tails.status not in ('provisioned', 'keys_configured'):
            issues.append(f"Tails tag not provisioned (status: {tails.status})")

        return {
            'complete': len(issues) == 0,
            'heads': heads,
            'tails': tails,
            'issues': issues
        }

    def list_coins(self) -> dict[str, dict]:
        """List all coins and their status.

        Returns:
            {
                'SWIFT-FALCON-42': {
                    'complete': True,
                    'heads_uid': '04AE664A2F7080',
                    'tails_uid': '04AE664A2F7081'
                },
                'BOLD-EAGLE-99': {
                    'complete': False,
                    'heads_uid': '04AE664A2F7082',
                    'tails_uid': None
                },
                '': {  # Unassigned tags
                    'complete': False,
                    'heads_uid': None,
                    'tails_uid': None,
                    'unassigned_count': 3
                }
            }
        """
        coins: dict[str, dict] = {}
        tags = self.list_tags()

        # Group tags by coin_name
        for tag in tags:
            coin_name = tag.coin_name or ""  # Empty string for unassigned

            if coin_name not in coins:
                coins[coin_name] = {
                    'complete': False,
                    'heads_uid': None,
                    'tails_uid': None
                }

            if tag.outcome == Outcome.HEADS:
                coins[coin_name]['heads_uid'] = tag.uid.uid
            elif tag.outcome == Outcome.TAILS:
                coins[coin_name]['tails_uid'] = tag.uid.uid

        # Calculate completeness
        for coin_name, coin_data in coins.items():
            if coin_name == "":
                # Special handling for unassigned tags
                unassigned_tags = [t for t in tags if not t.coin_name]
                coin_data['unassigned_count'] = len(unassigned_tags)
            else:
                coin_data['complete'] = (
                    coin_data['heads_uid'] is not None and
                    coin_data['tails_uid'] is not None
                )

        return coins

    def generate_random_keys(self, uid: UID, coin_name: str = "", outcome: Outcome = Outcome.INVALID) -> TagKeys:
        """Generate random keys for a tag.

        Args:
            uid: Tag UID
            coin_name: Optional coin identifier (defaults to unassigned)
            outcome: Optional outcome (defaults to INVALID)

        Returns:
            TagKeys with randomly generated keys
        """
        return TagKeys(
            uid=uid,
            picc_master_key=secrets.token_hex(16),  # 16 bytes = 32 hex chars
            app_read_key=secrets.token_hex(16),
            sdm_mac_key=secrets.token_hex(16),
            outcome=outcome,
            coin_name=coin_name,
            provisioned_date=datetime.now().isoformat(),
            status="provisioned",
            notes="Randomly generated keys",
        )

    @contextmanager
    def provision_tag(
        self, uid: UID, url: str | None = None, coin_name: str = "", outcome: Outcome = Outcome.INVALID
    ):
        """Context manager for two-phase commit of tag provisioning.

        TWO-PHASE PROVISIONING:
        - Phase 1 (Keys): provision_tag(uid, url=None) → status='keys_configured'
          - Only changes keys on tag, no SDM/NDEF configuration
          - Allows URL failures without burning through keys
        - Phase 2 (URL): provision_tag(uid, url="...") → status='provisioned'
          - Configures SDM and writes NDEF with URL
          - Tag must already have status='keys_configured'

        Args:
            uid: Tag UID
            url: Base URL for NDEF. If None, only keys are set (keys_configured).
                 If provided, SDM/NDEF configured (provisioned).
            coin_name: Optional coin identifier (e.g., "SWIFT-FALCON-42")
            outcome: Optional outcome (HEADS | TAILS | INVALID for unassigned)

        Yields:
            TagKeys with newly generated keys (status='pending')

        Example (Two-Phase):
            # Phase 1: Set keys only with coin assignment
            with key_mgr.provision_tag(uid, url=None, coin_name="COIN-001", outcome=Outcome.HEADS) as keys:
                change_key(0, keys.get_picc_master_key_bytes())
                change_key(1, keys.get_app_read_key_bytes())
                change_key(3, keys.get_sdm_mac_key_bytes())
            # SUCCESS: Status → 'keys_configured', coin assigned

            # Phase 2: Configure URL
            keys = key_mgr.get_tag_keys(uid)
            with key_mgr.update_url(uid, "https://app.com") as keys:
                configure_sdm(...)
                write_ndef(...)
            # SUCCESS: Status → 'provisioned'
        """
        # Save OLD keys before generating NEW keys
        try:
            old_keys = self.get_tag_keys(uid)
        except KeyError:
            old_keys = None

        # Phase 1: Generate NEW keys with coin info and save with 'pending' status
        # (This automatically backs up OLD keys via save_tag_keys)
        new_keys = self.generate_random_keys(uid, coin_name, outcome)
        new_keys.status = "pending"
        new_keys.notes = "Provisioning in progress..."
        self.save_tag_keys(new_keys)

        success = False
        try:
            # Yield NEW keys to caller for provisioning
            yield new_keys
            success = True
        except Exception as e:
            # Phase 2a: Provisioning failed - RESTORE OLD keys
            # The tag still has OLD keys, so DB must reflect that
            if old_keys:
                old_keys.status = "failed"
                old_keys.notes = f"Provisioning failed: {e!s}"
                self.save_tag_keys(old_keys)
            else:
                # No old keys - was factory, still is factory
                factory_keys = TagKeys.from_factory_keys(uid)
                factory_keys.status = "failed"
                factory_keys.notes = f"Provisioning failed: {e!s}"
                self.save_tag_keys(factory_keys)
            raise  # Re-raise exception
        finally:
            if success:
                # Phase 2b: Provisioning succeeded - NEW keys now on tag
                if url is None:
                    # Phase 1: Keys configured, no URL yet
                    new_keys.status = "keys_configured"
                    new_keys.notes = "Keys configured, ready for URL provisioning"
                else:
                    # Phase 2: Full provisioning with URL
                    new_keys.status = "provisioned"
                    new_keys.notes = url
                self.save_tag_keys(new_keys)

    def print_summary(self):
        """Print summary of all tags in database."""
        tags = self.list_tags()
        tag_data = "\n-------\n".join(["  " + str(tag) + "\n" for tag in tags])
        (
        f'{"=" * 80}\n' 
        f'Tag Key Database Summary\n'
        f'{"=" * 80}\n' 
        f"Total tags: {len(tags)}\n"
        f'{tag_data}\n'
        f'{"=" * 80}\n' 
        )
        log.info(tag_data)
        print(tag_data)
