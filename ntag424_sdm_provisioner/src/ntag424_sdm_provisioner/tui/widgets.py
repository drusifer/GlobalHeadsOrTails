"""Reusable TUI widgets for NTAG424 provisioning."""

import logging
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys


log = logging.getLogger(__name__)


class TagStatusWidget(Static):
    """Compact widget showing current tag state.

    Displays:
    - UID
    - Key versions (from hardware)
    - Database status
    - Key presence indicators (✓/✗)
    """

    uid: reactive[str] = reactive("", init=False)
    key0_version: reactive[int | None] = reactive(None, init=False)
    key1_version: reactive[int | None] = reactive(None, init=False)
    key3_version: reactive[int | None] = reactive(None, init=False)
    db_keys: reactive[TagKeys | None] = reactive(None, init=False)

    DEFAULT_CSS = """
    TagStatusWidget {
        border: round $primary;
        padding: 0 1;
        height: auto;
        max-height: 6;
        min-height: 2;
        margin-bottom: 1;
    }

    #tag_status_content {
        height: auto;
        padding: 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[dim]No tag scanned[/dim]", id="tag_status_content")

    def watch_uid(self, new_value: str) -> None:
        """React to UID changes."""
        self._update_display()

    def watch_key0_version(self, new_value: int | None) -> None:
        """React to key version changes."""
        self._update_display()

    def watch_key1_version(self, new_value: int | None) -> None:
        """React to key version changes."""
        self._update_display()

    def watch_key3_version(self, new_value: int | None) -> None:
        """React to key version changes."""
        self._update_display()

    def watch_db_keys(self, new_value: TagKeys | None) -> None:
        """React to database keys changes."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the display with current tag state."""
        content = self.query_one("#tag_status_content", Static)

        if not self.uid:
            content.update("[dim]No tag scanned[/dim]")
            return

        lines = []

        # Compact: UID + HW state + DB state on one line
        hw_indicator = ""
        if self.key0_version is not None:
            is_factory = (self.key0_version == 0x00 and
                         self.key1_version == 0x00 and
                         self.key3_version == 0x00)
            hw_color = "yellow" if is_factory else "green"
            hw_state = "FAC" if is_factory else "PRO"
            hw_indicator = f"[{hw_color}]HW:{hw_state}[/{hw_color}]"

        # Database status
        db_indicator = ""
        if self.db_keys:
            status_color = {
                "provisioned": "green",
                "keys_configured": "cyan",
                "picc_verified": "blue",  # Only PICC key verified, Keys 1/3 unknown
                "reformatted": "magenta",  # Factory reset via FormatPICC
                "pending": "yellow",
                "failed": "red",
                "factory": "yellow",
            }.get(self.db_keys.status, "white")
            db_indicator = f"[{status_color}]DB:{self.db_keys.status[:4].upper()}[/{status_color}]"
        else:
            db_indicator = "[dim]DB:N/A[/dim]"

        # First line: UID + status indicators
        lines.append(f"{self.uid}  {hw_indicator}  {db_indicator}")

        # Second line: Key presence (only if in database)
        if self.db_keys:
            picc_present = self.db_keys.picc_master_key != "00000000000000000000000000000000"
            app_present = self.db_keys.app_read_key != "00000000000000000000000000000000"
            sdm_present = self.db_keys.sdm_mac_key != "00000000000000000000000000000000"

            picc_marker = "[green]✓[/green]" if picc_present else "[red]✗[/red]"
            app_marker = "[green]✓[/green]" if app_present else "[red]✗[/red]"
            sdm_marker = "[green]✓[/green]" if sdm_present else "[red]✗[/red]"

            lines.append(
                f"Keys: PICC{picc_marker} App{app_marker} SDM{sdm_marker}"
            )

        content.update("\n".join(lines))

    def update_from_hardware(
        self,
        uid: str,
        key0_ver: int,
        key1_ver: int,
        key3_ver: int
    ) -> None:
        """Update widget with hardware-read values.

        Args:
            uid: Tag UID as hex string
            key0_ver: Key 0 version from GetKeyVersion
            key1_ver: Key 1 version from GetKeyVersion
            key3_ver: Key 3 version from GetKeyVersion
        """
        self.uid = uid
        self.key0_version = key0_ver
        self.key1_version = key1_ver
        self.key3_version = key3_ver

    def update_from_database(self, key_manager: CsvKeyManager, uid: str) -> None:
        """Update widget with database values.

        Args:
            key_manager: CsvKeyManager instance
            uid: Tag UID as hex string
        """
        try:
            keys = key_manager.get_tag_keys(uid)
            self.db_keys = keys
        except Exception:
            self.db_keys = None

    def clear(self) -> None:
        """Clear all tag information."""
        self.uid = ""
        self.key0_version = None
        self.key1_version = None
        self.key3_version = None
        self.db_keys = None
