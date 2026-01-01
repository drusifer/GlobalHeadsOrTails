"""NFCCommand abstraction for headless-ready NFC operations."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class NFCCommand(ABC):
    """Abstract base for NFC operations.

    UI-agnostic design allows commands to run:
    - In TUI (via WorkerManager)
    - In CLI (headless mode)
    - In tests (direct call)
    """

    @abstractmethod
    def execute(self) -> Any:
        """Execute the blocking NFC operation.

        Returns:
            Operation result (tag data, provision status, etc.)
        """

    @property
    @abstractmethod
    def timeout_seconds(self) -> int:
        """Get the operation timeout in seconds."""

    @property
    @abstractmethod
    def operation_name(self) -> str:
        """Get the human-readable operation name (for logging/UI)."""

    def execute_with_progress(self, progress_callback: Callable[[str], None] | None = None) -> Any:
        """Execute with optional progress updates.

        Args:
            progress_callback: Optional callback for progress messages
                               (used by UI or logging)

        Returns:
            Operation result
        """
        if progress_callback:
            progress_callback(f"Starting {self.operation_name}...")

        try:
            result = self.execute()
            if progress_callback:
                progress_callback(f"Completed {self.operation_name}")
            return result
        except Exception as e:
            if progress_callback:
                progress_callback(f"Failed {self.operation_name}: {e}")
            raise
