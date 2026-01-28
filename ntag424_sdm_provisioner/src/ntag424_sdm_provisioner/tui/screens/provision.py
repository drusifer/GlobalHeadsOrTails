import logging

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RichLog
from textual.worker import Worker, WorkerState

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, Outcome, generate_coin_name
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.sequence_logger import (
    SequenceLogger,
    create_sequence_logger,
    format_step_line,
)
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
from ntag424_sdm_provisioner.tui.logging_handler import TextualLogHandler
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


class ServiceAdapter:
    """Adapts ProvisioningService to WorkerManager protocol."""

    def __init__(
        self,
        base_url: str,
        key_manager: CsvKeyManager,
        sequence_logger: SequenceLogger,
        coin_name: str = "",
        outcome: Outcome = Outcome.HEADS,
        progress_callback=None,
    ):
        self.base_url = base_url
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.coin_name = coin_name
        self.outcome = outcome
        self.progress_callback = progress_callback
        self.operation_name = "Provision Tag"

    @property
    def timeout_seconds(self) -> int:
        return 30

    def execute(self):
        """Execute provisioning via service."""
        # Pass sequence logger to CardManager (explicit DI)
        with CardManager(sequence_logger=self.sequence_logger) as card:
            service = ProvisioningService(card, self.key_manager, self.progress_callback)
            success = service.provision(self.base_url, self.coin_name, self.outcome)

            if not success:
                raise Exception("Provisioning failed (check logs)")
            return success


class ProvisionScreen(Screen):
    """Screen for provisioning a tag with coin name and outcome selection."""

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager
        self.selected_outcome = Outcome.HEADS  # Default to HEADS

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Provision Tag", id="title"),
            Label("Coin Name:", id="coin_name_label"),
            Input(
                value=generate_coin_name(),
                placeholder="SWIFT-FALCON-42",
                id="coin_name_input",
            ),
            Label("Outcome:", id="outcome_label"),
            Horizontal(
                Button("◉ Heads", id="btn_heads", variant="primary"),
                Button("○ Tails", id="btn_tails"),
                id="outcome_buttons",
            ),
            Label("Ready to provision...", id="status_label"),
            Label("", id="status_timer"),
            Label("", id="error_label"),
            Label("", id="success_label"),
            Button("Start Provisioning", id="btn_start", variant="success"),
            RichLog(highlight=True, markup=True, id="log_view"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Provision Tag"
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
            self.start_provisioning()
        elif event.button.id == "btn_heads":
            self.select_outcome(Outcome.HEADS)
        elif event.button.id == "btn_tails":
            self.select_outcome(Outcome.TAILS)

    def select_outcome(self, outcome: Outcome) -> None:
        """Update outcome selection and button states."""
        self.selected_outcome = outcome

        btn_heads = self.query_one("#btn_heads", Button)
        btn_tails = self.query_one("#btn_tails", Button)

        if outcome == Outcome.HEADS:
            btn_heads.label = "◉ Heads"
            btn_heads.variant = "primary"
            btn_tails.label = "○ Tails"
            btn_tails.variant = "default"
        else:
            btn_heads.label = "○ Heads"
            btn_heads.variant = "default"
            btn_tails.label = "◉ Tails"
            btn_tails.variant = "primary"

    def start_provisioning(self) -> None:
        self.query_one("#btn_start", Button).disabled = True
        self.query_one("#status_label", Label).update("Starting provisioning task...")

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
        seq = create_sequence_logger("Provisioning")
        seq.on_step_complete = on_step
        self._sequence_logger = seq  # Store for summary display

        # Get coin name and outcome from UI
        coin_name = self.query_one("#coin_name_input", Input).value.strip()
        if not coin_name:
            coin_name = generate_coin_name()  # Fallback to generated name if empty

        # Create adapter with injected dependencies (including coin info)
        cmd = ServiceAdapter(
            base_url="https://example.com/verify",
            key_manager=self.key_manager,
            sequence_logger=seq,
            coin_name=coin_name,
            outcome=self.selected_outcome,
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
            self.query_one("#status_timer", Label).update("")

            if event.state == WorkerState.SUCCESS:
                # Coin name was assigned atomically during provisioning
                coin_name = self.query_one("#coin_name_input", Input).value.strip() or "auto-generated"

                self.query_one("#status_label", Label).update("Provisioning Complete!")
                # Show success banner with coin info
                success_label = self.query_one("#success_label", Label)
                success_label.update(
                    f"✓ Provisioning Successful! Coin: {coin_name} ({self.selected_outcome.value})"
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

                self.query_one("#status_label", Label).update("Provisioning Failed")
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
