"""Key Recovery Service - Find lost keys from backup files."""

import csv
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ntag424_sdm_provisioner.constants import FACTORY_KEY
from ntag424_sdm_provisioner.hal import NTag424CardConnection


# NOTE: AuthenticateEV2 is imported lazily in methods to avoid circular dependency:
# key_recovery_service → auth_session → commands/base → hal → commands/base (circular!)

log = logging.getLogger(__name__)

# Conservative delay between authentication attempts to avoid lockout
AUTH_RETRY_DELAY_SECONDS = 5


@dataclass
class KeyRecoveryCandidate:
    """A potential key match found in backup files."""

    uid: str
    source_file: str
    picc_master_key: bytes
    app_read_key: bytes
    sdm_file_read_key: bytes
    status: str
    provisioned_date: str
    notes: str
    file_date: str  # Date from filename or mtime
    tested: bool = False
    works: bool = False


class KeyRecoveryService:
    """Recover lost keys by scanning backup files and testing against tags."""

    def __init__(self, root_path: Path | None = None):
        """Initialize recovery service.

        Args:
            root_path: Root directory to search for CSV files (defaults to cwd)
        """
        self.root_path = root_path or Path.cwd()

    def find_all_csv_files(self) -> list[Path]:
        """Recursively find ALL CSV files in project tree using os.walk.

        Searches entire tree from root_path, including hidden directories
        like .history, .backups, etc.

        Returns:
            List of all CSV file paths found, sorted by mtime (newest first)
        """
        csv_files: list[Path] = []

        # Walk entire tree including hidden dirs
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Don't skip hidden dirs - we want .history, .backups, etc.
            for filename in filenames:
                if filename.endswith('.csv'):
                    csv_files.append(Path(dirpath) / filename)

        # Sort by modification time (newest first)
        csv_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        log.info(f"Found {len(csv_files)} CSV files in tree")
        return csv_files

    def find_all_log_files(self) -> list[Path]:
        """Recursively find ALL tui_*.log files in project tree.

        Returns:
            List of all log file paths found, sorted by mtime (newest first)
        """
        log_files: list[Path] = []

        # Walk entire tree including hidden dirs
        for dirpath, dirnames, filenames in os.walk(self.root_path):
            for filename in filenames:
                if filename.startswith('tui_') and filename.endswith('.log'):
                    log_files.append(Path(dirpath) / filename)

        # Sort by modification time (newest first)
        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        log.info(f"Found {len(log_files)} TUI log files in tree")
        return log_files

    def _extract_date_from_file(self, file_path: Path) -> str:
        """Extract date from filename or use mtime.

        Looks for patterns like: tag_keys_backup_20251218_223014.csv
        Falls back to file modification time.

        Args:
            file_path: Path to CSV file

        Returns:
            Date string in YYYY-MM-DD format
        """
        # Try to extract from filename: YYYYMMDD or YYYYMMDD_HHMMSS
        match = re.search(r'(\d{8})(?:_\d{6})?', file_path.name)
        if match:
            date_str = match.group(1)
            try:
                dt = datetime.strptime(date_str, "%Y%m%d")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Fall back to mtime
        mtime = file_path.stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        return dt.strftime("%Y-%m-%d")

    def _extract_all_keys_from_context(self, context: str) -> dict[str, str | None]:
        """Extract all 3 key types from a log context.

        Looks for various log patterns that contain key information:
        - Direct key logging: "PICC Master Key: <hex>"
        - Auth key: "Auth key: <hex>" (PICC only)
        - CSV update logs: "picc_master_key='<hex>'"
        - TagKeys repr: "PICC Master Key: <hex>"

        Args:
            context: Text context to search

        Returns:
            Dict with keys 'picc', 'app_read', 'sdm_mac' (None if not found)
        """
        result: dict[str, str | None] = {'picc': None, 'app_read': None, 'sdm_mac': None}

        # Pattern 1: Direct key logging from provisioning_service.py
        # "PICC Master Key: 6eaaf5f76a12cab506926ccf0b48275d"
        picc_direct = re.search(r'PICC Master Key:\s*([0-9a-fA-F]{32})', context)
        if picc_direct:
            result['picc'] = picc_direct.group(1).upper()

        # "App Read Key: 75049c19dd53acb97acb011bc9552e50"
        app_direct = re.search(r'App Read Key:\s*([0-9a-fA-F]{32})', context)
        if app_direct:
            result['app_read'] = app_direct.group(1).upper()

        # "SDM MAC Key: 034e5593a0379b042f6ea9020fa82893" or "SDM MAC Key (Key 3): ..."
        sdm_direct = re.search(r'SDM MAC Key(?:\s*\(Key 3\))?:\s*([0-9a-fA-F]{32})', context)
        if sdm_direct:
            result['sdm_mac'] = sdm_direct.group(1).upper()

        # Pattern 2: CSV update logs with Python repr format
        # "picc_master_key='6eaaf5f76a12cab506926ccf0b48275d'"
        if not result['picc']:
            picc_csv = re.search(r"picc_master_key='([0-9a-fA-F]{32})'", context)
            if picc_csv:
                result['picc'] = picc_csv.group(1).upper()

        if not result['app_read']:
            app_csv = re.search(r"app_read_key='([0-9a-fA-F]{32})'", context)
            if app_csv:
                result['app_read'] = app_csv.group(1).upper()

        if not result['sdm_mac']:
            sdm_csv = re.search(r"sdm_mac_key='([0-9a-fA-F]{32})'", context)
            if sdm_csv:
                result['sdm_mac'] = sdm_csv.group(1).upper()

        # Pattern 3: Auth key pattern (PICC only, fallback)
        # "Auth key: 6EAAF5F76A12CAB506926CCF0B48275D"
        if not result['picc']:
            auth_key = re.search(r'Auth key:\s*([0-9a-fA-F]{32})', context)
            if auth_key:
                result['picc'] = auth_key.group(1).upper()

        return result

    def _scan_log_for_keys(self, log_file: Path, uid_normalized: str) -> list[KeyRecoveryCandidate]:
        """Extract keys from a TUI log file for a specific UID.

        Parses log files for all key patterns:
        - PICC Master Key: <hex>
        - App Read Key: <hex>
        - SDM MAC Key: <hex>
        - Auth key: <hex> (PICC only, fallback)
        - CSV update logs with picc_master_key='<hex>' format

        Args:
            log_file: Path to log file
            uid_normalized: Normalized UID (uppercase, no spaces)

        Returns:
            List of key candidates found in this log file
        """
        candidates = []

        try:
            with log_file.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Find all UID mentions
            uid_pattern = r'Tag UID:\s*([0-9A-Fa-f]{14})'
            uid_matches = list(re.finditer(uid_pattern, content))

            # Also find UIDs in CSV update format: "UID 04B6694A2F7080" or "uid='04B6694A2F7080'"
            uid_csv_pattern = r"(?:UID|uid[=:])[\s']*([0-9A-Fa-f]{14})"
            uid_csv_matches = list(re.finditer(uid_csv_pattern, content))

            all_uid_positions = []
            for m in uid_matches:
                if m.group(1).upper() == uid_normalized:
                    all_uid_positions.append(m.start())
            for m in uid_csv_matches:
                if m.group(1).upper() == uid_normalized:
                    all_uid_positions.append(m.start())

            if not all_uid_positions:
                return candidates

            # Deduplicate positions that are close together (within 1000 chars)
            all_uid_positions = sorted(set(all_uid_positions))
            deduped_positions = []
            for pos in all_uid_positions:
                if not deduped_positions or pos - deduped_positions[-1] > 1000:
                    deduped_positions.append(pos)

            # Extract date from log filename
            file_date = self._extract_date_from_file(log_file)

            # Get relative path
            try:
                relative_path = log_file.relative_to(self.root_path)
            except ValueError:
                relative_path = log_file

            # For each UID mention, look for all keys in nearby context
            for start_pos in deduped_positions:
                # Search within 50000 chars after this UID
                context = content[start_pos:start_pos + 50000]

                # Extract all keys from context
                keys = self._extract_all_keys_from_context(context)

                # Skip if no PICC key found
                if not keys['picc']:
                    continue

                # Skip factory keys (all zeros)
                if keys['picc'] == "00000000000000000000000000000000":
                    continue

                try:
                    picc_key = bytes.fromhex(keys['picc'])
                    app_read_key = bytes.fromhex(keys['app_read']) if keys['app_read'] else bytes(16)
                    sdm_mac_key = bytes.fromhex(keys['sdm_mac']) if keys['sdm_mac'] else bytes(16)

                    # Skip if app/sdm keys are factory (only PICC is non-factory)
                    app_is_factory = app_read_key == bytes(16) or keys['app_read'] == "00000000000000000000000000000000"
                    sdm_is_factory = sdm_mac_key == bytes(16) or keys['sdm_mac'] == "00000000000000000000000000000000"

                    # Normalize factory keys to zeros
                    if keys['app_read'] == "00000000000000000000000000000000":
                        app_read_key = bytes(16)
                    if keys['sdm_mac'] == "00000000000000000000000000000000":
                        sdm_mac_key = bytes(16)

                    # Determine completeness for notes
                    if not app_is_factory and not sdm_is_factory:
                        notes = "Complete key set extracted from TUI log"
                        status = "log_complete"
                    elif not app_is_factory or not sdm_is_factory:
                        notes = "Partial key set from TUI log (some keys unknown)"
                        status = "log_partial"
                    else:
                        notes = "PICC key only from TUI log (App Read & SDM MAC unknown)"
                        status = "log_picc_only"

                    candidate = KeyRecoveryCandidate(
                        uid=uid_normalized,
                        source_file=f"{relative_path} (log)",
                        picc_master_key=picc_key,
                        app_read_key=app_read_key,
                        sdm_file_read_key=sdm_mac_key,
                        status=status,
                        provisioned_date=file_date,
                        notes=notes,
                        file_date=file_date,
                    )

                    candidates.append(candidate)

                except (ValueError, IndexError) as e:
                    log.debug(f"Failed to parse keys from log context: {e}")
                    continue

        except Exception as e:
            log.debug(f"Error scanning log {log_file}: {e}")

        return candidates

    def scan_for_uid(self, uid: str) -> list[KeyRecoveryCandidate]:
        """Scan all CSV files and log files for matching UID, deduplicate by all 3 keys.

        Searches all CSV files and TUI log files in the tree and deduplicates
        candidates with identical (picc_master_key, app_read_key, sdm_file_read_key) tuples.

        Args:
            uid: Tag UID to search for (hex string)

        Returns:
            Deduplicated list of key candidates, sorted by completeness then file date
        """
        uid_normalized = uid.upper().replace(" ", "")
        csv_files = self.find_all_csv_files()
        log_files = self.find_all_log_files()

        log.info(f"Scanning {len(csv_files)} CSV + {len(log_files)} log files for UID {uid_normalized}")

        # Deduplicate by ALL THREE KEYS as a tuple
        # Key: (picc_master_key, app_read_key, sdm_file_read_key)
        candidates_dict: dict[tuple[bytes, bytes, bytes], KeyRecoveryCandidate] = {}

        def _get_completeness_score(candidate: KeyRecoveryCandidate) -> int:
            """Return completeness score: 2 = complete, 1 = partial, 0 = PICC only."""
            app_zero = candidate.app_read_key == bytes(16)
            sdm_zero = candidate.sdm_file_read_key == bytes(16)
            if not app_zero and not sdm_zero:
                return 2  # Complete
            elif not app_zero or not sdm_zero:
                return 1  # Partial
            else:
                return 0  # PICC only

        # Scan CSV files first (these usually have complete key sets)
        for csv_file in csv_files:
            try:
                with csv_file.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["uid"].upper() == uid_normalized:
                            picc_key = bytes.fromhex(row["picc_master_key"])

                            # Skip factory keys (all zeros)
                            if picc_key == bytes(16):
                                log.debug(f"Skipping factory key (all zeros) from {csv_file}")
                                continue

                            # Extract date from filename or use mtime
                            file_date = self._extract_date_from_file(csv_file)

                            # Get relative path from root
                            try:
                                relative_path = csv_file.relative_to(self.root_path)
                            except ValueError:
                                relative_path = csv_file

                            # Handle both old (sdm_mac_key) and new (sdm_file_read_key) column names
                            sdm_key = row.get("sdm_file_read_key") or row.get("sdm_mac_key", "")

                            app_read_key = bytes.fromhex(row["app_read_key"])
                            sdm_file_read_key = bytes.fromhex(sdm_key)

                            candidate = KeyRecoveryCandidate(
                                uid=row["uid"],
                                source_file=str(relative_path),
                                picc_master_key=picc_key,
                                app_read_key=app_read_key,
                                sdm_file_read_key=sdm_file_read_key,
                                status=row["status"],
                                provisioned_date=row["provisioned_date"],
                                notes=row.get("notes", ""),
                                file_date=file_date,
                            )

                            # Deduplicate by all three keys
                            key_tuple = (picc_key, app_read_key, sdm_file_read_key)
                            if key_tuple not in candidates_dict:
                                candidates_dict[key_tuple] = candidate
                            # If duplicate, keep the one with newer date
                            elif candidate.file_date > candidates_dict[key_tuple].file_date:
                                candidates_dict[key_tuple] = candidate

            except Exception as e:
                log.debug(f"Error reading {csv_file}: {e}")
                continue

        # Scan log files for additional keys
        for log_file in log_files:
            log_candidates = self._scan_log_for_keys(log_file, uid_normalized)
            for candidate in log_candidates:
                # Skip factory keys
                if candidate.picc_master_key == bytes(16):
                    log.debug(f"Skipping factory key from log {log_file.name}")
                    continue

                # Deduplicate by all three keys
                key_tuple = (candidate.picc_master_key, candidate.app_read_key, candidate.sdm_file_read_key)
                if key_tuple not in candidates_dict:
                    candidates_dict[key_tuple] = candidate
                    log.debug(f"Found new key set in log: {log_file.name}")
                # If duplicate, keep the one with newer date
                elif candidate.file_date > candidates_dict[key_tuple].file_date:
                    candidates_dict[key_tuple] = candidate

        candidates = list(candidates_dict.values())

        # Sort by: 1) completeness (complete first), 2) file_date (newest first)
        candidates.sort(key=lambda c: (-_get_completeness_score(c), c.file_date), reverse=True)

        log.info(f"Found {len(candidates)} unique key set candidates for UID {uid_normalized}")
        return candidates

    def test_key_candidate(
        self, candidate: KeyRecoveryCandidate, card: NTag424CardConnection
    ) -> bool:
        """Test if a key candidate works with the physical tag.

        Args:
            candidate: Key candidate to test
            card: Card connection to test against

        Returns:
            True if the key successfully authenticated
        """
        # Lazy import to avoid circular dependency
        from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2

        log.info(f"Testing key from {candidate.source_file}")

        # Try authenticating with the PICC master key
        try:
            with AuthenticateEV2(candidate.picc_master_key, key_no=0)(card):
                log.info("✓ Key candidate WORKS!")
                candidate.tested = True
                candidate.works = True
                return True
        except Exception as e:
            log.debug(f"Key candidate failed: {e}")
            candidate.tested = True
            candidate.works = False
            return False

    def recover_keys_for_tag(
        self, uid: str, card: NTag424CardConnection
    ) -> KeyRecoveryCandidate | None:
        """Attempt to recover working keys for a tag.

        Args:
            uid: Tag UID
            card: Connected card to test against

        Returns:
            Working KeyRecoveryCandidate if found, None otherwise
        """
        log.info(f"Starting key recovery for UID {uid}")

        candidates = self.scan_for_uid(uid)
        log.info(f"Found {len(candidates)} key candidates in backup files")

        if not candidates:
            log.warning(f"No key candidates found for UID {uid}")
            return None

        # Test each candidate
        for i, candidate in enumerate(candidates, 1):
            log.info(f"Testing candidate {i}/{len(candidates)} from {candidate.source_file}")
            if self.test_key_candidate(candidate, card):
                return candidate

        log.warning(f"No working keys found for UID {uid}")
        return None

    def try_factory_reset(self, uid: str, card: NTag424CardConnection) -> bool:
        """Test if tag is still in factory state.

        Args:
            uid: Tag UID
            card: Connected card

        Returns:
            True if factory keys work
        """
        # Lazy import to avoid circular dependency
        from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2

        log.info(f"Testing factory keys for UID {uid}")

        try:
            with AuthenticateEV2(FACTORY_KEY, key_no=0)(card):
                log.info("✓ Tag is in FACTORY state (factory keys work)")
                return True
        except Exception as e:
            log.debug(f"Factory keys failed: {e}")
            return False
