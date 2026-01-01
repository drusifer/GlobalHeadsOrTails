"""Base types for NTAG424 Tag Tools.

Defines the Tool protocol and common data structures for clean separation
between business logic (tools) and I/O (runner).
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import NTag424CardConnection


@dataclass
class TagState:
    """Current state of a tag.

    Assessed by runner before offering tools to user.
    Passed to tools for decision making.
    """

    uid: bytes
    in_database: bool
    keys: Any  # KeysRecord from CSV
    has_ndef: bool
    backup_count: int


@dataclass
class ConfirmationRequest:
    """Request for user confirmation before executing tool.

    Runner displays this and gets user input before calling tool.execute().
    """

    title: str
    items: list[str]  # List of actions that will be performed
    default_yes: bool = False


@dataclass
class ToolResult:
    """Result from tool execution.

    Tools return this instead of printing. Runner handles display.
    """

    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class Tool(Protocol):
    """Protocol for tag tools.

    Tools are pure business logic - no I/O!
    Runner handles all display and input.
    """

    name: str
    description: str

    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        """Check if tool can run on this tag.

        Returns:
            True if available
            (False, reason) if not available
        """
        ...

    def get_confirmation_request(self, tag_state: TagState) -> ConfirmationRequest | None:
        """Get confirmation details if tool needs user approval.

        Returns:
            ConfirmationRequest if confirmation needed
            None if tool should run without confirmation
        """
        ...

    def execute(
        self, tag_state: TagState, card: NTag424CardConnection, key_mgr: CsvKeyManager
    ) -> ToolResult:
        """Execute tool logic - NO I/O!

        NO print(), NO input() - return ToolResult instead.
        Runner will display results and handle errors.

        Returns:
            ToolResult with success status and data

        Raises:
            Exception on error (runner catches and displays)
        """
        ...
