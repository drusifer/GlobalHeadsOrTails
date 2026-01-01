"""Tool Runner - Main loop for tag operations.

Handles connection management, tag state assessment, menu display,
and tool execution with error handling.
"""

import csv
import logging
import sys
from contextlib import contextmanager

from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.hal import CardManager, NTag424CardConnection
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger, create_sequence_logger
from ntag424_sdm_provisioner.tools.base import TagState, Tool, ToolResult
from ntag424_sdm_provisioner.tools.configure_sdm_tool import ConfigureSdmTool
from ntag424_sdm_provisioner.tools.diagnostics_tool import DiagnosticsTool
from ntag424_sdm_provisioner.tools.provision_factory_tool import ProvisionFactoryTool
from ntag424_sdm_provisioner.tools.restore_backup_tool import RestoreBackupTool
from ntag424_sdm_provisioner.tools.tool_helpers import has_ndef_content as check_ndef_content
from ntag424_sdm_provisioner.tools.tool_helpers import read_ndef_file
from ntag424_sdm_provisioner.trace_util import trace_block
from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag


log = logging.getLogger(__name__)


class ToolRunner:
    """Main orchestrator for tool-based tag operations.

    Manages:
    - Tag connection/disconnection per operation
    - Tag state assessment
    - Tool filtering based on preconditions
    - Menu display and user interaction
    - Tool execution with error handling
    """

    def __init__(self, key_mgr: CsvKeyManager, tools: list[Tool], reader_index: int = 0):
        """Initialize tool runner.

        Args:
            key_mgr: Key manager for database operations
            tools: List of available tools
            reader_index: Reader index (default 0 for first reader)
        """
        self.key_mgr = key_mgr
        self.tools = tools
        self.reader_index = reader_index
        self.sequence_logger: SequenceLogger | None = None

    @contextmanager
    def _connect_to_tag(self):
        """Connect to tag on reader, yield connection, disconnect.

        Fresh connection for each operation - allows tag swapping,
        rate limit recovery, and clean state.

        CardManager handles connection/disconnection automatically.
        """
        log.info("Connecting to tag...")
        # Create sequence logger for this connection
        self.sequence_logger = create_sequence_logger("ToolRunner")
        with CardManager(self.sequence_logger, reader_index=self.reader_index) as card:
            # card is already NTag424CardConnection from CardManager.__enter__
            # Select application
            card.send(SelectPiccApplication())
            log.info("Connected to tag")
            yield card
        # CardManager.__exit__ handles disconnect automatically
        log.info("Disconnected from tag")

    def _get_tag_state_fresh(self) -> TagState:
        """Assess tag state using a fresh connection.

        Returns:
            TagState snapshot
        """
        with self._connect_to_tag() as card:
            return self._assess_tag_state(card)

    def _collect_diagnostics(self) -> dict:
        """Run diagnostics tool with a fresh connection and return details."""
        diagnostics: dict = {}
        try:
            with self._connect_to_tag() as card:
                tag_state = self._assess_tag_state(card)
                diag_tool = DiagnosticsTool()
                result = diag_tool.execute(tag_state, card, self.key_mgr)
                diagnostics = result.details or {}
        except Exception as exc:
            diagnostics = {"error": str(exc)}
        return diagnostics

    def _execute_tool_auto(self, tool: Tool) -> ToolResult:
        """Execute a tool using a fresh connection (no prompts/prints).

        Args:
            tool: Tool implementation to execute

        Returns:
            ToolResult from tool execution

        Raises:
            RuntimeError if tool is unavailable for current tag state
            Exception propagated from tool.execute on failure
        """
        with self._connect_to_tag() as card:
            tag_state = self._assess_tag_state(card)
            availability = tool.is_available(tag_state)
            if availability is True:
                return tool.execute(tag_state, card, self.key_mgr)
            if isinstance(availability, tuple):
                is_available, reason = availability
                if not is_available:
                    raise RuntimeError(f"{tool.name} unavailable: {reason}")
                return tool.execute(tag_state, card, self.key_mgr)
            raise RuntimeError(f"{tool.name} unavailable for current tag state")

    def run_auto(self, base_url: str) -> ToolResult:
        """Perform automatic SDM provisioning workflow.

        Steps:
            1. Assess current tag state.
            2. Provision factory tags if required.
            3. Configure SDM (authenticated).
               - On auth failure, attempt restore-from-backup and retry once.

        Returns:
            ToolResult summarising actions performed.
        """
        steps: list[str] = []
        provision_tool = ProvisionFactoryTool(base_url)
        configure_tool = ConfigureSdmTool(base_url)
        restore_tool = RestoreBackupTool()

        def needs_provision(state: TagState) -> bool:
            keys = getattr(state, "keys", None)
            status = getattr(keys, "status", "")
            return (not state.in_database) or status.lower() in {"factory", "pending", ""}

        with trace_block("Auto Provision"):
            try:
                current_state = self._get_tag_state_fresh()
            except Exception as exc:
                log.exception("Failed to assess tag state")
                return ToolResult(
                    success=False,
                    message="Auto provisioning failed while assessing tag",
                    details={
                        "steps": steps,
                        "error": str(exc),
                        "diagnostics": self._collect_diagnostics(),
                    },
                )

            # Step 1: Provision if needed (with restore fallback)
            if needs_provision(current_state):
                steps.append("Provisioning factory tag")
                try:
                    provision_result = self._execute_tool_auto(provision_tool)  # type: ignore[arg-type]
                except Exception as exc:
                    steps.append(f"Provisioning failed: {exc}")
                    steps.append("Attempting restore from backup")
                    try:
                        restore_result = self._execute_tool_auto(restore_tool)
                    except Exception as restore_exc:
                        steps.append(f"Restore failed: {restore_exc}")
                        raise RuntimeError("Provision failed; restore failed") from restore_exc

                    if not restore_result.success:
                        steps.append(f"Restore completed with warnings: {restore_result.message}")
                        raise RuntimeError("Provision failed; restore produced warnings") from None

                    steps.append("Restore succeeded")
                    current_state = self._get_tag_state_fresh()
                else:
                    if not provision_result.success:
                        steps.append(
                            f"Provisioning completed with warnings: {provision_result.message}"
                        )
                        raise RuntimeError("Provision returned warnings")
                    steps.append("Provisioning succeeded")
                    current_state = self._get_tag_state_fresh()

                    if needs_provision(current_state):
                        steps.append("Tag remains in factory state after restore/provision")
                        return ToolResult(
                            success=False,
                            message="Auto provisioning could not progress beyond factory state",
                            details={"steps": steps, "diagnostics": self._collect_diagnostics()},
                        )
            else:
                steps.append("Tag already provisioned; skipping factory provision")

            # Step 2: Configure SDM
            def configure_sdm(step_label: str) -> tuple[bool, ToolResult | None, str | None]:
                try:
                    result = self._execute_tool_auto(configure_tool)
                except Exception as exc:
                    log.exception("Configure SDM failed")
                    return False, None, str(exc)

                if result.success:
                    detail = dict(result.details)
                    detail["steps"] = steps + [step_label]
                    return True, ToolResult(True, "Auto SDM completed", detail), None

                detail = dict(result.details)
                detail["steps"] = steps + [f"{step_label} (warnings: {result.message})"]
                return False, ToolResult(False, result.message, detail), None

            steps.append("Configuring SDM")
            success, final_result, error = configure_sdm("SDM configured")
            if success and final_result:
                diag_summary = self._collect_diagnostics()
                final_result.details = final_result.details or {}
                final_result.details["diagnostics"] = diag_summary
                return final_result

            if error is None and final_result:
                # Configuration finished with warnings (no exception)
                return final_result

            steps.append("SDM configuration failed; attempting restore from backup")
            try:
                restore_result = self._execute_tool_auto(restore_tool)
            except Exception as exc:
                steps.append(f"Restore failed: {exc}")
                raise RuntimeError("Restore from backup failed") from exc

            if not restore_result.success:
                steps.append(f"Restore completed with warnings: {restore_result.message}")
                raise RuntimeError("Restore from backup returned warning")

            steps.append("Restore succeeded; retrying SDM configuration")
            success, final_result, error = configure_sdm("SDM configured after restore")
            if final_result:
                diag_summary = self._collect_diagnostics()
                final_result.details = final_result.details or {}
                final_result.details["diagnostics"] = diag_summary
                return final_result

            steps.append(f"SDM configuration retry failed: {error}")
            raise RuntimeError("SDM configuration failed after restore attempt")

    def _assess_tag_state(self, card: NTag424CardConnection) -> TagState:
        """Assess current state of the tag.

        Reads tag info, checks database, examines NDEF, scans backups.

        Args:
            card: Open connection to tag

        Returns:
            TagState with all relevant information
        """
        # Get UID and version
        version_info = card.send(GetChipVersion())
        uid = version_info.uid
        asset_tag = uid_to_asset_tag(uid)

        log.info(f"Assessing tag state for UID: {uid.hex().upper()} [{asset_tag}]")

        # Check database
        in_database = False
        keys = None
        try:
            keys = self.key_mgr.get_tag_keys(uid)
            in_database = True
            log.debug(f"Tag in database: status={keys.status}")
        except KeyError:
            log.debug("Tag not in database")

        # Check NDEF content (using helper - single source of truth)
        ndef_has_content = False
        try:
            ndef_data = read_ndef_file(card)
            ndef_has_content = check_ndef_content(ndef_data)
            log.debug(f"NDEF content detected: {ndef_has_content}")
        except Exception as e:
            log.debug(f"Could not read NDEF: {e}")

        # Check backups
        backups = self._get_backups_for_uid(uid)
        has_successful_backup = any(b.get("status") == "provisioned" for b in backups)

        log.debug(f"Backups: {len(backups)} total, successful={has_successful_backup}")

        return TagState(
            uid=uid,
            in_database=in_database,
            keys=keys,
            has_ndef=ndef_has_content,
            backup_count=len(backups),
        )

    def _get_backups_for_uid(self, uid: bytes) -> list:
        """Load all backups for a specific UID."""
        backups: list[dict[str, str]] = []
        backup_path = self.key_mgr.backup_path

        if not backup_path.exists():
            return backups

        uid_hex = uid.hex().upper()

        try:
            with backup_path.open(newline="") as f:
                reader = csv.DictReader(f)
                backups = [row for row in reader if row["uid"].upper() == uid_hex]
        except Exception as e:
            log.warning(f"Error reading backups: {e}")

        return backups

    def _show_menu(self, tag_state: TagState) -> int | str:
        """Display menu showing ALL tools (available and unavailable).

        Args:
            tag_state: Current tag state

        Returns:
            Tool index (0-based) or 'quit'
        """
        print("\n" + "=" * 70)
        print("NTAG424 Tag Tool Menu")
        print("=" * 70)
        print(f"Tag: {uid_to_asset_tag(tag_state.uid)} (UID: {tag_state.uid.hex().upper()})")

        if tag_state.in_database:
            status = tag_state.keys.status if tag_state.keys else "unknown"
            print(f"Database: {status}")
        else:
            print("Database: Not found")

        print("=" * 70)
        print("Tools:")
        print()

        # Build tool availability info
        tool_info: list[tuple[Tool, int, bool, str | None]] = []
        num_available = 0
        for i, tool in enumerate(self.tools):
            result = tool.is_available(tag_state)
            if result is True:
                tool_info.append((tool, i, True, None))
                num_available += 1
                log.debug(f"Tool available: {tool.name}")
            else:
                is_available, reason = result  # type: ignore[misc]
                tool_info.append((tool, i, is_available, reason))
                log.debug(f"Tool unavailable: {tool.name} - {reason}")

        # Display all tools with availability status
        menu_number = 1
        for tool, _idx, is_available, reason in tool_info:
            if is_available:
                print(f"  {menu_number}. {tool.name}")
                print(f"     {tool.description}")
                menu_number += 1
            else:
                print(f"  X. {tool.name}")
                print(f"     {tool.description}")
                if reason:
                    print(f"     ⚠️  Requires: {reason}")

        print()
        print("  q. Quit")
        print("=" * 70)

        # Build mapping of menu numbers to tool indices
        number_to_idx = {}
        menu_num = 1
        for _tool, idx, is_available, _reason in tool_info:
            if is_available:
                number_to_idx[menu_num] = idx
                menu_num += 1

        while True:
            choice = input("Select tool: ").strip().lower()

            if choice == "q":
                return "quit"

            try:
                selected_num = int(choice)
                if selected_num in number_to_idx:
                    return number_to_idx[selected_num]
                else:
                    print(f"Invalid choice. Enter 1-{num_available} or 'q'")
            except ValueError:
                print("Invalid input. Enter a number or 'q'")

    def _display_result_details(self, tool_name: str, details: dict):
        """Display tool result details with custom formatting per tool."""
        # Diagnostics tool - special formatting
        if tool_name == "Show Diagnostics":
            self._display_diagnostics(details)
            return

        # Default formatting for simple tools
        print()
        for key, value in details.items():
            display_key = key.replace("_", " ").title()

            # Handle different value types
            if isinstance(value, bool):
                print(f"  {display_key}: {'Yes' if value else 'No'}")
            elif isinstance(value, str) and len(value) > 500:
                print(f"  {display_key}: {value[:500]}...")
            else:
                print(f"  {display_key}: {value}")

    def _display_diagnostics(self, diagnostics: dict):
        """Display diagnostics with structured formatting."""
        print()

        # Chip info
        if "chip" in diagnostics:
            print("Chip Information:")
            chip = diagnostics["chip"]
            if "error" in chip:
                print(f"  Error: {chip['error']}")
            else:
                for key, value in chip.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            print()

        # Database status
        if "database" in diagnostics:
            print("Database Status:")
            for key, value in diagnostics["database"].items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
            print()

        # Key versions
        if "key_versions" in diagnostics:
            print("Key Versions:")
            for key, value in diagnostics["key_versions"].items():
                print(f"  {key.upper()}: {value}")
            print()

        # File settings
        if "file_settings" in diagnostics:
            print("File Settings (File 02 - NDEF):")
            settings_str = diagnostics["file_settings"]
            for line in settings_str.split("\n"):
                if line.strip():
                    print(f"  {line}")
            print()

        # CC File
        if "cc_file" in diagnostics:
            print("Capability Container (CC) File:")
            cc = diagnostics["cc_file"]
            if "error" in cc:
                print(f"  Error: {cc['error']}")
            else:
                for key, value in cc.items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            print()

        # NDEF
        if "ndef" in diagnostics:
            print("NDEF File:")
            ndef = diagnostics["ndef"]
            if "error" in ndef:
                print(f"  Error: {ndef['error']}")
            else:
                print(f"  Length: {ndef['length']} bytes")
                if "preview" in ndef:
                    preview = ndef["preview"]
                    # Format as hex blocks
                    for i in range(0, min(len(preview), 128), 64):
                        print(f"    {preview[i : i + 64]}")
            print()

        # Backups
        if "backups" in diagnostics:
            print("Backups:")
            backups = diagnostics["backups"]
            print(f"  Total: {backups.get('total', 0)}")
            print(f"  Successful: {'Yes' if backups.get('has_successful') else 'No'}")

    def _run_tool(self, tool, tag_state: TagState, card: NTag424CardConnection):
        """Run a tool with centralized I/O handling.

        Handles: confirmation, execution, result display, error handling.
        """
        print(f"\n{'=' * 70}")
        print(f"Executing: {tool.name}")
        print("=" * 70)
        print()

        # Check if confirmation needed
        confirmation = tool.get_confirmation_request(tag_state)
        if confirmation:
            print(confirmation.title)
            print()
            for item in confirmation.items:
                print(f"  - {item}")
            print()

            # Get confirmation (respects --yes flag via stdin check)
            if sys.stdin.isatty():
                response = input("Continue? (y/n): ").strip().lower()
                if response not in ["y", "yes"]:
                    print("Cancelled.")
                    return
            else:
                print("Continue? (y/n): y (auto-confirmed)")

        # Execute tool
        try:
            result = tool.execute(tag_state, card, self.key_mgr)

            # Display result
            print()
            if result.success:
                print(f"[SUCCESS] {result.message}")
                log.info(f"✅ {tool.name} completed successfully")
            else:
                print(f"[COMPLETED] {result.message}")
                log.warning(f"⚠️  {tool.name} completed with warnings")

            # Display details based on tool type
            if result.details:
                self._display_result_details(tool.name, result.details)

            print("=" * 70)

        except Exception as e:
            log.exception(f"❌ {tool.name} failed: {e}")
            print(f"\n[FAILED] {tool.name}")
            print(f"  Error: {e}")
            print()
            print("Troubleshooting:")
            print("  - Check keys in database are correct")
            print("  - Verify tag is not rate-limited (wait 60s if needed)")
            print("  - Try running Diagnostics tool to check tag state")
            print("=" * 70)

    def run(self):
        """Main loop: connect → assess → menu → execute → repeat.

        Fresh connection for each operation. Allows tag swapping,
        rate limit recovery, and clean state between tools.
        """
        print("\n" + "=" * 70)
        print("NTAG424 Tag Tool")
        print("=" * 70)
        print("Place tag on reader to begin")
        print()
        input("Press Enter when ready...")

        while True:
            try:
                # Fresh connection per operation
                with self._connect_to_tag() as card:
                    # Assess current tag state
                    tag_state = self._assess_tag_state(card)

                    # Show menu and get choice (menu filters internally)
                    choice = self._show_menu(tag_state)

                    if choice == "quit":
                        print("\nExiting...")
                        break

                    if isinstance(choice, int):
                        # Execute chosen tool (choice is already the tool index)
                        tool = self.tools[choice]

                        # Run tool with centralized I/O handling
                        self._run_tool(tool, tag_state, card)

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break

            except Exception as e:
                log.error(f"Error in main loop: {e}")
                print(f"\n❌ Error: {e}")
                print("Remove/replace tag and try again")

            # Wait for user before next operation
            print("\n" + "=" * 70)
            response = input("Press Enter for next operation (or 'q' to quit): ").strip().lower()
            if response == "q":
                print("\nExiting...")
                break

        print("\nGoodbye!")
