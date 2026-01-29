"""Format PICC Screen - Factory reset NTAG424 DNA tags."""

import logging

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, RichLog, Static
from textual.worker import Worker, WorkerState

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger
from ntag424_sdm_provisioner.services.format_service import FormatService
from ntag424_sdm_provisioner.tui.logging_handler import TextualLogHandler
from ntag424_sdm_provisioner.tui.widgets import TagStatusWidget
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


log = logging.getLogger(__name__)


class FormatAdapter:
    """Adapts FormatService to WorkerManager protocol."""

    def __init__(
        self,
        key_manager: CsvKeyManager,
        sequence_logger: SequenceLogger,
        picc_master_key: bytes,
        progress_callback=None,
        tag_status_widget=None,
    ):
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.picc_master_key = picc_master_key
        self.progress_callback = progress_callback
        self.tag_status_widget = tag_status_widget
        self.operation_name = "Format PICC"

    @property
    def timeout_seconds(self) -> int:
        return 30

    def execute(self):
        """Execute format via service."""
        from ntag424_sdm_provisioner.services.tag_status_service import TagStatusService

        with CardManager(self.sequence_logger) as card:
            # Read tag status before format
            if self.tag_status_widget:
                status_service = TagStatusService(card, self.key_manager)
                tag_status = status_service.read_tag_status()

                # Update widget in main thread
                def update_widget():
                    status_service.update_widget(self.tag_status_widget, tag_status)

                if hasattr(self.tag_status_widget.app, "call_from_thread"):
                    self.tag_status_widget.app.call_from_thread(update_widget)

            # Format tag
            format_service = FormatService(card, self.key_manager, self.progress_callback)
            success = format_service.format_tag(self.picc_master_key)

            # Read status after format to update widget
            if self.tag_status_widget and success:
                status_service = TagStatusService(card, self.key_manager)
                tag_status = status_service.read_tag_status()

                def update_widget_after():
                    status_service.update_widget(self.tag_status_widget, tag_status)

                if hasattr(self.tag_status_widget.app, "call_from_thread"):
                    self.tag_status_widget.app.call_from_thread(update_widget_after)

            return {"success": success}


class FormatPICCScreen(Screen):
    """Screen for factory resetting tags with FormatPICC command."""

    CSS = """
    FormatPICCScreen {
        align: center middle;
    }

    #format_container {
        width: 100;
        height: auto;
        max-height: 95%;
        border: solid $error;
        padding: 1 2;
        background: $error 10%;
    }

    #format_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $error;
        padding: 1;
    }

    #warning_box {
        width: 100%;
        height: auto;
        padding: 1;
        margin-bottom: 1;
        border: double $error;
        background: $error 20%;
    }

    #key_input {
        width: 100%;
        margin-bottom: 1;
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
        grid-size: 2;
        grid-gutter: 1;
        padding: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager
        self.current_uid: str | None = None
        self.picc_master_key: bytes | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="format_container"):
            yield Label("⚠ FORMAT PICC - FACTORY RESET ⚠", id="format_title")

            # Tag status widget
            yield TagStatusWidget(id="tag_status")

            # Warning box
            with Vertical(id="warning_box"):
                yield Static(
                    "[bold red]WARNING: This operation is DESTRUCTIVE and IRREVERSIBLE![/]\n\n"
                    "FormatPICC will:\n"
                    "  ✗ Reset ALL keys to factory (0x00 * 16)\n"
                    "  ✗ Erase ALL files and data\n"
                    "  ✗ Disable SDM configuration\n"
                    "  ✗ Delete ALL content on the tag\n\n"
                    "[yellow]Requirements:[/]\n"
                    "  ✓ PICC Master Key (Key 0) only\n"
                    "  ✓ Does NOT need Keys 1 or 3\n\n"
                    "[cyan]After formatting:[/]\n"
                    "  → Tag returns to factory state\n"
                    "  → Can be provisioned fresh\n"
                    "  → All previous data is LOST"
                )

            yield Label("Status: Ready to scan...", id="status_label")
            yield Label("", id="status_timer")
            yield RichLog(highlight=True, markup=True, id="log_view")

            with Vertical(id="button_container"):
                yield Button("1. Scan Tag", id="btn_scan", variant="primary")
                yield Button(
                    "2. FORMAT TAG", id="btn_format", variant="error", disabled=True
                )
                yield Button("Back", id="btn_back", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Format PICC"

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
        if event.button.id == "btn_back":
            self.app.pop_screen()
        elif event.button.id == "btn_scan":
            self._scan_tag()
        elif event.button.id == "btn_format":
            self._confirm_and_format()

    def _scan_tag(self) -> None:
        """Scan tag and check if we have PICC Master Key in database."""
        self.query_one("#btn_scan").disabled = True
        self.query_one("#status_label").update("Scanning tag...")  # type: ignore[attr-defined]

        try:
            from ntag424_sdm_provisioner.card_factory import CardConnectionFactory
            from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
            from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
            from ntag424_sdm_provisioner.commands.select_picc_application import (
                SelectPiccApplication,
            )

            with CardConnectionFactory.create(SequenceLogger()) as conn:
                conn.send(SelectPiccApplication())
                version_info = conn.send(GetChipVersion())
                uid = version_info.uid.uid  # version_info.uid is already a UID object
                self.current_uid = uid

                # Read key versions
                key0_resp = conn.send(GetKeyVersion(key_no=0))
                key1_resp = conn.send(GetKeyVersion(key_no=1))
                key3_resp = conn.send(GetKeyVersion(key_no=3))

                # Update tag status widget
                tag_status = self.query_one("#tag_status", TagStatusWidget)
                tag_status.update_from_hardware(
                    uid=uid,
                    key0_ver=key0_resp.version,
                    key1_ver=key1_resp.version,
                    key3_ver=key3_resp.version,
                )
                tag_status.update_from_database(self.key_manager, uid)

                # Check if we have PICC Master Key in database
                try:
                    keys = self.key_manager.get_tag_keys(uid)
                    picc_key_hex = keys.picc_master_key

                    if picc_key_hex == "00000000000000000000000000000000":
                        # Factory key
                        self.picc_master_key = bytes(16)
                        self.query_one("#status_label").update(  # type: ignore[attr-defined]
                            f"Tag {uid} - Factory key detected - ready to format"
                        )
                        self.query_one("#btn_format").disabled = False
                    else:
                        # Custom key from database
                        self.picc_master_key = bytes.fromhex(picc_key_hex)
                        self.query_one("#status_label").update(  # type: ignore[attr-defined]
                            f"Tag {uid} - PICC Master Key from database - ready to format"
                        )
                        self.query_one("#btn_format").disabled = False

                except Exception:
                    # Not in database
                    self.query_one("#status_label").update(  # type: ignore[attr-defined]
                        f"Tag {uid} - NOT in database - trying factory key"
                    )
                    self.picc_master_key = bytes(16)  # Try factory
                    self.query_one("#btn_format").disabled = False

        except Exception as e:
            log.error(f"Error scanning tag: {e}")
            self.query_one("#status_label").update(f"Error scanning tag: {e}")  # type: ignore[attr-defined]
        finally:
            self.query_one("#btn_scan").disabled = False

    def _confirm_and_format(self) -> None:
        """Execute format operation."""
        if not self.current_uid or not self.picc_master_key:
            self.query_one("#status_label").update("Please scan a tag first")  # type: ignore[attr-defined]
            return

        self.query_one("#btn_format").disabled = True
        self.query_one("#btn_scan").disabled = True
        self.query_one("#status_label").update("Formatting tag...")  # type: ignore[attr-defined]

        # Create sequence logger
        seq = SequenceLogger()

        # Get tag status widget
        tag_status_widget = self.query_one("#tag_status", TagStatusWidget)

        # Execute format command
        cmd = FormatAdapter(
            key_manager=self.key_manager,
            sequence_logger=seq,
            picc_master_key=self.picc_master_key,
            progress_callback=self._log_handler.emit_message
            if hasattr(self, "_log_handler")
            else None,
            tag_status_widget=tag_status_widget,
        )
        self._worker_mgr.execute_command(
            cmd, _status_label_id="status_label", timer_label_id="status_timer"
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        self._worker_mgr.cleanup()

        try:
            if event.state == WorkerState.SUCCESS:
                result = event.worker.result
                if result and result.get("success"):  # type: ignore[union-attr]
                    self.query_one("#status_label").update("✓ Tag formatted successfully - now in factory state")  # type: ignore[attr-defined]
                else:
                    self.query_one("#status_label").update("Format completed with warnings")  # type: ignore[attr-defined]

                # Re-enable scan button
                self.query_one("#btn_scan").disabled = False
                # Keep format button disabled until next scan
                self.query_one("#btn_format").disabled = True
                self.current_uid = None
                self.picc_master_key = None

            elif event.state == WorkerState.ERROR:
                error = event.worker.error
                error_msg = str(error) if error else "Unknown error"
                self.query_one("#status_label").update(f"✗ Format failed: {error_msg}")  # type: ignore[attr-defined]
                log.error(f"Format failed: {error_msg}")

                # Re-enable buttons to allow retry
                self.query_one("#btn_scan").disabled = False
                self.query_one("#btn_format").disabled = False

        except Exception:
            pass
