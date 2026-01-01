import logging
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from textual.app import App
from textual.binding import BindingType

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.tui.screens.configure_keys import ConfigureKeysScreen
from ntag424_sdm_provisioner.tui.screens.format_picc import FormatPICCScreen
from ntag424_sdm_provisioner.tui.screens.key_recovery import KeyRecoveryScreen
from ntag424_sdm_provisioner.tui.screens.main_menu import MainMenu
from ntag424_sdm_provisioner.tui.screens.read_tag import ReadTagScreen
from ntag424_sdm_provisioner.tui.screens.setup_url import SetupUrlScreen


class NtagProvisionerApp(App):
    """A Textual app for NTAG424 DNA Provisioning.

    Uses a single CsvKeyManager instance shared across all screens
    for consistent key lookups and storage.
    """

    CSS = """
    Screen {
        background: $surface;
    }
    
    #title {
        color: $accent;
        text-style: bold;
        text-align: center;
        margin: 1;
    }

    Button {
        width: 100%;
        margin: 1 0;
        background: $panel;
        color: $text;
        border: tall $accent;
    }

    Button:hover {
        background: $accent;
        color: $surface;
    }
    
    .box {
        height: 100%;
        width: 100%;
        align: center middle;
        padding: 2;
    }
    
    /* Error display styling */
    #error_label {
        background: darkred;
        color: white;
        text-style: bold;
        padding: 1 2;
        margin: 1 0;
        text-align: center;
        display: none;
    }
    
    #error_label.visible {
        display: block;
    }
    
    /* Success display styling */
    #success_label {
        background: darkgreen;
        color: white;
        text-style: bold;
        padding: 1 2;
        margin: 1 0;
        text-align: center;
        display: none;
    }
    
    #success_label.visible {
        display: block;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("q", "quit", "Quit"),
        ("m", "switch_mode('menu')", "Main Menu"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, log_file: str | None = None, **kwargs):
        super().__init__(**kwargs)

        # Detect project root to ensure consistent file paths regardless of CWD
        # Walk up to find the project root (contains tag_keys.csv or ntag424_sdm_provisioner/)
        project_root = Path.cwd()
        while project_root.parent != project_root:
            if (project_root / "tag_keys.csv").exists() or (project_root / "ntag424_sdm_provisioner").exists():
                break
            project_root = project_root.parent

        # Configure logging. If a log_file is passed (e.g., from a test), use it.
        # Otherwise, create a new timestamped log file in project root.
        if log_file is None:
            _log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = str(project_root / f"tui_{_log_timestamp}.log")
        else:
            self.log_file = log_file

        # Force-remove any existing handlers from the root logger to ensure
        # test isolation and prevent log pollution from other modules.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        logging.basicConfig(
            filename=self.log_file,
            level=logging.DEBUG,
            filemode="w",
            format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            force=True,
        )

        # Single KeyManager instance shared across all screens
        # Use absolute paths based on project root
        self.key_manager = CsvKeyManager(
            csv_path=str(project_root / "tag_keys.csv"),
            backup_path=str(project_root / "tag_keys_backup.csv"),
            timestamped_backup_dir=str(project_root / "tag_keys_backups"),
        )
        log = logging.getLogger(__name__)
        log.info(f"KeyManager initialized with {len(self.key_manager.list_tags())} registered tags")

    def on_mount(self) -> None:
        # Pass key_manager to screens that need it
        self.install_screen(MainMenu(id="menu"), name="menu")
        self.install_screen(
            ConfigureKeysScreen(key_manager=self.key_manager, id="configure_keys"),
            name="configure_keys",
        )
        self.install_screen(
            SetupUrlScreen(key_manager=self.key_manager, id="setup_url"), name="setup_url"
        )
        self.install_screen(
            ReadTagScreen(key_manager=self.key_manager, id="read_tag"), name="read_tag"
        )
        self.install_screen(
            KeyRecoveryScreen(key_manager=self.key_manager, id="key_recovery"),
            name="key_recovery",
        )
        self.install_screen(
            FormatPICCScreen(key_manager=self.key_manager, id="format_picc"),
            name="format_picc",
        )
        self.push_screen("menu")

    async def action_switch_mode(self, mode: str) -> None:
        await self.push_screen(mode)

    async def action_go_back(self) -> None:
        """Go back to previous screen (pop current screen)."""
        if len(self.screen_stack) > 1:
            self.pop_screen()


if __name__ == "__main__":
    app = NtagProvisionerApp()
    app.run()
