import logging

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, RichLog
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
from ntag424_sdm_provisioner.tui.widgets import TagStatusWidget
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


log = logging.getLogger(__name__)


class DiagnosticsAdapter:
    """Adapts TagDiagnosticsService to WorkerManager protocol."""

    def __init__(
        self,
        key_manager: CsvKeyManager,
        sequence_logger: SequenceLogger,
        tag_status_widget=None,
    ):
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.tag_status_widget = tag_status_widget
        self.operation_name = "Check Tag Status"

    @property
    def timeout_seconds(self) -> int:
        return 15

    def execute(self):
        """Execute diagnostics via service."""
        from ntag424_sdm_provisioner.services.tag_status_service import TagStatusService

        with CardManager(self.sequence_logger) as card:
            # Read tag status
            status_service = TagStatusService(card, self.key_manager)
            tag_status = status_service.read_tag_status()

            # Update widget if provided
            if self.tag_status_widget:
                def update_widget():
                    status_service.update_widget(self.tag_status_widget, tag_status)

                # Schedule widget update in main thread
                if hasattr(self.tag_status_widget.app, 'call_from_thread'):
                    self.tag_status_widget.app.call_from_thread(update_widget)

            # Determine display status
            registered = tag_status.db_keys is not None
            if registered:
                db_status = tag_status.db_keys.status
                if db_status == "provisioned":
                    status = "Provisioned (Registered)"
                elif db_status == "failed":
                    status = "Failed (Registered)"
                else:
                    status = f"{db_status.title() if db_status else ''} (Registered)"
                provisioned_date = tag_status.db_keys.provisioned_date
                asset_tag = tag_status.db_keys.get_asset_tag()
            else:
                status = "Factory (Not Registered)"
                db_status = None
                provisioned_date = None
                asset_tag = None

            return {
                "uid": tag_status.uid,
                "status": status,
                "registered": registered,
                "db_status": db_status,
                "provisioned_date": provisioned_date,
                "asset_tag": asset_tag,
                "hw_version": f"{tag_status.hw_major_version}.{tag_status.hw_minor_version}",
            }


class TagStatusScreen(Screen):
    """Screen for checking tag status (Factory vs Provisioned)."""

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Check Tag Status", id="title"),
            TagStatusWidget(id="tag_status"),
            Label("Ready to scan...", id="status_label"),
            Label("", id="status_timer"),
            Label("", id="error_label"),
            Label("", id="result_label"),  # For the big status result
            Button("Check Status", id="btn_scan", variant="primary"),
            RichLog(highlight=True, markup=True, id="log_view"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Tag Status"
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

    def scan_tag(self) -> None:
        self.query_one("#btn_scan").disabled = True
        self.query_one("#status_label").update("Scanning...")  # type: ignore[attr-defined]
        self.query_one("#result_label").update("")  # type: ignore[attr-defined]

        # Clear previous error
        error_label = self.query_one("#error_label")
        error_label.update("")  # type: ignore[attr-defined]
        error_label.remove_class("visible")

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
        seq = create_sequence_logger("TagStatus")
        seq.on_step_complete = on_step
        self._sequence_logger = seq

        # Use DiagnosticsAdapter with injected dependencies
        tag_status_widget = self.query_one("#tag_status", TagStatusWidget)
        cmd = DiagnosticsAdapter(
            key_manager=self.key_manager,
            sequence_logger=seq,
            tag_status_widget=tag_status_widget,
        )
        self._worker_mgr.execute_command(
            cmd, _status_label_id="status_label", timer_label_id="status_timer"  # type: ignore[arg-type]
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        self._worker_mgr.cleanup()

        try:
            self.query_one("#status_timer").update("")  # type: ignore[attr-defined]

            if event.state == WorkerState.SUCCESS:
                result = event.worker.result
                status = result.get("status", "Unknown")  # type: ignore[union-attr]
                uid = result.get("uid", "Unknown")  # type: ignore[union-attr]
                asset_tag = result.get("asset_tag", "")  # type: ignore[union-attr]
                registered = result.get("registered", False)  # type: ignore[union-attr]
                provisioned_date = result.get("provisioned_date", "")  # type: ignore[union-attr]

                # Build display info
                info_parts = [f"UID: {uid}"]
                if asset_tag:
                    info_parts.append(f"Tag: {asset_tag}")
                if registered and provisioned_date:
                    info_parts.append(f"Date: {provisioned_date[:10]}")

                self.query_one("#status_label").update(" | ".join(info_parts))  # type: ignore[attr-defined]
                self.query_one("#result_label").update(f"STATUS: {status}")  # type: ignore[attr-defined]
                self.query_one("#btn_scan").disabled = False

                # Show sequence summary
                if hasattr(self, "_sequence_logger") and self._sequence_logger:
                    seq = self._sequence_logger
                    log_view = self.query_one("#log_view", RichLog)
                    success_count = sum(1 for s in seq.steps if s.result.value == "success")
                    log_view.write(
                        f"[bold cyan]━━━ {len(seq.steps)} commands | ✓ {success_count} success ━━━[/]"
                    )

                log.info(f"Tag status: {status} (Registered: {registered})")

            elif event.state == WorkerState.ERROR:
                # Extract error details from worker
                error = event.worker.error
                error_type = type(error).__name__ if error else "Unknown"
                error_msg = str(error) if error else "Unknown error"

                # Show error banner with details
                error_label = self.query_one("#error_label")
                error_label.update(f"✗ {error_type}: {error_msg}")  # type: ignore[attr-defined]
                error_label.add_class("visible")

                self.query_one("#status_label").update("Scan Failed")  # type: ignore[attr-defined]
                self.query_one("#result_label").update("")  # type: ignore[attr-defined]
                self.query_one("#btn_scan").disabled = False
                log.error(f"Worker failed: {error_type}: {error_msg}")
        except Exception:
            pass
