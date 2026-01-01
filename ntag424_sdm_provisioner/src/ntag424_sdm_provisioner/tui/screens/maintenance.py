"""MaintenanceScreen - Factory reset and tag maintenance operations."""

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
from ntag424_sdm_provisioner.services.maintenance_service import TagMaintenanceService
from ntag424_sdm_provisioner.tui.logging_handler import TextualLogHandler
from ntag424_sdm_provisioner.tui.worker_manager import WorkerManager


log = logging.getLogger(__name__)


class MaintenanceAdapter:
    """Adapts TagMaintenanceService to WorkerManager protocol."""

    def __init__(
        self, key_manager: CsvKeyManager, sequence_logger: SequenceLogger, progress_callback=None
    ):
        self.key_manager = key_manager
        self.sequence_logger = sequence_logger
        self.progress_callback = progress_callback
        self.operation_name = "Factory Reset"

    @property
    def timeout_seconds(self) -> int:
        return 30

    def execute(self):
        """Execute factory reset via service."""
        with CardManager(self.sequence_logger) as card:
            service = TagMaintenanceService(card, self.key_manager, self.progress_callback)
            success = service.factory_reset()

            if not success:
                raise Exception("Factory reset failed (check logs)")
            return {"success": success}


class MaintenanceScreen(Screen):
    """Screen for tag maintenance operations (factory reset)."""

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager
        self._confirmed = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Factory Reset", id="title"),
            Label("⚠️ WARNING: This will ERASE all keys!", id="warning_label"),
            Label("Ready to reset...", id="status_label"),
            Label("", id="status_timer"),
            Label("", id="error_label"),
            Label("", id="result_label"),
            Button("Reset to Factory", id="btn_reset", variant="error"),
            RichLog(highlight=True, markup=True, id="log_view"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Factory Reset"
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
        if hasattr(self, "_log_handler") and self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_reset":
            if not self._confirmed:
                # First click - ask for confirmation
                self._confirmed = True
                self.query_one("#warning_label", Label).update("🔴 CLICK AGAIN TO CONFIRM RESET!")
                self.query_one("#btn_reset", Button).label = "CONFIRM RESET"
            else:
                # Second click - execute reset
                self.do_factory_reset()

    def do_factory_reset(self) -> None:
        self.query_one("#btn_reset", Button).disabled = True
        self.query_one("#status_label", Label).update("Resetting tag...")
        self.query_one("#result_label", Label).update("")
        self._confirmed = False

        # Clear previous error
        error_label = self.query_one("#error_label", Label)
        error_label.update("")
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
        seq = create_sequence_logger("FactoryReset")
        seq.on_step_complete = on_step
        self._sequence_logger = seq

        # Use MaintenanceAdapter with injected dependencies
        cmd = MaintenanceAdapter(
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
        self._worker_mgr.cleanup()

        try:
            self.query_one("#status_timer", Label).update("")
            # Reset confirmation state
            self._confirmed = False
            self.query_one("#warning_label", Label).update("⚠️ WARNING: This will ERASE all keys!")
            self.query_one("#btn_reset", Button).label = "Reset to Factory"

            if event.state == WorkerState.SUCCESS:
                self.query_one("#status_label", Label).update("Reset Complete!")
                self.query_one("#result_label", Label).update("✅ TAG RESET TO FACTORY")
                self.query_one("#btn_reset", Button).disabled = False

                # Show sequence summary
                if hasattr(self, "_sequence_logger") and self._sequence_logger:
                    seq = self._sequence_logger
                    log_view = self.query_one("#log_view", RichLog)
                    success_count = sum(1 for s in seq.steps if s.result.value == "success")
                    log_view.write(
                        f"[bold cyan]━━━ {len(seq.steps)} commands | ✓ {success_count} success ━━━[/]"
                    )

                log.info("Factory reset completed successfully")

            elif event.state == WorkerState.ERROR:
                # Extract error details from worker
                error = event.worker.error
                error_type = type(error).__name__ if error else "Unknown"
                error_msg = str(error) if error else "Unknown error"

                # Show error banner with details
                error_label = self.query_one("#error_label", Label)
                error_label.update(f"✗ {error_type}: {error_msg}")
                error_label.add_class("visible")

                self.query_one("#status_label", Label).update("Reset Failed")
                self.query_one("#result_label", Label).update("")
                self.query_one("#btn_reset", Button).disabled = False
                log.error(f"Factory reset failed: {error_type}: {error_msg}")
        except Exception:
            pass
