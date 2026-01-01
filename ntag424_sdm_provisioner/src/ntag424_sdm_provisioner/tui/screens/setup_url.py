import logging

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog
from textual.worker import Worker, WorkerState

from ntag424_sdm_provisioner.constants import GAME_COIN_BASE_URL
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.sequence_logger import (
    SequenceLogger,
    create_sequence_logger,
    format_step_line,
)
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
from ntag424_sdm_provisioner.tui.logging_handler import TextualLogHandler
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


log = logging.getLogger(__name__)


class SetupUrlAdapter:
    """Adapts ProvisioningService.provision_url() to WorkerManager protocol."""

    def __init__(
        self,
        base_url: str,
        key_manager: CsvKeyManager,
        sequence_logger: SequenceLogger,
        progress_callback=None,
    ):
        self.base_url = base_url
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.progress_callback = progress_callback
        self.operation_name = "Setup URL"

    @property
    def timeout_seconds(self) -> int:
        return 20

    def execute(self):
        """Execute URL setup via service."""
        # Pass sequence logger to CardManager (explicit DI)
        with CardManager(sequence_logger=self.sequence_logger) as card:
            service = ProvisioningService(card, self.key_manager, self.progress_callback)
            success = service.provision_url(self.base_url)

            if not success:
                raise Exception("URL setup failed (check logs)")
            return success


class SetupUrlScreen(Screen):
    """Screen for configuring SDM and NDEF URL (Phase 2)."""

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Setup URL (Phase 2)", id="title"),
            Label(
                "Configure SDM and NDEF URL.\nTag must have keys configured (Phase 1) first.",
                id="info",
            ),
            Label("Base URL:", id="url_label"),
            Input(
                value=GAME_COIN_BASE_URL, placeholder="https://example.com/verify", id="url_input"
            ),
            Label("Ready to setup URL...", id="status_label"),
            Label("", id="status_timer"),
            Label("", id="error_label"),
            Label("", id="success_label"),
            Button("Setup URL", id="btn_start", variant="primary"),
            RichLog(highlight=True, markup=True, id="log_view"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Setup URL (Phase 2)"
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
            self.start_url_setup()

    def start_url_setup(self) -> None:
        # Get URL from input
        url_input = self.query_one("#url_input", Input)
        base_url = url_input.value.strip()

        # Basic validation
        if not base_url:
            error_label = self.query_one("#error_label")
            error_label.update("✗ URL cannot be empty")  # type: ignore[attr-defined]
            error_label.add_class("visible")
            return

        if not base_url.startswith(("http://", "https://")):
            error_label = self.query_one("#error_label")
            error_label.update("✗ URL must start with http:// or https://")  # type: ignore[attr-defined]
            error_label.add_class("visible")
            return

        self.query_one("#btn_start").disabled = True
        self.query_one("#status_label").update("Starting URL setup...")  # type: ignore[attr-defined]

        # Clear previous error/success messages
        error_label = self.query_one("#error_label")
        error_label.update("")  # type: ignore[attr-defined]
        error_label.remove_class("visible")
        success_label = self.query_one("#success_label")
        success_label.update("")  # type: ignore[attr-defined]
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
        seq = create_sequence_logger("Setup URL")
        seq.on_step_complete = on_step
        self._sequence_logger = seq  # Store for summary display

        # Create adapter with injected dependencies (no optionals)
        cmd = SetupUrlAdapter(
            base_url=base_url,
            key_manager=self.key_manager,
            sequence_logger=seq,
            progress_callback=self._log_handler.emit_message
            if hasattr(self, "_log_handler")
            else None,
        )

        self._worker_mgr.execute_command(
            cmd, _status_label_id="status_label", timer_label_id="status_timer"  # type: ignore[arg-type]
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        # Cleanup managed resources
        self._worker_mgr.cleanup()

        try:
            self.query_one("#status_timer").update("")  # type: ignore[attr-defined]

            if event.state == WorkerState.SUCCESS:
                self.query_one("#status_label").update("Provisioning Complete!")  # type: ignore[attr-defined]
                # Show success banner
                success_label = self.query_one("#success_label")
                success_label.update("✓ Provisioning Complete! Tag is ready for field use.")  # type: ignore[attr-defined]
                success_label.add_class("visible")
                self.query_one("#btn_start").disabled = False
                log.info("Worker finished successfully.")

                # Show summary (steps already displayed live)
                if hasattr(self, "_sequence_logger") and self._sequence_logger:
                    seq = self._sequence_logger
                    log_view = self.query_one("#log_view", RichLog)
                    success_count = sum(1 for s in seq.steps if s.result.value == "success")
                    log_view.write(
                        f"[bold cyan]━━━ {len(seq.steps)} commands | ✓ {success_count} success ━━━[/]"
                    )
                    log_view.write("[bold green]Tag Status: provisioned[/]")
                    # Write full sequence diagram to log file
                    seq.log_to_file()

            elif event.state == WorkerState.ERROR:
                # Extract error details from worker
                error = event.worker.error
                error_type = type(error).__name__ if error else "Unknown"
                error_msg = str(error) if error else "Unknown error"

                # Show error banner with details
                error_label = self.query_one("#error_label")
                error_label.update(f"✗ {error_type}: {error_msg}")  # type: ignore[attr-defined]
                error_label.add_class("visible")

                self.query_one("#status_label").update("URL Setup Failed")  # type: ignore[attr-defined]
                self.query_one("#btn_start").disabled = False
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
