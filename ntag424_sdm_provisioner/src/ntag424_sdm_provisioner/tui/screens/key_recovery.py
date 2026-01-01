"""Key Recovery Screen - Discover and recover lost keys from backup files."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, OptionList, Static
from textual.widgets.option_list import Option
from textual.worker import Worker, WorkerState

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.services.key_recovery_service import (
    KeyRecoveryCandidate,
    KeyRecoveryService,
)
from ntag424_sdm_provisioner.tui.commands.key_recovery_command import KeyRecoveryCommand
from ntag424_sdm_provisioner.tui.widgets import TagStatusWidget
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


log = logging.getLogger(__name__)


@dataclass
class UIDSummary:
    """Summary of all key candidates for a single UID."""

    uid: str
    candidate_count: int  # Number of distinct key sets
    backup_files: list[str]  # List of backup file paths
    most_recent_date: str  # Most recent backup date
    candidates: list[KeyRecoveryCandidate]  # All candidates


class KeyRecoveryScreen(Screen):
    """Screen for discovering and recovering lost keys from backup files."""

    CSS = """
    KeyRecoveryScreen {
        align: center middle;
    }

    #recovery_container {
        width: 100;
        height: auto;
        max-height: 95%;
        border: solid $primary;
        padding: 1 2;
    }

    #recovery_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    #summary_section {
        width: 100%;
        height: auto;
        max-height: 5;
        border: solid $primary;
        padding: 0 1;
        margin-bottom: 1;
    }

    #candidates_section {
        width: 100%;
        height: auto;
        max-height: 30;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }

    #candidate_list {
        width: 100%;
        height: 20;
        border: solid $accent;
    }

    #db_status_box {
        width: 100%;
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: double $accent;
    }

    #status_label {
        width: 100%;
        padding: 1;
        min-height: 2;
        border: solid $primary;
    }

    #button_container {
        width: 100%;
        height: auto;
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
        padding: 1;
    }

    Button {
        margin: 0 1;
    }

    .highlight {
        background: $accent 30%;
        color: $text;
    }
    """

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager

        # Use project root to ensure we scan all directories including .history
        # Walk up to find the project root (contains both tag_keys.csv and ntag424_sdm_provisioner/)
        project_root = Path.cwd()
        while project_root.parent != project_root:
            if (project_root / "tag_keys.csv").exists() or (project_root / "ntag424_sdm_provisioner").exists():
                break
            project_root = project_root.parent

        self.recovery_service = KeyRecoveryService(root_path=project_root)
        self.uid_summaries: dict[str, UIDSummary] = {}
        self.scanned_uid: str | None = None
        self.total_files_scanned = 0
        self.total_keys_found = 0
        self.last_successful_test: dict[str, Any] | None = None  # Store successful test results

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="recovery_container"):
            yield Label("🔍 Key Recovery Tool", id="recovery_title")

            # Tag status widget - shows hardware + database state
            yield TagStatusWidget(id="tag_status")

            # Summary section - compact aggregate stats
            with Vertical(id="summary_section"):
                yield Static("Scanning backup files...", id="summary_display")

            # Database status box
            yield Static("", id="db_status_box")

            # Candidates section - shows detailed candidates for selected UID
            with Vertical(id="candidates_section"):
                yield Label("Key Candidates (select one to test):", id="candidates_label")
                yield OptionList(id="candidate_list")

            yield Label("Status: Initializing...", id="status_label")

            with Vertical(id="button_container"):
                yield Button("Scan Tag", id="btn_scan", variant="primary")
                yield Button("Test Selected Key", id="btn_recover", variant="success", disabled=True)
                yield Button("Restore Key to DB", id="btn_restore", variant="warning", disabled=True)
                yield Button("Refresh", id="btn_refresh", variant="default")
                yield Button("Back", id="btn_back", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the screen and auto-scan backups."""
        self._worker_mgr = WorkerManager(self)
        self.query_one("#btn_scan", Button).focus()
        self._discover_all_tags()

    def _scan_log_file_for_uid(self, log_file: Path, target_uid: str) -> list[KeyRecoveryCandidate]:
        """Scan a log file for key information for a specific UID.

        Args:
            log_file: Path to log file
            target_uid: UID to search for (uppercase, no spaces)

        Returns:
            List of key candidates found in the log for this UID
        """
        import re

        candidates = []

        try:
            with log_file.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Find all UID mentions
            uid_pattern = r'Tag UID:\s*([0-9A-Fa-f]{14})'
            uid_matches = list(re.finditer(uid_pattern, content))

            for uid_match in uid_matches:
                found_uid = uid_match.group(1).upper()

                # Skip if not the target UID
                if found_uid != target_uid:
                    continue

                # Search for auth keys within 50000 chars after this UID
                # (provisioning logs can be verbose with full crypto traces)
                start_pos = uid_match.start()
                context = content[start_pos:start_pos + 50000]

                # Look for: Auth key: <32 hex chars> (non-factory keys)
                auth_key_pattern = r'Auth key:\s*([0-9a-fA-F]{32})'
                for key_match in re.finditer(auth_key_pattern, context):
                    picc_key_hex = key_match.group(1).upper()

                    # Skip factory keys (all zeros)
                    if picc_key_hex == "00000000000000000000000000000000":
                        continue

                    try:
                        picc_key = bytes.fromhex(picc_key_hex)

                        # Extract date from log filename
                        file_date = self.recovery_service._extract_date_from_file(log_file)

                        # Get relative path
                        try:
                            relative_path = log_file.relative_to(self.recovery_service.root_path)
                        except ValueError:
                            relative_path = log_file

                        # Create candidate
                        candidate = KeyRecoveryCandidate(
                            uid=found_uid,
                            source_file=f"{relative_path} (log)",
                            picc_master_key=picc_key,
                            app_read_key=bytes(16),  # Unknown from logs
                            sdm_file_read_key=bytes(16),  # Unknown from logs
                            status="log_extracted",
                            provisioned_date=file_date,
                            notes="Extracted from TUI log file - app keys unknown",
                            file_date=file_date,
                        )

                        candidates.append(candidate)

                    except (ValueError, IndexError):
                        continue

        except Exception as e:
            log.debug(f"Error scanning log {log_file}: {e}")

        return candidates

    def _discover_all_tags(self) -> None:
        """Scan all CSV and log files in tree, collect all UIDs and keys."""
        self._update_status("Scanning for CSV and log files...")

        try:
            import csv
            import os
            import re

            # Group all candidates by UID
            all_candidates_by_uid: dict[str, list[KeyRecoveryCandidate]] = {}
            csv_count = 0
            log_count = 0

            # Single os.walk - collect from both CSV and log files
            for dirpath, dirnames, filenames in os.walk(self.recovery_service.root_path):
                for filename in filenames:
                    file_path = Path(dirpath) / filename

                    # Process CSV files
                    if filename.endswith('.csv'):
                        csv_count += 1
                        try:
                            with file_path.open("r", encoding="utf-8") as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    uid = row["uid"].upper()
                                    file_date = self.recovery_service._extract_date_from_file(file_path)

                                    try:
                                        relative_path = file_path.relative_to(self.recovery_service.root_path)
                                    except ValueError:
                                        relative_path = file_path

                                    # Handle both column name variants
                                    sdm_key = row.get("sdm_file_read_key") or row.get("sdm_mac_key", "")

                                    candidate = KeyRecoveryCandidate(
                                        uid=uid,
                                        source_file=str(relative_path),
                                        picc_master_key=bytes.fromhex(row["picc_master_key"]),
                                        app_read_key=bytes.fromhex(row["app_read_key"]),
                                        sdm_file_read_key=bytes.fromhex(sdm_key),
                                        status=row["status"],
                                        provisioned_date=row["provisioned_date"],
                                        notes=row.get("notes", ""),
                                        file_date=file_date,
                                    )

                                    if uid not in all_candidates_by_uid:
                                        all_candidates_by_uid[uid] = []
                                    all_candidates_by_uid[uid].append(candidate)
                        except Exception as e:
                            log.debug(f"Error reading CSV {file_path}: {e}")

                    # Process log files - extract ALL keys (PICC, App Read, SDM MAC)
                    elif filename.startswith('tui_') and filename.endswith('.log'):
                        log_count += 1
                        try:
                            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()

                            # Find all UIDs in various formats
                            uid_pattern = r'Tag UID:\s*([0-9A-Fa-f]{14})'
                            uid_csv_pattern = r"(?:UID|uid[=:])[\s']*([0-9A-Fa-f]{14})"

                            all_uid_matches = []
                            for m in re.finditer(uid_pattern, content):
                                all_uid_matches.append((m.group(1).upper(), m.start()))
                            for m in re.finditer(uid_csv_pattern, content):
                                all_uid_matches.append((m.group(1).upper(), m.start()))

                            # Group by UID and dedupe positions
                            uid_positions: dict[str, list[int]] = {}
                            for uid, pos in all_uid_matches:
                                if uid not in uid_positions:
                                    uid_positions[uid] = []
                                uid_positions[uid].append(pos)

                            file_date = self.recovery_service._extract_date_from_file(file_path)
                            try:
                                relative_path = file_path.relative_to(self.recovery_service.root_path)
                            except ValueError:
                                relative_path = file_path

                            for uid, uid_pos_list in uid_positions.items():
                                # Dedupe positions within 1000 chars
                                sorted_positions = sorted(set(uid_pos_list))
                                deduped = []
                                for pos in sorted_positions:
                                    if not deduped or pos - deduped[-1] > 1000:
                                        deduped.append(pos)

                                for start_pos in deduped:
                                    context = content[start_pos:start_pos + 50000]

                                    # Extract all keys using the service's helper
                                    keys = self.recovery_service._extract_all_keys_from_context(context)

                                    # Skip if no PICC key or factory key
                                    if not keys['picc'] or keys['picc'] == "00000000000000000000000000000000":
                                        continue

                                    try:
                                        picc_key = bytes.fromhex(keys['picc'])
                                        app_key = bytes.fromhex(keys['app_read']) if keys['app_read'] and keys['app_read'] != "00000000000000000000000000000000" else bytes(16)
                                        sdm_key = bytes.fromhex(keys['sdm_mac']) if keys['sdm_mac'] and keys['sdm_mac'] != "00000000000000000000000000000000" else bytes(16)

                                        # Determine status based on completeness
                                        app_is_zero = app_key == bytes(16)
                                        sdm_is_zero = sdm_key == bytes(16)
                                        if not app_is_zero and not sdm_is_zero:
                                            status = "log_complete"
                                            notes = "Complete key set from TUI log"
                                        elif not app_is_zero or not sdm_is_zero:
                                            status = "log_partial"
                                            notes = "Partial key set from TUI log"
                                        else:
                                            status = "log_picc_only"
                                            notes = "PICC only from TUI log"

                                        candidate = KeyRecoveryCandidate(
                                            uid=uid,
                                            source_file=f"{relative_path} (log)",
                                            picc_master_key=picc_key,
                                            app_read_key=app_key,
                                            sdm_file_read_key=sdm_key,
                                            status=status,
                                            provisioned_date=file_date,
                                            notes=notes,
                                            file_date=file_date,
                                        )

                                        if uid not in all_candidates_by_uid:
                                            all_candidates_by_uid[uid] = []
                                        all_candidates_by_uid[uid].append(candidate)

                                    except (ValueError, IndexError) as e:
                                        log.debug(f"Failed to parse keys: {e}")

                        except Exception as e:
                            log.debug(f"Error reading log {file_path}: {e}")

            # Deduplicate and build summaries
            self.uid_summaries = {}
            for uid, candidates in all_candidates_by_uid.items():
                # Deduplicate by all three keys (picc_master_key, app_read_key, sdm_file_read_key)
                unique_keys = {}
                for candidate in candidates:
                    key_tuple = (candidate.picc_master_key, candidate.app_read_key, candidate.sdm_file_read_key)
                    if key_tuple not in unique_keys:
                        unique_keys[key_tuple] = candidate

                unique_candidates = list(unique_keys.values())
                backup_files = sorted(set(c.source_file for c in unique_candidates))
                dates = sorted([c.file_date for c in unique_candidates], reverse=True)

                self.uid_summaries[uid] = UIDSummary(
                    uid=uid,
                    candidate_count=len(unique_candidates),
                    backup_files=backup_files,
                    most_recent_date=dates[0] if dates else "Unknown",
                    candidates=unique_candidates,
                )

            # Calculate total keys across all UIDs
            self.total_files_scanned = csv_count + log_count
            self.total_keys_found = sum(s.candidate_count for s in self.uid_summaries.values())

            self._update_summary_display()
            self._update_status(
                f"Found {len(self.uid_summaries)} tag(s), {self.total_keys_found} keys in {self.total_files_scanned} files"
            )

        except Exception as e:
            log.error(f"Error discovering tags: {e}")
            self._update_status(f"Error: {e}")
            self.query_one("#summary_display", Static).update(f"Error scanning: {e}")

    def _update_summary_display(self) -> None:
        """Update the summary display with compact aggregate stats."""
        if not self.uid_summaries:
            self.query_one("#summary_display", Static).update(
                "No tags found - scan CSV/log files in project tree"
            )
            return

        # Compact aggregate stats
        display = f"📊 {len(self.uid_summaries)} tags | {self.total_keys_found} keys | {self.total_files_scanned} files scanned"

        # Add scanned tag indicator if present
        if self.scanned_uid and self.scanned_uid in self.uid_summaries:
            summary = self.uid_summaries[self.scanned_uid]
            display += f"\n🎯 Scanned: {self.scanned_uid} ({summary.candidate_count} candidate keys)"

        self.query_one("#summary_display", Static).update(display)

    def _update_candidates_display(self, uid: str | None = None) -> None:
        """Update candidates display for a specific UID."""
        option_list = self.query_one("#candidate_list", OptionList)
        db_status_box = self.query_one("#db_status_box", Static)

        if uid is None or uid not in self.uid_summaries:
            option_list.clear_options()
            option_list.add_option(Option("No candidates - scan a tag first", disabled=True))
            db_status_box.update("")
            return

        summary = self.uid_summaries[uid]

        # Check current key in main database
        current_key_status = "Not set"
        current_key_match = None
        try:
            current_keys = self.key_manager.get_tag_keys(uid)
            if current_keys:
                current_key_status = f"{current_keys.status}"
                # Check if current key matches any candidate
                for i, candidate in enumerate(summary.candidates, 1):
                    if current_keys.picc_master_key == candidate.picc_master_key.hex():
                        current_key_match = i
                        break
        except Exception:
            pass

        # Update database status box
        status_display = "═" * 50 + "\n"
        status_display += f"DATABASE STATUS: {current_key_status.upper()}\n"
        if current_key_match:
            status_display += f"✓ KEY ALREADY SET - MATCHES CANDIDATE #{current_key_match}\n"
            status_display += "  Recovery may not be needed!\n"
        else:
            status_display += "⚠ Current key does not match any backup candidates\n"
            status_display += "  Recovery recommended if tag is not working\n"
        status_display += "═" * 50
        db_status_box.update(status_display)

        # Populate OptionList with candidates
        option_list.clear_options()
        for i, candidate in enumerate(summary.candidates, 1):
            match_marker = " ◀ CURRENT" if i == current_key_match else ""

            # Determine if this is a complete or partial key set
            app_is_zero = candidate.app_read_key.hex() == "00000000000000000000000000000000"
            sdm_is_zero = candidate.sdm_file_read_key.hex() == "00000000000000000000000000000000"
            is_complete = not app_is_zero and not sdm_is_zero
            completeness_marker = " [COMPLETE]" if is_complete else " [PARTIAL]"

            # Build option prompt showing ALL key details
            prompt = f"#{i}: {candidate.source_file}{match_marker}{completeness_marker}\n"

            # PICC Master Key (always present)
            prompt += f"    PICC Master: ✓ {candidate.picc_master_key.hex().upper()}\n"

            # App Read Key
            if app_is_zero:
                prompt += f"    App Read:    ✗ <UNKNOWN>\n"
            else:
                prompt += f"    App Read:    ✓ {candidate.app_read_key.hex().upper()}\n"

            # SDM MAC Key
            if sdm_is_zero:
                prompt += f"    SDM MAC:     ✗ <UNKNOWN>\n"
            else:
                prompt += f"    SDM MAC:     ✓ {candidate.sdm_file_read_key.hex().upper()}\n"

            prompt += f"    Status: {candidate.status} | Date: {candidate.file_date}\n"
            if candidate.notes and "app keys unknown" not in candidate.notes.lower():
                prompt += f"    Notes: {candidate.notes[:60]}...\n" if len(candidate.notes) > 60 else f"    Notes: {candidate.notes}\n"

            option_list.add_option(Option(prompt.strip(), id=str(i)))

    def _update_status(self, text: str) -> None:
        """Update status label."""
        self.query_one("#status_label", Label).update(f"Status: {text}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle key candidate selection."""
        # Enable the test button when a candidate is selected
        self.query_one("#btn_recover", Button).disabled = False
        selected_id = event.option.id
        self._update_status(f"Selected candidate #{selected_id} - click 'Test Selected Key'")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn_back":
            self.app.pop_screen()
        elif event.button.id == "btn_refresh":
            self._discover_all_tags()
        elif event.button.id == "btn_scan":
            self._scan_tag()
        elif event.button.id == "btn_recover":
            self._start_recovery()
        elif event.button.id == "btn_restore":
            self._restore_keys()

    def _scan_tag(self) -> None:
        """Scan tag to get UID and filter candidates."""
        self._update_status("Scanning tag...")

        try:
            from ntag424_sdm_provisioner.card_factory import CardConnectionFactory
            from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
            from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
            from ntag424_sdm_provisioner.commands.select_picc_application import (
                SelectPiccApplication,
            )
            from ntag424_sdm_provisioner.sequence_logger import SequenceLogger

            with CardConnectionFactory.create(SequenceLogger()) as conn:
                conn.send(SelectPiccApplication())
                version_info = conn.send(GetChipVersion())
                uid = version_info.uid.hex().upper()

                # Read key versions from hardware
                key0_resp = conn.send(GetKeyVersion(key_no=0))
                key1_resp = conn.send(GetKeyVersion(key_no=1))
                key3_resp = conn.send(GetKeyVersion(key_no=3))

                # Update tag status widget with hardware info
                tag_status = self.query_one("#tag_status", TagStatusWidget)
                tag_status.update_from_hardware(
                    uid=uid,
                    key0_ver=key0_resp.version,
                    key1_ver=key1_resp.version,
                    key3_ver=key3_resp.version
                )

                # Update tag status widget with database info
                tag_status.update_from_database(self.key_manager, uid)

                self.scanned_uid = uid
                self._update_summary_display()
                self._update_candidates_display(uid)

                if uid in self.uid_summaries:
                    summary = self.uid_summaries[uid]
                    self._update_status(
                        f"Tag {uid} found - {summary.candidate_count} key set(s) available"
                    )
                    # Enable recovery button
                    self.query_one("#btn_recover", Button).disabled = False
                else:
                    self._update_status(f"Tag {uid} scanned - No keys found in backups")
                    self.query_one("#btn_recover", Button).disabled = True

        except Exception as e:
            log.error(f"Error scanning tag: {e}")
            self._update_status(f"Error scanning tag: {e}")

    def _start_recovery(self) -> None:
        """Start the key recovery process for the selected candidate."""
        if not self.scanned_uid:
            self._update_status("Please scan a tag first")
            return

        if self.scanned_uid not in self.uid_summaries:
            self._update_status("No keys found for scanned tag")
            return

        # Get selected candidate from OptionList
        option_list = self.query_one("#candidate_list", OptionList)
        selected = option_list.highlighted
        if selected is None:
            self._update_status("Please select a candidate key to test")
            return

        # Get the candidate index from the option ID
        try:
            candidate_idx = int(str(option_list.get_option_at_index(selected).id)) - 1
            summary = self.uid_summaries[self.scanned_uid]
            selected_candidate = summary.candidates[candidate_idx]

            log.info(f"Testing selected candidate #{candidate_idx + 1} for UID {self.scanned_uid}")
            self._update_status(f"Testing candidate #{candidate_idx + 1} from {selected_candidate.source_file}...")

            # Disable buttons during recovery
            self.query_one("#btn_recover", Button).disabled = True
            self.query_one("#btn_scan", Button).disabled = True
            self.query_one("#btn_refresh", Button).disabled = True

            # Execute recovery command with only the selected candidate
            command = KeyRecoveryCommand(
                self.recovery_service,
                self.key_manager,
                selected_candidate=selected_candidate,
            )
            self._worker_mgr.execute_command(
                command, _status_label_id="status_label", timer_label_id="status_label"
            )
        except (ValueError, IndexError) as e:
            log.error(f"Failed to get selected candidate: {e}")
            self._update_status("Error: Could not get selected candidate")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        self._worker_mgr.cleanup()

        try:
            if event.state == WorkerState.SUCCESS:
                result = event.worker.result
                assert isinstance(result, dict)
                self._on_recovery_success(result)
            elif event.state == WorkerState.ERROR:
                error = event.worker.error
                if isinstance(error, Exception):
                    self._on_recovery_failure(error)
                else:
                    self._on_recovery_failure(Exception("Unknown error"))
        except Exception:
            pass

        # Re-enable buttons
        self.query_one("#btn_scan", Button).disabled = False
        self.query_one("#btn_refresh", Button).disabled = False
        if self.scanned_uid and self.scanned_uid in self.uid_summaries:
            self.query_one("#btn_recover", Button).disabled = False

    def _on_recovery_success(self, result: dict[str, Any]) -> None:
        """Handle successful key recovery."""
        log.info(f"Key recovery completed: {result}")

        if result.get("recovered"):
            candidate = result["candidate"]

            # Store successful test result for later restore
            self.last_successful_test = result

            # Enable the "Restore Key to DB" button
            self.query_one("#btn_restore", Button).disabled = False

            self._update_status("✓ Key test successful! Click 'Restore Key to DB' to save")
            self._update_candidates_display(result["uid"])

            # Show success message WITHOUT saying it's been restored yet
            self.query_one("#candidates_display", Static).update(
                f"✓ Working key found!\n\n"
                f"UID: {result['uid']}\n"
                f"Source: {candidate['source_file']}\n"
                f"Status: {candidate['status']}\n"
                f"Date: {candidate.get('provisioned_date', 'N/A')}\n\n"
                f"⚠ NEXT STEP: Click 'Restore Key to DB' to save keys to database.\n"
                f"Keys are NOT saved automatically - you must restore manually."
            )
        elif result.get("is_factory"):
            self._update_status("Tag is in factory state - no recovery needed")
            self.query_one("#candidates_display", Static).update(
                f"UID: {result['uid']}\n\n"
                f"This tag is in FACTORY state (default keys).\n"
                f"No key recovery needed.\n\n"
                f"You can provision this tag using 'Configure Keys'."
            )
        # Check if auth delay was encountered
        elif result.get("auth_delay"):
            self._update_status("⚠ Authentication delay - tag in lockout mode")
            self.query_one("#candidates_display", Static).update(
                f"UID: {result['uid']}\n\n"
                f"⚠ AUTHENTICATION DELAY DETECTED\n\n"
                f"The tag is in lockout mode due to too many failed\n"
                f"authentication attempts (possibly from previous operations).\n\n"
                f"SOLUTION:\n"
                f"• Wait ~30 seconds for the lockout to clear\n"
                f"• Try 'Recover Keys' again\n"
                f"• The keys in the database may already be correct\n\n"
                f"Tested {result.get('candidates_tested', 0)} candidate(s) before lockout."
            )
        else:
            self._update_status("No working keys found")
            self.query_one("#candidates_display", Static).update(
                f"UID: {result['uid']}\n\n"
                f"Tested {result.get('candidates_tested', 0)} key candidate(s)\n"
                f"✗ No working keys found.\n\n"
                f"This tag's keys may be permanently lost."
            )

    def _on_recovery_failure(self, error: Exception) -> None:
        """Handle key recovery failure."""
        log.error(f"Key recovery failed: {error}")
        self._update_status(f"Recovery failed: {error}")

    def _restore_keys(self) -> None:
        """Restore the last successfully tested keys to the database."""
        if not self.last_successful_test:
            self._update_status("No successful test to restore - test a key first")
            return

        try:
            from datetime import datetime
            from ntag424_sdm_provisioner.csv_key_manager import TagKeys

            result = self.last_successful_test
            candidate = result["candidate"]
            uid = result["uid"]

            # Determine status based on key completeness
            app_is_zero = candidate["app_read_key"] == "00000000000000000000000000000000"
            sdm_is_zero = candidate["sdm_file_read_key"] == "00000000000000000000000000000000"

            if app_is_zero and sdm_is_zero:
                # PICC only - warn strongly
                status = "picc_only"
                notes = (
                    f"WARNING: Only PICC Master Key verified from {candidate['source_file']} at {datetime.now().isoformat()}. "
                    f"App Read Key and SDM MAC Key are UNKNOWN. SDM CMAC validation WILL FAIL until correct keys are found. "
                    f"Try finding a complete key set in backups or re-provision the tag."
                )
                log.warning(f"[KEY RECOVERY] Restoring PARTIAL key set - SDM CMAC will fail!")
            elif app_is_zero or sdm_is_zero:
                # Partial key set
                status = "partial_keys"
                missing = []
                if app_is_zero:
                    missing.append("App Read Key")
                if sdm_is_zero:
                    missing.append("SDM MAC Key")
                notes = (
                    f"PARTIAL: {', '.join(missing)} unknown. Verified from {candidate['source_file']} at {datetime.now().isoformat()}. "
                    f"SDM CMAC validation may fail if SDM MAC key is wrong."
                )
                log.warning(f"[KEY RECOVERY] Restoring partial key set - missing: {missing}")
            else:
                # Complete key set
                status = "provisioned"
                notes = f"All 3 keys recovered from {candidate['source_file']} at {datetime.now().isoformat()}"
                log.info(f"[KEY RECOVERY] Restoring COMPLETE key set")

            # Create TagKeys from the successful test result
            recovered_keys = TagKeys(
                uid=uid,
                picc_master_key=candidate["picc_master_key"],
                app_read_key=candidate["app_read_key"],
                sdm_mac_key=candidate["sdm_file_read_key"],
                provisioned_date=candidate.get("provisioned_date") or datetime.now().isoformat(),
                status=status,
                notes=notes,
            )

            log.info(f"[KEY RECOVERY] Saving recovered keys to database:")
            log.info(f"  UID: {uid}")
            log.info(f"  PICC Master Key: {recovered_keys.picc_master_key}")
            log.info(f"  App Read Key: {recovered_keys.app_read_key}")
            log.info(f"  SDM MAC Key: {recovered_keys.sdm_mac_key}")
            log.info(f"  Status: {recovered_keys.status}")
            log.info(f"  Source: {candidate['source_file']}")

            self.key_manager.save_tag_keys(uid, recovered_keys)
            log.info("✓ Recovered keys saved to database")

            # Update tag status widget to show new database state
            tag_status = self.query_one("#tag_status", TagStatusWidget)
            tag_status.update_from_database(self.key_manager, uid)

            # Disable restore button (already restored)
            self.query_one("#btn_restore", Button).disabled = True

            self._update_status(f"✓ Keys restored to database for UID {uid}")

        except Exception as e:
            log.error(f"Failed to restore keys: {e}")
            self._update_status(f"Failed to restore keys: {e}")
