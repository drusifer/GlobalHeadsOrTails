"""Reusable TUI widgets for NTAG424 provisioning."""

import logging
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import DataTable, Static

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys


log = logging.getLogger(__name__)


@dataclass
class KeyTestResult:
    """Result of testing a specific key."""

    tested: bool = False  # Whether this key was tested
    works: bool | None = None  # None = not tested, True = passed, False = failed


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

    def watch_uid(self, new_value: str) -> None:  # noqa: ARG002
        """React to UID changes."""
        self._update_display()

    def watch_key0_version(self, new_value: int | None) -> None:  # noqa: ARG002
        """React to key version changes."""
        self._update_display()

    def watch_key1_version(self, new_value: int | None) -> None:  # noqa: ARG002
        """React to key version changes."""
        self._update_display()

    def watch_key3_version(self, new_value: int | None) -> None:  # noqa: ARG002
        """React to key version changes."""
        self._update_display()

    def watch_db_keys(self, new_value: TagKeys | None) -> None:  # noqa: ARG002
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


class TagKeysDetailWidget(Static):
    """Detailed widget showing all 3 keys with their status.

    Displays for each key (PICC/App/SDM):
    - Key value (truncated hex)
    - Database presence (in DB or not)
    - Hardware version (from GetKeyVersion)
    - Test status (tested/passed/failed)

    Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ KEY 0 (PICC):  825f8399...  DB: ✓  HW: v01  TESTED: ✓              │
    │ KEY 1 (App):   3865245e...  DB: ✓  HW: v01  TESTED: ✓              │
    │ KEY 3 (SDM):   c099b6d1...  DB: ✓  HW: v01  TESTED: -              │
    └─────────────────────────────────────────────────────────────────────┘
    """

    FACTORY_KEY = "00000000000000000000000000000000"

    # Key values (hex strings, 32 chars)
    picc_key: reactive[str] = reactive(FACTORY_KEY, init=False)
    app_key: reactive[str] = reactive(FACTORY_KEY, init=False)
    sdm_key: reactive[str] = reactive(FACTORY_KEY, init=False)

    # Database presence
    picc_in_db: reactive[bool] = reactive(False, init=False)
    app_in_db: reactive[bool] = reactive(False, init=False)
    sdm_in_db: reactive[bool] = reactive(False, init=False)

    # Hardware key versions (from GetKeyVersion command)
    hw_key0_version: reactive[int | None] = reactive(None, init=False)
    hw_key1_version: reactive[int | None] = reactive(None, init=False)
    hw_key3_version: reactive[int | None] = reactive(None, init=False)

    # Test results: None = not tested, True = passed, False = failed
    picc_tested: reactive[bool | None] = reactive(None, init=False)
    app_tested: reactive[bool | None] = reactive(None, init=False)
    sdm_tested: reactive[bool | None] = reactive(None, init=False)

    DEFAULT_CSS = """
    TagKeysDetailWidget {
        border: solid $accent;
        padding: 0 1;
        height: auto;
        min-height: 3;
        max-height: 5;
        margin-bottom: 1;
    }

    #keys_detail_content {
        height: auto;
        padding: 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[dim]No keys loaded[/dim]", id="keys_detail_content")

    def _format_key_line(
        self,
        label: str,
        key_value: str,
        in_db: bool,
        hw_version: int | None,
        tested: bool | None,
    ) -> str:
        """Format a single key line for display.

        Args:
            label: Key label (e.g., "KEY 0 (PICC)")
            key_value: 32-char hex string
            in_db: Whether key is in database
            hw_version: Hardware key version or None
            tested: Test result (None=not tested, True=passed, False=failed)

        Returns:
            Formatted string with Rich markup
        """
        # Truncate key to first 8 chars + ellipsis
        is_factory = key_value == self.FACTORY_KEY
        key_display = "[dim]00000000...[/dim]" if is_factory else f"{key_value[:8]}..."

        # Database indicator
        if in_db and not is_factory:
            db_indicator = "[green]DB:✓[/green]"
        elif is_factory:
            db_indicator = "[yellow]DB:FAC[/yellow]"
        else:
            db_indicator = "[red]DB:✗[/red]"

        # Hardware version indicator
        if hw_version is not None:
            if hw_version == 0:
                hw_indicator = "[yellow]HW:v00[/yellow]"
            else:
                hw_indicator = f"[green]HW:v{hw_version:02d}[/green]"
        else:
            hw_indicator = "[dim]HW:---[/dim]"

        # Test status indicator
        if tested is None:
            test_indicator = "[dim]TEST:-[/dim]"
        elif tested:
            test_indicator = "[green]TEST:✓[/green]"
        else:
            test_indicator = "[red]TEST:✗[/red]"

        return f"{label:14s} {key_display:14s} {db_indicator:16s} {hw_indicator:16s} {test_indicator}"

    def _update_display(self) -> None:
        """Update the display with current key states."""
        content = self.query_one("#keys_detail_content", Static)

        lines = [
            self._format_key_line(
                "KEY 0 (PICC):",
                self.picc_key,
                self.picc_in_db,
                self.hw_key0_version,
                self.picc_tested,
            ),
            self._format_key_line(
                "KEY 1 (App):",
                self.app_key,
                self.app_in_db,
                self.hw_key1_version,
                self.app_tested,
            ),
            self._format_key_line(
                "KEY 3 (SDM):",
                self.sdm_key,
                self.sdm_in_db,
                self.hw_key3_version,
                self.sdm_tested,
            ),
        ]

        content.update("\n".join(lines))

    # Watchers for reactive updates
    def watch_picc_key(self, new_value: str) -> None:  # noqa: ARG002
        self._update_display()

    def watch_app_key(self, new_value: str) -> None:  # noqa: ARG002
        self._update_display()

    def watch_sdm_key(self, new_value: str) -> None:  # noqa: ARG002
        self._update_display()

    def watch_picc_in_db(self, new_value: bool) -> None:  # noqa: ARG002
        self._update_display()

    def watch_app_in_db(self, new_value: bool) -> None:  # noqa: ARG002
        self._update_display()

    def watch_sdm_in_db(self, new_value: bool) -> None:  # noqa: ARG002
        self._update_display()

    def watch_hw_key0_version(self, new_value: int | None) -> None:  # noqa: ARG002
        self._update_display()

    def watch_hw_key1_version(self, new_value: int | None) -> None:  # noqa: ARG002
        self._update_display()

    def watch_hw_key3_version(self, new_value: int | None) -> None:  # noqa: ARG002
        self._update_display()

    def watch_picc_tested(self, new_value: bool | None) -> None:  # noqa: ARG002
        self._update_display()

    def watch_app_tested(self, new_value: bool | None) -> None:  # noqa: ARG002
        self._update_display()

    def watch_sdm_tested(self, new_value: bool | None) -> None:  # noqa: ARG002
        self._update_display()

    def update_from_database(self, tag_keys: TagKeys | None) -> None:
        """Update widget with keys from database.

        Args:
            tag_keys: TagKeys object from CsvKeyManager, or None if not found
        """
        if tag_keys is None:
            self.picc_key = self.FACTORY_KEY
            self.app_key = self.FACTORY_KEY
            self.sdm_key = self.FACTORY_KEY
            self.picc_in_db = False
            self.app_in_db = False
            self.sdm_in_db = False
        else:
            self.picc_key = tag_keys.picc_master_key
            self.app_key = tag_keys.app_read_key
            self.sdm_key = tag_keys.sdm_mac_key
            # Key is "in DB" if it's not factory (all zeros)
            self.picc_in_db = tag_keys.picc_master_key != self.FACTORY_KEY
            self.app_in_db = tag_keys.app_read_key != self.FACTORY_KEY
            self.sdm_in_db = tag_keys.sdm_mac_key != self.FACTORY_KEY

    def update_from_hardware(
        self,
        key0_ver: int,
        key1_ver: int,
        key3_ver: int,
    ) -> None:
        """Update widget with hardware key versions.

        Args:
            key0_ver: Key 0 version from GetKeyVersion
            key1_ver: Key 1 version from GetKeyVersion
            key3_ver: Key 3 version from GetKeyVersion
        """
        self.hw_key0_version = key0_ver
        self.hw_key1_version = key1_ver
        self.hw_key3_version = key3_ver

    def update_test_results(
        self,
        picc_works: bool | None = None,
        app_works: bool | None = None,
        sdm_works: bool | None = None,
    ) -> None:
        """Update widget with test results.

        Args:
            picc_works: PICC key test result (None=not tested, True=passed, False=failed)
            app_works: App key test result
            sdm_works: SDM key test result
        """
        if picc_works is not None:
            self.picc_tested = picc_works
        if app_works is not None:
            self.app_tested = app_works
        if sdm_works is not None:
            self.sdm_tested = sdm_works

    def clear_test_results(self) -> None:
        """Clear all test results (set to not tested)."""
        self.picc_tested = None
        self.app_tested = None
        self.sdm_tested = None

    def clear(self) -> None:
        """Clear all key information."""
        self.picc_key = self.FACTORY_KEY
        self.app_key = self.FACTORY_KEY
        self.sdm_key = self.FACTORY_KEY
        self.picc_in_db = False
        self.app_in_db = False
        self.sdm_in_db = False
        self.hw_key0_version = None
        self.hw_key1_version = None
        self.hw_key3_version = None
        self.picc_tested = None
        self.app_tested = None
        self.sdm_tested = None


@dataclass
class KeyCandidate:
    """A key candidate for display in the table."""

    source: str  # Source file (e.g., "backup1.csv (log)")
    status: str  # Status (e.g., "provisioned", "failed", "log_complete")
    date: str  # Date string (e.g., "2025-12-25")
    picc_key: str  # PICC key hex (32 chars)
    app_key: str  # App key hex (32 chars)
    sdm_key: str  # SDM key hex (32 chars)
    picc_tested: bool | None = None  # Test result for PICC key
    app_tested: bool | None = None  # Test result for App key
    sdm_tested: bool | None = None  # Test result for SDM key


class KeyCandidatesTable(DataTable):
    """Table widget showing key candidates from backup files.

    Columns: Source | Status | Date | PICC | App | SDM | Tested
    Shows partial key values (first 8 chars) and test status indicators.

    Layout:
    ┌───────────┬────────┬──────────┬──────────┬──────────┬──────────┬─────────────┐
    │ Source    │ Status │ Date     │ PICC     │ App      │ SDM      │ Tested      │
    ├───────────┼────────┼──────────┼──────────┼──────────┼──────────┼─────────────┤
    │ backup1   │ prov   │ 12/25    │ 825f...  │ 3865...  │ c099...  │ ✓P ✓A -S    │
    │ backup2   │ failed │ 12/20    │ 825f...  │ 0000...  │ 0000...  │ ✓P -A -S    │
    │ tag_keys  │ prov   │ 11/08    │ 825f...  │ 3865...  │ c099...  │ -           │
    └───────────┴────────┴──────────┴──────────┴──────────┴──────────┴─────────────┘
    """

    FACTORY_KEY = "00000000000000000000000000000000"

    DEFAULT_CSS = """
    KeyCandidatesTable {
        height: auto;
        min-height: 5;
        max-height: 15;
        border: solid $primary;
        margin-bottom: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._candidates: list[KeyCandidate] = []

    def on_mount(self) -> None:
        """Initialize the table columns."""
        self.add_column("Source", key="source", width=20)
        self.add_column("Status", key="status", width=10)
        self.add_column("Date", key="date", width=10)
        self.add_column("PICC", key="picc", width=10)
        self.add_column("App", key="app", width=10)
        self.add_column("SDM", key="sdm", width=10)
        self.add_column("Tested", key="tested", width=12)
        self.cursor_type = "row"

    def _format_key(self, key_hex: str) -> str:
        """Format a key for display (truncated)."""
        if key_hex == self.FACTORY_KEY:
            return "[dim]0000...[/dim]"
        return f"{key_hex[:4]}..."

    def _format_status(self, status: str) -> str:
        """Format status with color coding."""
        status_colors = {
            "provisioned": "green",
            "prov": "green",
            "keys_configured": "cyan",
            "log_complete": "green",
            "log_partial": "yellow",
            "log_picc_only": "yellow",
            "picc_only": "yellow",
            "partial_keys": "yellow",
            "pending": "yellow",
            "failed": "red",
            "factory": "dim",
        }
        color = status_colors.get(status, "white")
        # Truncate status to 8 chars
        display = status[:8] if len(status) > 8 else status
        return f"[{color}]{display}[/{color}]"

    def _format_tested(self, candidate: KeyCandidate) -> str:
        """Format tested column showing which keys were tested."""
        parts = []

        # PICC test status
        if candidate.picc_tested is None:
            parts.append("[dim]-P[/dim]")
        elif candidate.picc_tested:
            parts.append("[green]✓P[/green]")
        else:
            parts.append("[red]✗P[/red]")

        # App test status
        if candidate.app_tested is None:
            parts.append("[dim]-A[/dim]")
        elif candidate.app_tested:
            parts.append("[green]✓A[/green]")
        else:
            parts.append("[red]✗A[/red]")

        # SDM test status
        if candidate.sdm_tested is None:
            parts.append("[dim]-S[/dim]")
        elif candidate.sdm_tested:
            parts.append("[green]✓S[/green]")
        else:
            parts.append("[red]✗S[/red]")

        return " ".join(parts)

    def load_candidates(self, candidates: list[KeyCandidate]) -> None:
        """Load candidates into the table.

        Args:
            candidates: List of KeyCandidate objects to display
        """
        self._candidates = candidates
        self.clear()

        for i, candidate in enumerate(candidates):
            # Truncate source to fit
            source_display = candidate.source
            if len(source_display) > 18:
                source_display = source_display[:15] + "..."

            self.add_row(
                source_display,
                self._format_status(candidate.status),
                candidate.date,
                self._format_key(candidate.picc_key),
                self._format_key(candidate.app_key),
                self._format_key(candidate.sdm_key),
                self._format_tested(candidate),
                key=str(i),
            )

    def get_selected_candidate(self) -> KeyCandidate | None:
        """Get the currently selected candidate.

        Returns:
            KeyCandidate if a row is selected, None otherwise
        """
        if self.cursor_row is None or self.cursor_row >= len(self._candidates):
            return None
        return self._candidates[self.cursor_row]

    def get_candidate_at_index(self, index: int) -> KeyCandidate | None:
        """Get candidate at a specific index.

        Args:
            index: Row index

        Returns:
            KeyCandidate if index is valid, None otherwise
        """
        if 0 <= index < len(self._candidates):
            return self._candidates[index]
        return None

    def update_test_results(
        self,
        index: int,
        picc_works: bool | None = None,
        app_works: bool | None = None,
        sdm_works: bool | None = None,
    ) -> None:
        """Update test results for a specific candidate.

        Args:
            index: Row index to update
            picc_works: PICC key test result
            app_works: App key test result
            sdm_works: SDM key test result
        """
        if 0 <= index < len(self._candidates):
            candidate = self._candidates[index]
            if picc_works is not None:
                candidate.picc_tested = picc_works
            if app_works is not None:
                candidate.app_tested = app_works
            if sdm_works is not None:
                candidate.sdm_tested = sdm_works

            # Update the tested column in the table
            self.update_cell(str(index), "tested", self._format_tested(candidate))

    @property
    def candidate_count(self) -> int:
        """Return the number of candidates in the table."""
        return len(self._candidates)


class PhoneTapWidget(Static):
    """Widget showing SDM validation results (Phone Tap simulation).

    Displays:
    - URL from tag
    - SDM parameters (UID, Counter, CMAC)
    - Validation result (VALID/INVALID)
    - Android NFC detection checklist

    Layout:
    ┌─────────────────────────────────────────────────────────────────────┐
    │ PHONE TAP TEST                                                       │
    │ URL: ...exec?uid=04B7664A2F7080&ctr=000005&cmac=A1B2C3D4E5F6G7H8     │
    │ ✓ VALID SDM - CMAC matches                                           │
    │                                                                       │
    │ Android NFC Detection:                                                │
    │   1. Read Access FREE: ✓                                             │
    │   2. NDEF Format: ✓                                                  │
    │   3. CC File Valid: ✓                                                │
    │   4. Offsets Valid: ✓                                                │
    └─────────────────────────────────────────────────────────────────────┘
    """

    DEFAULT_CSS = """
    PhoneTapWidget {
        border: solid $success;
        padding: 0 1;
        height: auto;
        min-height: 5;
        max-height: 15;
        margin-bottom: 1;
    }

    #phone_tap_content {
        height: auto;
        padding: 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[dim]No SDM validation data[/dim]", id="phone_tap_content")

    def update_from_validation(self, sdm_validation: dict | None) -> None:
        """Update widget with SDM validation results.

        Args:
            sdm_validation: Dictionary with SDM validation data from diagnostics,
                           or None to clear the widget
        """
        content = self.query_one("#phone_tap_content", Static)

        if sdm_validation is None:
            content.update("[dim]No SDM validation data[/dim]")
            return

        lines = ["[bold cyan]PHONE TAP TEST[/]"]

        if not isinstance(sdm_validation, dict):
            lines.append(f"[red]Invalid data: {sdm_validation}[/]")
            content.update("\n".join(lines))
            return

        # Show URL if available
        url = sdm_validation.get("url", "")
        if url:
            # Show truncated URL (last ~70 chars with SDM params)
            url_display = "..." + url[-67:] if len(url) > 70 else url
            lines.append(f"[cyan]{url_display}[/]")

        # Check for errors
        if sdm_validation.get("error"):
            lines.append(f"[red]{sdm_validation['error'][:50]}[/]")
            content.update("\n".join(lines))
            return

        if not sdm_validation.get("has_url"):
            lines.append("[yellow]No URL on tag[/]")
            content.update("\n".join(lines))
            return

        if not sdm_validation.get("has_sdm"):
            lines.append("[yellow]No SDM parameters in URL[/]")
            content.update("\n".join(lines))
            return

        # Show validation result
        validation = sdm_validation.get("validation", {})
        if validation:
            uid = validation.get("uid", "N/A")
            counter = validation.get("counter", "N/A")
            cmac_received = validation.get("cmac_received", "N/A")

            lines.append(f"[yellow]UID:[/] {uid}  [yellow]Counter:[/] {counter}  [yellow]CMAC:[/] {cmac_received}")

            if validation.get("valid"):
                lines.append("[green bold]✓ VALID - CMAC matches[/]")
                # Show warning if using factory default key
                if validation.get("warning"):
                    lines.append(f"[yellow]{validation['warning']}[/]")
            elif validation.get("error"):
                if "placeholders" in validation.get("error", "").lower():
                    lines.append("[yellow]Placeholders not yet replaced[/]")
                    lines.append("[dim]Tag not yet tapped by phone[/]")
                else:
                    lines.append("[red bold]✗ INVALID - CMAC mismatch[/]")
                    lines.append(f"[red]{validation.get('error', 'Unknown')[:50]}[/]")
            else:
                lines.append("[red bold]✗ INVALID - CMAC mismatch[/]")
                cmac_calculated = validation.get("cmac_calculated", "N/A")
                lines.append(f"[dim]Expected:[/] {cmac_calculated}")
        else:
            lines.append("[yellow]No validation performed[/]")

        # Android NFC detection checks
        android_checks = sdm_validation.get("android_nfc_checks", {})
        if isinstance(android_checks, dict) and android_checks:
            lines.append("")
            lines.append("[bold yellow]Android NFC Detection:[/]")

            all_pass = android_checks.get("all_conditions_pass", False)
            if all_pass:
                lines.append("[green]✓ ALL CHECKS PASS - Android will detect tag[/]")
            else:
                lines.append("[yellow]⚠ Some checks failed[/]")

            c1 = android_checks.get("condition_1_read_access_free", False)
            c2 = android_checks.get("condition_2_ndef_format", False)
            c3 = android_checks.get("condition_3_cc_file_valid", False)
            c4 = android_checks.get("condition_4_offsets_valid", False)

            def check_mark(v: bool) -> str:
                return "[green]✓[/]" if v else "[red]✗[/]"

            lines.append(f"  1. Read Access FREE: {check_mark(c1)}")
            lines.append(f"  2. NDEF Format: {check_mark(c2)}")
            lines.append(f"  3. CC File Valid: {check_mark(c3)}")
            lines.append(f"  4. Offsets Valid: {check_mark(c4)}")

        content.update("\n".join(lines))

    def clear(self) -> None:
        """Clear the widget."""
        content = self.query_one("#phone_tap_content", Static)
        content.update("[dim]No SDM validation data[/dim]")
