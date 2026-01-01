import logging

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, RichLog, Static
from textual.worker import Worker, WorkerState

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.sequence_logger import (
    SequenceLogger,
    create_sequence_logger,
    format_step_line,
)
from ntag424_sdm_provisioner.services.diagnostics_service import TagDiagnosticsService
from ntag424_sdm_provisioner.tui.logging_handler import TextualLogHandler
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


log = logging.getLogger(__name__)


class FullDiagnosticsAdapter:
    """Adapts TagDiagnosticsService.get_full_diagnostics to WorkerManager protocol."""

    def __init__(self, key_manager: CsvKeyManager, sequence_logger: SequenceLogger):
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.operation_name = "Read Tag Info"

    @property
    def timeout_seconds(self) -> int:
        return 20

    def execute(self):
        """Execute full diagnostics via service."""
        with CardManager(self.sequence_logger) as card:
            service = TagDiagnosticsService(card, self.key_manager)
            return service.get_full_diagnostics()


class ReadTagScreen(Screen):
    """Screen for reading tag details."""

    CSS = """
    .tile {
        border: solid $accent;
        padding: 1;
        margin: 1;
        height: auto;
        min-height: 8;
        background: $surface;
    }

    #dashboard_row1, #dashboard_row2, #dashboard_row3 {
        height: auto;
        margin-bottom: 1;
    }

    #url_tile {
        width: 100%;
    }

    #log_view {
        height: 15;
        border: solid $primary;
        margin-top: 1;
    }
    """

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Read Tag Info", id="title"),
            Label("Ready to scan...", id="status_label"),
            Label("", id="status_timer"),  # Timer label
            Label("", id="error_label"),
            Label("", id="success_label"),
            Button("Scan Tag", id="btn_scan", variant="primary"),
            # Dashboard tiles for chip data
            Horizontal(
                Static("", id="chip_tile", classes="tile"),
                Static("", id="database_tile", classes="tile"),
                Static("", id="keys_tile", classes="tile"),
                id="dashboard_row1",
            ),
            Horizontal(
                Static("", id="files_tile", classes="tile"),
                Static("", id="ndef_tile", classes="tile"),
                Static("", id="extra_tile", classes="tile"),
                id="dashboard_row2",
            ),
            # Row 3: Full-width URL validation tile
            Horizontal(
                Static("", id="url_tile", classes="tile"),
                id="dashboard_row3",
            ),
            RichLog(highlight=True, markup=True, id="log_view"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Read Tag"
        # Setup logging
        log_view = self.query_one(RichLog)
        handler = TextualLogHandler(log_view)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s"
        )
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        self._log_handler = handler

        # Initialize WorkerManager
        self._worker_mgr = WorkerManager(self)

    def on_unmount(self) -> None:
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_scan":
            self.scan_tag()
        elif event.button.id == "btn_back":
            self.app.pop_screen()

    def _update_dashboard_tiles(self, diagnostics: dict) -> None:
        """Update dashboard tiles with diagnostics data."""
        # Chip Info Tile
        chip_info = diagnostics.get("chip", {})
        chip_content = "[bold cyan]CHIP INFO[/]\n"
        if isinstance(chip_info, dict) and "uid" in chip_info:
            chip_content += f"UID: [green]{chip_info.get('uid', 'N/A')}[/]\n"
            chip_content += f"HW: {chip_info.get('hw_version', 'N/A')}\n"
            chip_content += f"SW: {chip_info.get('sw_version', 'N/A')}\n"
            chip_content += f"Storage: {chip_info.get('hw_storage', 'N/A')} bytes\n"
            chip_content += f"Batch: {chip_info.get('batch', 'N/A')}\n"
            chip_content += f"Fab: {chip_info.get('fab_date', 'N/A')}"
        else:
            chip_content += f"[red]Error: {chip_info}[/]"
        self.query_one("#chip_tile", Static).update(chip_content)

        # Database Status Tile
        db_status = diagnostics.get("database_status", {})
        db_content = "[bold cyan]DATABASE[/]\n"
        if isinstance(db_status, dict):
            in_db = db_status.get("in_database", False)
            if in_db:
                db_content += f"Status: [green]{db_status.get('status', 'N/A')}[/]\n"
                db_content += f"Date: {db_status.get('provisioned_date', 'N/A')[:10]}\n"
                notes = db_status.get('notes', 'None')
                if notes and notes != 'None':
                    db_content += f"Notes: {notes[:30]}..."
            else:
                db_content += "[yellow]Not in database[/]"
        else:
            db_content += f"[red]{db_status}[/]"
        self.query_one("#database_tile", Static).update(db_content)

        # Key Versions Tile
        key_versions = diagnostics.get("key_versions_unauth", {})
        keys_content = "[bold cyan]KEY VERSIONS[/]\n"
        if isinstance(key_versions, dict):
            for i in range(5):
                key_name = f"key_{i}"
                version = key_versions.get(key_name, "N/A")
                keys_content += f"Key {i}: {version}\n"
        else:
            keys_content += f"[red]{key_versions}[/]"
        self.query_one("#keys_tile", Static).update(keys_content)

        # File Settings Tile
        file_settings = diagnostics.get("file_settings_unauth", "N/A")
        files_content = "[bold cyan]FILE SETTINGS[/]\n"
        if isinstance(file_settings, str):
            # file_settings is a string representation
            files_content += f"{file_settings}"
        elif isinstance(file_settings, dict):
            for file_id, settings in file_settings.items():
                files_content += f"{file_id}: {settings}\n"
        else:
            files_content += "N/A"
        self.query_one("#files_tile", Static).update(files_content)

        # NDEF Tile
        ndef_info = diagnostics.get("ndef", {})
        cc_info = diagnostics.get("cc_file", {})
        ndef_content = "[bold cyan]NDEF DATA[/]\n"
        if isinstance(ndef_info, dict) and "length" in ndef_info:
            length = ndef_info.get("length", 0)
            preview = ndef_info.get("preview", "")
            ndef_content += f"Length: {length} bytes\n"
            ndef_content += f"Preview: {preview[:40]}...\n"
        else:
            ndef_content += f"[red]{ndef_info}[/]\n"

        if isinstance(cc_info, dict) and "version" in cc_info:
            ndef_content += f"CC Ver: {cc_info.get('version', 'N/A')}\n"
            ndef_content += f"Max: {cc_info.get('max_size', 'N/A')} bytes"
        self.query_one("#ndef_tile", Static).update(ndef_content)

        # SDM Validation Tile (Phone Tap Simulation)
        sdm_validation = diagnostics.get("sdm_validation", {})
        import logging
        log = logging.getLogger(__name__)
        log.debug(f"[Dashboard] sdm_validation type: {type(sdm_validation)}, keys: {sdm_validation.keys() if isinstance(sdm_validation, dict) else 'N/A'}")
        log.debug(f"[Dashboard] sdm_validation content: {sdm_validation}")

        sdm_content = "[bold cyan]PHONE TAP TEST[/]\n"

        if isinstance(sdm_validation, dict):
            # Always show URL first if available - make it PROMINENT
            url = sdm_validation.get("url", "")
            log.debug(f"[Dashboard] URL from sdm_validation: '{url}' (type: {type(url)})")

            if url:
                # Show the SDM parameters part prominently (last ~80 chars)
                url_display = "..." + url[-77:] if len(url) > 80 else url
                sdm_content += f"[cyan]{url_display}[/]\n\n"
                log.info(f"[Dashboard] Added URL to display: {url_display}")
            else:
                log.warning("[Dashboard] URL is empty or None!")

            # Check for errors first
            if sdm_validation.get("error"):
                sdm_content += f"[red]{sdm_validation['error'][:50]}[/]"
            elif not sdm_validation.get("has_url"):
                sdm_content += "[yellow]No URL on tag[/]"
            elif not sdm_validation.get("has_sdm"):
                sdm_content += "[yellow]No SDM parameters[/]"
            else:
                # We have SDM - show validation result
                validation = sdm_validation.get("validation", {})
                if validation.get("valid"):
                    sdm_content += "[green bold]✓ VALID SDM[/]\n"
                    sdm_content += f"Counter: {validation.get('counter', 'N/A')}\n"
                    sdm_content += "CMAC: [green]Match[/]"
                elif validation.get("error"):
                    if "placeholders" in validation.get("error", "").lower():
                        sdm_content += "[yellow]Placeholders[/]\n"
                        sdm_content += "[dim]Not yet tapped[/]"
                    else:
                        sdm_content += "[red bold]✗ INVALID[/]\n"
                        error_msg = validation.get("error", "Unknown")
                        sdm_content += f"[red]{error_msg[:35]}[/]"
                else:
                    sdm_content += "[red bold]✗ INVALID[/]\n"
                    sdm_content += "[red]CMAC mismatch[/]"
        else:
            sdm_content += "[dim]No validation data[/]"

        log.debug(f"[Dashboard] Final sdm_content: {sdm_content}")
        self.query_one("#extra_tile", Static).update(sdm_content)

        # New dedicated URL validation tile with full details
        url_content = "[bold cyan]SDM URL VALIDATION & ANDROID NFC CHECKS[/]\n"

        if isinstance(sdm_validation, dict) and sdm_validation.get("has_url"):
            url = sdm_validation.get("url", "")
            validation = sdm_validation.get("validation", {})

            # Show base URL
            if url:
                # Extract base URL (everything before '?')
                base_url = url.split("?")[0] if "?" in url else url
                url_content += f"[dim]Base:[/] {base_url}\n\n"

            # Show SDM parameters
            if validation:
                uid = validation.get("uid", "N/A")
                counter = validation.get("counter", "N/A")
                cmac_received = validation.get("cmac_received", "N/A")
                cmac_calculated = validation.get("cmac_calculated", "N/A")

                url_content += f"[yellow]UID:[/] {uid}  "
                url_content += f"[yellow]Counter:[/] {counter}  "
                url_content += f"[yellow]CMAC:[/] {cmac_received}\n"

                # Validation status
                if validation.get("valid"):
                    url_content += "[green bold]✓ VALID - CMAC matches[/]"
                    # Show warning if using factory default key
                    if validation.get("warning"):
                        url_content += f"\n[yellow]{validation['warning']}[/]"
                else:
                    url_content += "[red bold]✗ INVALID - CMAC mismatch[/]\n"
                    url_content += f"[dim]Expected:[/] {cmac_calculated}"
            else:
                url_content += "[yellow]No validation performed[/]"

            # === ANDROID NFC DETECTION CHECKS ===
            android_checks = sdm_validation.get("android_nfc_checks", {})
            if isinstance(android_checks, dict):
                url_content += "\n\n[bold yellow]Android NFC Detection:[/]\n"

                all_pass = android_checks.get("all_conditions_pass", False)
                if all_pass:
                    url_content += "[green bold]✓ ALL CHECKS PASS - Android will detect and launch URL[/]\n"
                else:
                    url_content += "[yellow]⚠ Some checks failed - Android may not detect tag[/]\n"

                # Show individual condition status
                c1 = android_checks.get("condition_1_read_access_free", False)
                c2 = android_checks.get("condition_2_ndef_format", False)
                c3 = android_checks.get("condition_3_cc_file_valid", False)
                c4 = android_checks.get("condition_4_offsets_valid", False)

                url_content += f"  1. Read Access FREE: {'[green]✓[/]' if c1 else '[red]✗[/]'}\n"
                url_content += f"  2. NDEF Format: {'[green]✓[/]' if c2 else '[red]✗[/]'}\n"
                url_content += f"  3. CC File Valid: {'[green]✓[/]' if c3 else '[red]✗[/]'}\n"
                url_content += f"  4. Offsets Valid: {'[green]✓[/]' if c4 else '[red]✗[/]'}"
        else:
            url_content += "[dim]No URL on tag[/]"

        self.query_one("#url_tile", Static).update(url_content)

    def scan_tag(self) -> None:
        self.query_one("#btn_scan").disabled = True
        self.query_one("#status_label").update("Scanning...")  # type: ignore[attr-defined]

        # Clear previous error/success
        error_label = self.query_one("#error_label")
        error_label.update("")  # type: ignore[attr-defined]
        error_label.remove_class("visible")
        success_label = self.query_one("#success_label")
        success_label.update("")  # type: ignore[attr-defined]
        success_label.remove_class("visible")

        # Setup live sequence logging
        log_view = self.query_one("#log_view", RichLog)
        log_view.write("[bold cyan]━━━ SEQUENCE ━━━[/]")
        log_view.write("[dim]  Host                              Tag[/]")

        # Track step count for numbering
        self._step_count = 0

        def on_step(step):
            """Callback for live sequence updates."""
            self._step_count += 1
            line = format_step_line(step, self._step_count)
            if step.result.value == "error":
                log_view.write(f"[red]{line}[/]")
            else:
                log_view.write(f"[green]{line}[/]")

        # Create sequence logger with callback (explicit DI)
        seq = create_sequence_logger("ReadTag")
        seq.on_step_complete = on_step
        self._sequence_logger = seq

        # Use FullDiagnosticsAdapter with injected dependencies
        cmd = FullDiagnosticsAdapter(key_manager=self.key_manager, sequence_logger=seq)
        self._worker_mgr.execute_command(
            cmd, _status_label_id="status_label", timer_label_id="status_timer"  # type: ignore[arg-type]
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        # Cleanup managed resources
        self._worker_mgr.cleanup()

        try:
            self.query_one("#status_timer").update("")  # type: ignore[attr-defined]

            if event.state == WorkerState.SUCCESS:
                self.query_one("#status_label").update("Read Complete!")  # type: ignore[attr-defined]
                # Show success banner
                success_label = self.query_one("#success_label")
                success_label.update("✓ Tag Read Successfully!")  # type: ignore[attr-defined]
                success_label.add_class("visible")
                self.query_one("#btn_scan").disabled = False

                # Get diagnostics result
                result = event.worker.result

                # Update dashboard tiles with diagnostics data
                self._update_dashboard_tiles(result)  # type: ignore[arg-type]

                # Show sequence summary
                if hasattr(self, "_sequence_logger") and self._sequence_logger:
                    seq = self._sequence_logger
                    log_view = self.query_one("#log_view", RichLog)
                    success_count = sum(1 for s in seq.steps if s.result.value == "success")
                    log_view.write(
                        f"[bold cyan]━━━ {len(seq.steps)} commands | ✓ {success_count} success ━━━[/]"
                    )
            elif event.state == WorkerState.ERROR:
                # Extract error details from worker
                error = event.worker.error
                error_type = type(error).__name__ if error else "Unknown"
                error_msg = str(error) if error else "Unknown error"

                # Show error banner with details
                error_label = self.query_one("#error_label")
                error_label.update(f"✗ {error_type}: {error_msg}")  # type: ignore[attr-defined]
                error_label.add_class("visible")

                self.query_one("#status_label").update("Read Failed")  # type: ignore[attr-defined]
                self.query_one("#btn_scan").disabled = False
                log.error(f"Worker failed: {error_type}: {error_msg}")
        except Exception:
            pass
