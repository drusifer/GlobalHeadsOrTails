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
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
from ntag424_sdm_provisioner.tui.logging_handler import TextualLogHandler
from ntag424_sdm_provisioner.tui.widgets import TagStatusWidget
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


class ConfigureKeysAdapter:
    """Adapts ProvisioningService.provision_keys() to WorkerManager protocol."""

    def __init__(
        self,
        key_manager: CsvKeyManager,
        sequence_logger: SequenceLogger,
        progress_callback=None,
        tag_status_widget=None,
    ):
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.progress_callback = progress_callback
        self.tag_status_widget = tag_status_widget
        self.operation_name = "Configure Keys"

    @property
    def timeout_seconds(self) -> int:
        return 30

    def execute(self):
        """Execute key configuration via service."""
        from ntag424_sdm_provisioner.services.tag_status_service import TagStatusService

        # Pass sequence logger to CardManager (explicit DI)
        with CardManager(sequence_logger=self.sequence_logger) as card:
            # Read tag info before provisioning
            if self.tag_status_widget:
                status_service = TagStatusService(card, self.key_manager)
                tag_status = status_service.read_tag_status()

                # Update widget in main thread
                def update_widget():
                    status_service.update_widget(self.tag_status_widget, tag_status)

                # Schedule widget update in main thread
                if hasattr(self.tag_status_widget.app, 'call_from_thread'):
                    self.tag_status_widget.app.call_from_thread(update_widget)

            service = ProvisioningService(card, self.key_manager, self.progress_callback)
            success = service.provision_keys()

            if not success:
                raise Exception("Key configuration failed (check logs)")
            return success


class ConfigureKeysScreen(Screen):
    """Screen for configuring cryptographic keys on tag (Phase 1)."""

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Configure Keys (Phase 1)", id="title"),
            Label(
                "This will set cryptographic keys on the tag.\nSDM/URL configuration happens in Phase 2 (Setup URL).",
                id="info",
            ),
            TagStatusWidget(id="tag_status"),
            Label("Ready to configure keys...", id="status_label"),
            Label("", id="status_timer"),
            Label("", id="error_label"),
            Label("", id="success_label"),
            Button("Start Key Configuration", id="btn_start", variant="primary"),
            RichLog(highlight=True, markup=True, id="log_view"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Configure Keys (Phase 1)"
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
        if hasattr(self, "_log_handler"):
            logging.getLogger().removeHandler(self._log_handler)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_start":
            self.start_key_configuration()

    def start_key_configuration(self) -> None:
        self.query_one("#btn_start", Button).disabled = True
        self.query_one("#status_label", Label).update("Starting key configuration...")

        # Clear previous error/success messages
        error_label = self.query_one("#error_label", Label)
        error_label.update("")
        error_label.remove_class("visible")
        success_label = self.query_one("#success_label", Label)
        success_label.update("")
        success_label.remove_class("visible")

        # Setup live sequence logging (explicit DI - no singletons)
        log_view = self.query_one("#log_view", RichLog)
        log_view.write("[bold cyan]━━━ SEQUENCE ━━━[/]")
        log_view.write("[dim]  Host                              Tag[/]")

        # Track step count for numbering
        self._step_count = 0

        def on_step(step):
            """Callback for live sequence updates."""
            self._step_count += 1
            line = format_step_line(step, self._step_count)
            # Color based on result
            if step.result.value == "error":
                log_view.write(f"[red]{line}[/]")
            else:
                log_view.write(f"[green]{line}[/]")

        # Create sequence logger with callback (explicit DI)
        seq = create_sequence_logger("Configure Keys")
        seq.on_step_complete = on_step
        self._sequence_logger = seq  # Store for summary display

        # Create adapter with injected dependencies (no optionals)
        tag_status_widget = self.query_one("#tag_status", TagStatusWidget)
        cmd = ConfigureKeysAdapter(
            key_manager=self.key_manager,
            sequence_logger=seq,
            progress_callback=self._log_handler.emit_message
            if hasattr(self, "_log_handler")
            else None,
            tag_status_widget=tag_status_widget,
        )

        self._worker_mgr.execute_command(
            cmd, _status_label_id="status_label", timer_label_id="status_timer"  # type: ignore[arg-type]
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        # Cleanup managed resources
        self._worker_mgr.cleanup()

        try:
            self.query_one("#status_timer", Label).update("")

            if event.state == WorkerState.SUCCESS:
                self.query_one("#status_label", Label).update("Keys Configured!")
                # Show success banner with next step guidance
                success_label = self.query_one("#success_label", Label)
                success_label.update(
                    "✓ Keys Configured Successfully! Next: Use 'Setup URL' to complete provisioning"
                )
                success_label.add_class("visible")
                self.query_one("#btn_start", Button).disabled = False
                log = logging.getLogger(__name__)
                log.info("Worker finished successfully.")

                # Show summary (steps already displayed live)
                if hasattr(self, "_sequence_logger") and self._sequence_logger:
                    seq = self._sequence_logger
                    log_view = self.query_one("#log_view", RichLog)
                    success_count = sum(1 for s in seq.steps if s.result.value == "success")
                    log_view.write(
                        f"[bold cyan]━━━ {len(seq.steps)} commands | ✓ {success_count} success ━━━[/]"
                    )
                    log_view.write("[bold green]Tag Status: keys_configured[/]")
                    # Write full sequence diagram to log file
                    seq.log_to_file()

            elif event.state == WorkerState.ERROR:
                # Extract error details from worker
                error = event.worker.error
                error_type = type(error).__name__ if error else "Unknown"
                error_msg = str(error) if error else "Unknown error"

                # Show error banner with details
                error_label = self.query_one("#error_label", Label)
                error_label.update(f"✗ {error_type}: {error_msg}")
                error_label.add_class("visible")

                self.query_one("#status_label", Label).update("Key Configuration Failed")
                self.query_one("#btn_start", Button).disabled = False
                log = logging.getLogger(__name__)
                log.error(f"Worker failed: {error_type}: {error_msg}")

                # Show error summary (steps already displayed live)
                if hasattr(self, "_sequence_logger") and self._sequence_logger:
                    log_view = self.query_one("#log_view", RichLog)
                    error_summary = self._sequence_logger.get_error_summary()
                    if error_summary:
                        log_view.write(f"[bold red]━━━ FAILED: {error_summary} ━━━[/]")
                    # Write full sequence diagram to log file for debugging
                    self._sequence_logger.log_to_file()
        except Exception:
            pass
