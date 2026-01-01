"""SequenceLogger - Captures and visualizes APDU command sequences.

Provides real-time sequence diagram output for debugging protocol issues.
Logs actual commands as executed, not planned commands.
"""

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable


log = logging.getLogger(__name__)


# =============================================================================
# Sequenceable Protocol - Commands implement this for accurate sequence logging
# =============================================================================


@runtime_checkable
class Sequenceable(Protocol):
    """Protocol for commands that can be logged in a sequence diagram.

    Commands implementing this protocol provide structured metadata
    for accurate sequence logging, rather than relying on class names.
    """

    @property
    def sequence_name(self) -> str:
        """Human-readable name for sequence diagram display.

        Examples:
            "SelectPiccApplication"
            "AuthenticateEV2First (Key 0)"
            "ChangeFileSettings (File 02)"
        """
        ...

    @property
    def sequence_description(self) -> str:
        """Brief description of what this command does.

        Examples:
            "Select NTAG424 DNA application"
            "Start EV2 authentication with key 0"
        """
        ...

    def get_sequence_params(self) -> dict[str, str]:
        """Get key parameters for detailed logging.

        Returns:
            Dict of parameter name -> value for logging

        Examples:
            {"file_no": "02", "key_no": "0"}
        """
        ...


def get_command_sequence_name(command) -> str:
    """Get the sequence name for a command.

    If command implements Sequenceable, uses sequence_name.
    Otherwise falls back to class name.
    """
    if isinstance(command, Sequenceable):
        return command.sequence_name
    return type(command).__name__


def get_command_sequence_description(command) -> str:
    """Get the sequence description for a command.

    If command implements Sequenceable, uses sequence_description.
    Otherwise returns empty string.
    """
    if isinstance(command, Sequenceable):
        return command.sequence_description
    return ""


class StepResult(Enum):
    """Result of a sequence step."""

    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class SequenceStep:
    """A single step in the command sequence."""

    timestamp: datetime
    command_name: str
    command_bytes: str  # Hex string of C-APDU
    response_bytes: str | None = None  # Hex string of R-APDU
    status_word: str | None = None  # e.g., "9000", "91AD"
    status_name: str | None = None  # e.g., "OK", "NTAG_AUTHENTICATION_DELAY"
    result: StepResult = StepResult.PENDING
    duration_ms: float | None = None


# Type alias for step callback
StepCallback = Callable[[SequenceStep], None] | None


@dataclass
class SequenceLogger:
    """Accumulates command/response pairs and generates sequence diagrams.

    Usage:
        seq = SequenceLogger()
        seq.log_command("SelectPiccApplication", "00 A4 04 00 07 D2 76...")
        seq.log_response("9000", "OK")
        print(seq.render_diagram())

    For live TUI updates, set on_step_complete callback:
        seq.on_step_complete = lambda step: log_view.write(format_step(step))
    """

    steps: list[SequenceStep] = field(default_factory=list)
    _current_step: SequenceStep | None = None
    _start_time: datetime | None = None
    on_step_complete: StepCallback = None  # Called when each step completes

    def start_operation(self, operation_name: str = "Operation"):
        """Start a new sequence (clears previous steps)."""
        self.steps = []
        self._current_step = None
        self._start_time = datetime.now()
        log.info(f"=== SEQUENCE START: {operation_name} ===")

    def log_command(self, command_name: str, apdu_hex: str):
        """Log an outgoing command (C-APDU)."""
        self._current_step = SequenceStep(
            timestamp=datetime.now(),
            command_name=command_name,
            command_bytes=apdu_hex,
        )

    def log_response(self, status_word: str, status_name: str, response_hex: str = ""):
        """Log an incoming response (R-APDU)."""
        if self._current_step:
            self._current_step.response_bytes = response_hex
            self._current_step.status_word = status_word
            self._current_step.status_name = status_name

            # Determine result based on status word
            sw = status_word.upper()
            if sw in ("9000", "9100"):
                self._current_step.result = StepResult.SUCCESS
            elif sw == "91AF":
                # More data available - not an error
                self._current_step.result = StepResult.SUCCESS
            else:
                self._current_step.result = StepResult.ERROR

            # Calculate duration
            if self._current_step.timestamp:
                delta = datetime.now() - self._current_step.timestamp
                self._current_step.duration_ms = delta.total_seconds() * 1000

            self.steps.append(self._current_step)

            # Notify callback for live updates
            if self.on_step_complete:
                with contextlib.suppress(Exception):
                    self.on_step_complete(self._current_step)

            self._current_step = None

    def render_diagram(self, include_bytes: bool = False) -> str:
        """Render the sequence as an ASCII diagram.

        Args:
            include_bytes: If True, include raw APDU bytes
        """
        lines = []
        lines.append("=" * 60)
        lines.append("  SEQUENCE DIAGRAM")
        lines.append("=" * 60)
        lines.append("  Host                              Tag")
        lines.append("   │                                 │")

        for step in self.steps:
            # Command arrow (Host -> Tag)
            cmd_name = step.command_name[:28].ljust(28)
            lines.append(f"   │──── {cmd_name} ────▶│")

            # Include bytes if requested
            if include_bytes and step.command_bytes:
                bytes_preview = step.command_bytes[:40]
                if len(step.command_bytes) > 40:
                    bytes_preview += "..."
                lines.append(f"   │     [{bytes_preview}]")

            # Response arrow (Tag -> Host)
            status = f"{step.status_name} ({step.status_word})"
            if step.result == StepResult.ERROR:
                status = f"❌ {status}"
                status_display = status[:32].ljust(32)
            elif step.result == StepResult.SUCCESS:
                status = f"✓ {status}"
                status_display = status[:32].ljust(32)
            else:
                status_display = status[:32].ljust(32)

            lines.append(f"   │◀──── {status_display} ────│")

            # Add timing if available
            if step.duration_ms:
                lines.append(f"   │      ({step.duration_ms:.1f}ms)")

            lines.append("   │                                 │")

        lines.append("=" * 60)

        # Summary
        success_count = sum(1 for s in self.steps if s.result == StepResult.SUCCESS)
        error_count = sum(1 for s in self.steps if s.result == StepResult.ERROR)
        lines.append(
            f"  Total: {len(self.steps)} commands | ✓ {success_count} success | ❌ {error_count} errors"
        )
        lines.append("=" * 60)

        return "\n".join(lines)

    def render_compact(self) -> str:
        """Render a compact one-line-per-step format."""
        lines = ["=== SEQUENCE ==="]
        for i, step in enumerate(self.steps, 1):
            lines.append(format_step_line(step, i))
        return "\n".join(lines)

    def log_to_file(self, include_bytes: bool = True):
        """Write the full diagram to the log file."""
        diagram = self.render_diagram(include_bytes=include_bytes)
        for line in diagram.split("\n"):
            log.info(line)

    def get_error_summary(self) -> str | None:
        """Get a summary of errors, if any."""
        errors = [s for s in self.steps if s.result == StepResult.ERROR]
        if not errors:
            return None

        error_msgs = [f"{s.command_name}: {s.status_name} ({s.status_word})" for s in errors]
        return "; ".join(error_msgs)


def format_step_line(step: SequenceStep, step_num: int | None = None) -> str:
    """Format a single step as a compact line for live display."""
    icon = "✓" if step.result == StepResult.SUCCESS else "❌"
    prefix = f"  {step_num}. " if step_num else "  "
    timing = f" ({step.duration_ms:.0f}ms)" if step.duration_ms else ""
    return f"{prefix}{icon} {step.command_name} → {step.status_name} ({step.status_word}){timing}"


def format_step_diagram(step: SequenceStep) -> list[str]:
    """Format a single step as diagram lines for live TUI display."""
    lines = []
    # Command arrow (Host -> Tag)
    cmd_name = step.command_name[:28].ljust(28)
    lines.append(f"   │──── {cmd_name} ────▶│")

    # Response arrow (Tag -> Host)
    status = f"{step.status_name} ({step.status_word})"
    if step.result == StepResult.ERROR:
        status = f"❌ {status}"
    elif step.result == StepResult.SUCCESS:
        status = f"✓ {status}"
    status_display = status[:32].ljust(32)
    lines.append(f"   │◀──── {status_display} ────│")

    # Timing
    if step.duration_ms:
        lines.append(f"   │      ({step.duration_ms:.1f}ms)")

    lines.append("   │                                 │")
    return lines


def create_sequence_logger(operation_name: str = "Operation") -> SequenceLogger:
    """Create a new sequence logger for an operation."""
    seq = SequenceLogger()
    seq.start_operation(operation_name)
    return seq
