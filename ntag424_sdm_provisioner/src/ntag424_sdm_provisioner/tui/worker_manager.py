"""WorkerManager - Centralized async orchestration for Textual screens."""

from textual.screen import Screen
from textual.worker import Worker

from ntag424_sdm_provisioner.tui.nfc_command import NFCCommand


class WorkerManager:
    """Centralized worker orchestration.

    Built-in timer and state management. Eliminates race conditions by encapsulating all async interaction.
    """

    def __init__(self, screen: Screen):
        self._screen = screen
        self._timer: object | None = None  # Textual Timer
        self._countdown: int = 0
        self._worker: Worker | None = None

    def execute_command(
        self, command: NFCCommand, _status_label_id: str, timer_label_id: str
    ) -> None:
        """Execute NFC command with automatic timer/state management.

        Thread-safe, no race conditions.

        Args:
            command: NFCCommand to execute
            _status_label_id: ID of status label widget (unused)
            timer_label_id: ID of timer label widget
        """
        # Start countdown
        self._countdown = command.timeout_seconds
        self._update_label(timer_label_id, f"Waiting for tap... {self._countdown}s")
        self._timer = self._screen.set_interval(1.0, lambda: self._tick(timer_label_id))

        # Run worker (always thread-based for blocking I/O)
        self._worker = self._screen.run_worker(command.execute, exclusive=True, thread=True)

    def _tick(self, label_id: str) -> None:
        """Timer tick handler (race-safe)."""
        self._countdown -= 1
        try:
            if self._countdown > 0:
                self._update_label(label_id, f"Waiting for tap... {self._countdown}s")
            else:
                self._update_label(label_id, "Timeout imminent...")
        except Exception:
            # Screen might be unmounted
            if self._timer:
                self._timer.stop()  # type: ignore[attr-defined]

    def _update_label(self, label_id: str, text: str) -> None:
        """Safely update a label widget."""
        try:
            label = self._screen.query_one(f"#{label_id}")
            label.update(text)  # type: ignore[attr-defined]
        except Exception:
            # Widget might not exist or screen unmounted
            pass

    def cleanup(self) -> None:
        """Cleanup resources (call from on_worker_state_changed)."""
        if self._timer:
            self._timer.stop()  # type: ignore[attr-defined]
            self._timer = None
