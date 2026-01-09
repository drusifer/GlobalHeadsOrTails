"""Key Recovery Screen - Discover and recover lost keys from backup files."""

import csv
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static
from textual.worker import Worker, WorkerState

from ntag424_sdm_provisioner.card_factory import CardConnectionFactory
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger
from ntag424_sdm_provisioner.services.key_recovery_service import (
    KeyRecoveryCandidate,
    KeyRecoveryService,
)
from ntag424_sdm_provisioner.tui.commands.key_recovery_command import KeyRecoveryCommand
from ntag424_sdm_provisioner.tui.widgets import (
    KeyCandidate,
    KeyCandidatesTable,
    PhoneTapWidget,
    TagKeysDetailWidget,
    TagStatusWidget,
)
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
    """Screen for discovering and recovering lost keys from backup files.

    Layout (48 rows fixed height, wide horizontal layout):
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │ KEY RECOVERY TOOL                                                    [Status]   │
    ├──────────────────────────────────┬──────────────────────────────────────────────┤
    │ TAG STATUS (TagStatusWidget)     │  KEY DETAILS (TagKeysDetailWidget)           │
    │ UID: 04B7664A2F7080  HW:PRO      │  KEY 0 (PICC): 825f... DB:✓ HW:v01 TEST:✓   │
    │ Keys: PICC✓ App✓ SDM✓            │  KEY 1 (App):  3865... DB:✓ HW:v01 TEST:✓   │
    │                                  │  KEY 3 (SDM):  c099... DB:✓ HW:v01 TEST:-   │
    ├──────────────────────────────────┴──────────────────────────────────────────────┤
    │ BACKUP KEY CANDIDATES (KeyCandidatesTable)                                       │
    │ Source         │ Status │ Date    │ PICC    │ App     │ SDM     │ Tested        │
    │ backup1.csv    │ prov   │ 12/25   │ 825f... │ 3865... │ c099... │ ✓P ✓A -S      │
    │ tag_keys.csv   │ prov   │ 11/08   │ 825f... │ 3865... │ c099... │ -P -A -S      │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ PHONE TAP TEST (PhoneTapWidget) - only shown after SDM validation               │
    │ URL: ...?uid=04B7664A2F7080&ctr=000005&cmac=A1B2C3D4                            │
    │ ✓ VALID - CMAC matches                                                          │
    ├─────────────────────────────────────────────────────────────────────────────────┤
    │ [Scan Tag] [Test Selected] [Restore to DB] [Set to Factory] [Refresh] [Back]   │
    └─────────────────────────────────────────────────────────────────────────────────┘
    """

    CSS = """
    KeyRecoveryScreen {
        min-height: 48;
        height: 100%;
        width: 100%;
    }

    #main_container {
        width: 100%;
        height: 100%;
        min-height: 48;
        border: solid $primary;
        padding: 0 1;
    }

    #title_row {
        width: 100%;
        height: 1;
        layout: horizontal;
    }

    #recovery_title {
        width: 1fr;
        text-style: bold;
        color: $accent;
    }

    #status_label {
        width: 2fr;
        text-align: right;
        color: $text;
    }

    #top_section {
        width: 100%;
        height: 6;
        layout: horizontal;
    }

    #left_panel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }

    #right_panel {
        width: 2fr;
        height: 100%;
        border: solid $accent;
        padding: 0 1;
    }

    #candidates_section {
        width: 100%;
        height: 1fr;
        min-height: 15;
        border: solid $primary;
    }

    #candidates_label {
        height: 1;
        color: $accent;
        text-style: bold;
    }

    #candidates_table {
        height: 1fr;
    }

    #phone_tap {
        width: 100%;
        height: 6;
    }

    #result_section {
        width: 100%;
        height: 3;
        border: double $warning;
        padding: 0 1;
    }

    #button_row {
        width: 100%;
        height: 5;
        layout: grid;
        grid-size: 6;
        grid-gutter: 1;
        padding: 1 0;
    }

    #button_row Button {
        width: 100%;
        height: 3;
    }

    .hidden {
        display: none;
    }
    """

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager

        # Use project root to ensure we scan all directories including .history
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
        self.last_successful_test: dict[str, Any] | None = None
        self._selected_candidate_idx: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            # Title row with status
            with Horizontal(id="title_row"):
                yield Label("KEY RECOVERY TOOL", id="recovery_title")
                yield Label("Status: Initializing...", id="status_label")

            # Top section: Tag status (left) + Keys detail (right)
            with Horizontal(id="top_section"):
                with Vertical(id="left_panel"):
                    yield TagStatusWidget(id="tag_status")
                    yield Static("Scanning backups...", id="summary_display")
                with Vertical(id="right_panel"):
                    yield TagKeysDetailWidget(id="keys_detail")

            # Candidates table section
            with Vertical(id="candidates_section"):
                yield Label("BACKUP KEY CANDIDATES (select one to test)", id="candidates_label")
                yield KeyCandidatesTable(id="candidates_table")

            # SDM/Phone tap validation section
            yield PhoneTapWidget(id="phone_tap")

            # Result display section
            yield Static("", id="result_section")

            # Button row
            with Horizontal(id="button_row"):
                yield Button("Scan Tag", id="btn_scan", variant="primary")
                yield Button("Test Selected", id="btn_test", variant="success", disabled=True)
                yield Button("Restore to DB", id="btn_restore", variant="warning", disabled=True)
                yield Button("Set to Factory", id="btn_factory", variant="error", disabled=True)
                yield Button("Refresh", id="btn_refresh", variant="default")
                yield Button("Back", id="btn_back", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the screen and auto-scan backups."""
        self._worker_mgr = WorkerManager(self)
        self.query_one("#btn_scan", Button).focus()
        self._discover_all_tags()

    def _discover_all_tags(self) -> None:
        """Scan all CSV and log files in tree, collect all UIDs and keys."""
        self._update_status("Scanning for CSV and log files...")

        try:
            # Group all candidates by UID
            all_candidates_by_uid: dict[str, list[KeyRecoveryCandidate]] = {}
            csv_count = 0
            log_count = 0

            # Single os.walk - collect from both CSV and log files
            for dirpath, _dirnames, filenames in os.walk(self.recovery_service.root_path):
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

                    # Process log files
                    elif filename.startswith('tui_') and filename.endswith('.log'):
                        log_count += 1
                        try:
                            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()

                            # Find all UIDs in various formats
                            uid_pattern = r'Tag UID:\s*([0-9A-Fa-f]{14})'
                            uid_csv_pattern = r"(?:UID|uid[=:])[\s']*([0-9A-Fa-f]{14})"

                            all_uid_matches = [
                                (m.group(1).upper(), m.start())
                                for m in re.finditer(uid_pattern, content)
                            ]
                            all_uid_matches.extend(
                                (m.group(1).upper(), m.start())
                                for m in re.finditer(uid_csv_pattern, content)
                            )

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
                                sorted_positions = sorted(set(uid_pos_list))
                                deduped = []
                                for pos in sorted_positions:
                                    if not deduped or pos - deduped[-1] > 1000:
                                        deduped.append(pos)

                                for start_pos in deduped:
                                    context = content[start_pos:start_pos + 50000]
                                    keys = self.recovery_service._extract_all_keys_from_context(context)

                                    if not keys['picc'] or keys['picc'] == "00000000000000000000000000000000":
                                        continue

                                    try:
                                        picc_key = bytes.fromhex(keys['picc'])
                                        app_key = bytes.fromhex(keys['app_read']) if keys['app_read'] and keys['app_read'] != "00000000000000000000000000000000" else bytes(16)
                                        sdm_key = bytes.fromhex(keys['sdm_mac']) if keys['sdm_mac'] and keys['sdm_mac'] != "00000000000000000000000000000000" else bytes(16)

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
            self.query_one("#summary_display", Static).update("No tags found")
            return

        display = f"{len(self.uid_summaries)} tags | {self.total_keys_found} keys"
        if self.scanned_uid and self.scanned_uid in self.uid_summaries:
            summary = self.uid_summaries[self.scanned_uid]
            display += f"\nScanned: {summary.candidate_count} candidates"

        self.query_one("#summary_display", Static).update(display)

    def _update_candidates_table(self, uid: str | None = None) -> None:
        """Update candidates table for a specific UID."""
        table = self.query_one("#candidates_table", KeyCandidatesTable)

        if uid is None or uid not in self.uid_summaries:
            table.load_candidates([])
            return

        summary = self.uid_summaries[uid]

        # Convert KeyRecoveryCandidate to KeyCandidate for the table
        candidates = [
            KeyCandidate(
                source=c.source_file,
                status=c.status,
                date=c.file_date,
                picc_key=c.picc_master_key.hex(),
                app_key=c.app_read_key.hex(),
                sdm_key=c.sdm_file_read_key.hex(),
            )
            for c in summary.candidates
        ]
        table.load_candidates(candidates)

    def _update_keys_detail(self, uid: str | None = None) -> None:
        """Update the keys detail widget from database."""
        keys_detail = self.query_one("#keys_detail", TagKeysDetailWidget)

        if uid is None:
            keys_detail.clear()
            return

        try:
            tag_keys = self.key_manager.get_tag_keys(uid)
            keys_detail.update_from_database(tag_keys)
        except Exception:
            keys_detail.clear()

    def _update_status(self, text: str) -> None:
        """Update status label."""
        self.query_one("#status_label", Label).update(f"Status: {text}")

    def _update_result_section(self, text: str) -> None:
        """Update the result display section."""
        self.query_one("#result_section", Static).update(text)

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in candidates table."""
        self._selected_candidate_idx = event.cursor_row
        self.query_one("#btn_test", Button).disabled = False
        self._update_status(f"Selected candidate #{event.cursor_row + 1} - click 'Test Selected'")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn_back":
            self.app.pop_screen()
        elif event.button.id == "btn_refresh":
            self._discover_all_tags()
        elif event.button.id == "btn_scan":
            self._scan_tag()
        elif event.button.id == "btn_test":
            self._start_recovery()
        elif event.button.id == "btn_restore":
            self._restore_keys()
        elif event.button.id == "btn_factory":
            self._set_to_factory()

    def _scan_tag(self) -> None:
        """Scan tag to get UID and filter candidates."""
        self._update_status("Scanning tag...")

        try:
            with CardConnectionFactory.create(SequenceLogger()) as conn:
                conn.send(SelectPiccApplication())
                version_info = conn.send(GetChipVersion())
                uid = version_info.uid.uid

                # Read key versions from hardware
                key0_resp = conn.send(GetKeyVersion(key_no=0))
                key1_resp = conn.send(GetKeyVersion(key_no=1))
                key3_resp = conn.send(GetKeyVersion(key_no=3))

                # Update tag status widget
                tag_status = self.query_one("#tag_status", TagStatusWidget)
                tag_status.update_from_hardware(
                    uid=uid,
                    key0_ver=key0_resp.version,
                    key1_ver=key1_resp.version,
                    key3_ver=key3_resp.version
                )
                tag_status.update_from_database(self.key_manager, uid)

                # Update keys detail widget
                keys_detail = self.query_one("#keys_detail", TagKeysDetailWidget)
                keys_detail.update_from_hardware(key0_resp.version, key1_resp.version, key3_resp.version)
                self._update_keys_detail(uid)

                self.scanned_uid = uid
                self._update_summary_display()
                self._update_candidates_table(uid)

                # Enable factory button (can always set to factory)
                self.query_one("#btn_factory", Button).disabled = False

                if uid in self.uid_summaries:
                    summary = self.uid_summaries[uid]
                    self._update_status(f"Tag {uid[:8]}... - {summary.candidate_count} candidate(s)")
                else:
                    self._update_status(f"Tag {uid[:8]}... - No backups found")

        except Exception as e:
            log.error(f"Error scanning tag: {e}")
            self._update_status(f"Error: {e}")

    def _start_recovery(self) -> None:
        """Start the key recovery process for the selected candidate."""
        if not self.scanned_uid:
            self._update_status("Please scan a tag first")
            return

        if self.scanned_uid not in self.uid_summaries:
            self._update_status("No keys found for scanned tag")
            return

        table = self.query_one("#candidates_table", KeyCandidatesTable)
        if table.cursor_row is None:
            self._update_status("Please select a candidate to test")
            return

        candidate_idx = table.cursor_row
        summary = self.uid_summaries[self.scanned_uid]

        if candidate_idx >= len(summary.candidates):
            self._update_status("Invalid candidate selection")
            return

        selected_candidate = summary.candidates[candidate_idx]

        log.info(f"Testing candidate #{candidate_idx + 1} for UID {self.scanned_uid}")
        self._update_status(f"Testing candidate #{candidate_idx + 1}...")

        # Disable buttons during test
        self.query_one("#btn_test", Button).disabled = True
        self.query_one("#btn_scan", Button).disabled = True
        self.query_one("#btn_refresh", Button).disabled = True

        # Store index for updating test results later
        self._selected_candidate_idx = candidate_idx

        # Execute recovery command
        command = KeyRecoveryCommand(
            self.recovery_service,
            self.key_manager,
            selected_candidate=selected_candidate,
        )
        self._worker_mgr.execute_command(
            command, _status_label_id="status_label", timer_label_id="status_label"
        )

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
            self.query_one("#btn_test", Button).disabled = False

    def _on_recovery_success(self, result: dict[str, Any]) -> None:
        """Handle successful key recovery."""
        log.info(f"Key recovery completed: {result}")

        # Update test results in table and keys detail widget
        if self._selected_candidate_idx is not None:
            table = self.query_one("#candidates_table", KeyCandidatesTable)
            keys_detail = self.query_one("#keys_detail", TagKeysDetailWidget)

            if result.get("recovered"):
                # PICC key works
                table.update_test_results(self._selected_candidate_idx, picc_works=True)
                keys_detail.update_test_results(picc_works=True)

        if result.get("recovered"):
            candidate = result["candidate"]
            self.last_successful_test = result

            # Enable restore button
            self.query_one("#btn_restore", Button).disabled = False

            self._update_status("✓ Key works! Click 'Restore to DB' to save")
            self._update_result_section(
                f"[green bold]✓ Working key found![/]\n"
                f"Source: {candidate['source_file']}\n"
                f"[yellow]Click 'Restore to DB' to save keys to database[/]"
            )

        elif result.get("is_factory"):
            self._update_status("Tag is in factory state")
            self._update_result_section(
                "[yellow]Tag is in FACTORY state[/]\n"
                "Default keys are active. No recovery needed.\n"
                "Use 'Configure Keys' to provision this tag."
            )

        elif result.get("auth_delay"):
            self._update_status("⚠ Auth delay - tag locked out")
            self._update_result_section(
                f"[red]⚠ AUTHENTICATION DELAY[/]\n"
                f"Tag is in lockout mode. Wait ~30 seconds and try again.\n"
                f"Tested {result.get('candidates_tested', 0)} candidate(s)."
            )

        else:
            self._update_status("Key test failed")
            self._update_result_section(
                f"[red]✗ Key did not work[/]\n"
                f"Tested {result.get('candidates_tested', 0)} candidate(s).\n"
                f"Try another candidate from the table."
            )

    def _on_recovery_failure(self, error: Exception) -> None:
        """Handle key recovery failure."""
        log.error(f"Key recovery failed: {error}")
        self._update_status(f"Error: {error}")
        self._update_result_section(f"[red]Error: {error}[/]")

    def _restore_keys(self) -> None:
        """Restore the last successfully tested keys to the database."""
        if not self.last_successful_test:
            self._update_status("No successful test to restore")
            return

        try:
            result = self.last_successful_test
            candidate = result["candidate"]
            uid = result["uid"]

            # Determine status based on key completeness
            app_is_zero = candidate["app_read_key"] == "00000000000000000000000000000000"
            sdm_is_zero = candidate["sdm_file_read_key"] == "00000000000000000000000000000000"

            if app_is_zero and sdm_is_zero:
                status = "picc_only"
                notes = f"PICC only from {candidate['source_file']} at {datetime.now().isoformat()}"
            elif app_is_zero or sdm_is_zero:
                status = "partial_keys"
                notes = f"Partial keys from {candidate['source_file']} at {datetime.now().isoformat()}"
            else:
                status = "provisioned"
                notes = f"Recovered from {candidate['source_file']} at {datetime.now().isoformat()}"

            recovered_keys = TagKeys(
                uid=uid,
                picc_master_key=candidate["picc_master_key"],
                app_read_key=candidate["app_read_key"],
                sdm_mac_key=candidate["sdm_file_read_key"],
                provisioned_date=candidate.get("provisioned_date") or datetime.now().isoformat(),
                status=status,
                notes=notes,
            )

            self.key_manager.save_tag_keys(recovered_keys)
            log.info("✓ Keys saved to database")

            # Update widgets
            self.query_one("#tag_status", TagStatusWidget).update_from_database(self.key_manager, uid)
            self._update_keys_detail(uid)

            # Disable restore button
            self.query_one("#btn_restore", Button).disabled = True

            self._update_status(f"✓ Keys saved for {uid[:8]}...")
            self._update_result_section(
                f"[green bold]✓ Keys restored to database[/]\n"
                f"Status: {status}\n"
                f"UID: {uid}"
            )

        except Exception as e:
            log.error(f"Failed to restore keys: {e}")
            self._update_status(f"Error: {e}")

    def _set_to_factory(self) -> None:
        """Set all keys to factory defaults (all zeros) in the database."""
        if not self.scanned_uid:
            self._update_status("Please scan a tag first")
            return

        try:
            uid = self.scanned_uid
            factory_key = "00000000000000000000000000000000"

            factory_keys = TagKeys(
                uid=uid,
                picc_master_key=factory_key,
                app_read_key=factory_key,
                sdm_mac_key=factory_key,
                provisioned_date=datetime.now().isoformat(),
                status="factory",
                notes=f"Set to factory defaults at {datetime.now().isoformat()}",
            )

            self.key_manager.save_tag_keys(factory_keys)
            log.info(f"✓ Set {uid} to factory keys in database")

            # Update widgets
            self.query_one("#tag_status", TagStatusWidget).update_from_database(self.key_manager, uid)
            self._update_keys_detail(uid)

            self._update_status(f"✓ Set to factory for {uid[:8]}...")
            self._update_result_section(
                f"[yellow]Keys set to factory defaults[/]\n"
                f"All keys are now 00000000...\n"
                f"UID: {uid}"
            )

        except Exception as e:
            log.error(f"Failed to set factory keys: {e}")
            self._update_status(f"Error: {e}")
