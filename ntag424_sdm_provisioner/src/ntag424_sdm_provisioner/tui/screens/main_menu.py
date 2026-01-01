from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Rule, Static


class MainMenu(Screen):
    """The main menu screen."""

    def compose(self):
        yield Header()
        yield Container(
            Static("NTAG424 PROVISIONER", id="title"),
            Vertical(
                # Two-phase provisioning
                Static("Provisioning:", classes="section-header"),
                Button("1. Configure Keys", id="btn_configure_keys", variant="primary"),
                Button("2. Setup URL", id="btn_setup_url", variant="primary"),
                Rule(),
                # Diagnostics & Recovery
                Button("Read Tag (Diagnostics)", id="btn_read"),
                Button("Recover Lost Keys", id="btn_key_recovery"),
                Button("Format PICC (Factory Reset)", id="btn_format_picc", variant="error"),
                Rule(),
                Button("Quit", id="btn_quit", variant="error"),
                classes="box",
            ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_configure_keys":
            self.app.push_screen("configure_keys")
        elif event.button.id == "btn_setup_url":
            self.app.push_screen("setup_url")
        elif event.button.id == "btn_read":
            self.app.push_screen("read_tag")
        elif event.button.id == "btn_key_recovery":
            self.app.push_screen("key_recovery")
        elif event.button.id == "btn_format_picc":
            self.app.push_screen("format_picc")
        elif event.button.id == "btn_quit":
            self.app.exit()
