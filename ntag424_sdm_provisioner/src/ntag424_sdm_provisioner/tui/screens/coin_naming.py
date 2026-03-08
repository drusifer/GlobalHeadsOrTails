from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Rule, Static

from ntag424_sdm_provisioner.csv_key_manager import (
    CsvKeyManager,
    Outcome,
    generate_coin_name,
)
from ntag424_sdm_provisioner.uid_utils import UID


class CoinNamingScreen(Screen):
    """Assign a coin name and HEADS/TAILS outcomes to two provisioned tags.

    No APDU communication - only updates tag_keys.csv.
    """

    CSS = """
    #tag_list {
        height: auto;
        max-height: 16;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
        overflow-y: auto;
    }

    .tag_row {
        height: 3;
    }

    .tag_uid_label {
        width: 1fr;
        content-align: left middle;
        padding: 0 1;
    }

    .btn_heads {
        width: 10;
        min-width: 10;
        background: #1a4d1a;
    }

    .btn_heads_selected {
        width: 10;
        min-width: 10;
        background: #00bb00;
        color: white;
        text-style: bold;
    }

    .btn_tails {
        width: 10;
        min-width: 10;
        background: #5a3000;
    }

    .btn_tails_selected {
        width: 10;
        min-width: 10;
        background: #cc7700;
        color: white;
        text-style: bold;
    }

    #assignment_box {
        border: tall $primary;
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
    }

    #heads_label {
        height: 1;
    }

    #tails_label {
        height: 1;
        margin-bottom: 1;
    }

    #coin_name_display {
        height: 2;
        color: $accent;
        text-style: bold;
        content-align: left middle;
    }

    #btn_new_name {
        width: 24;
        height: 3;
        margin-top: 1;
    }

    #action_row {
        height: 3;
    }

    #btn_assign {
        width: 1fr;
    }

    #btn_clear {
        width: 1fr;
    }

    #error_label {
        background: darkred;
        color: white;
        padding: 0 2;
        height: 1;
        display: none;
    }

    #error_label.visible {
        display: block;
    }

    #success_label {
        background: darkgreen;
        color: white;
        padding: 0 2;
        height: 1;
        display: none;
    }

    #success_label.visible {
        display: block;
    }
    """

    def __init__(self, key_manager: CsvKeyManager, **kwargs):
        super().__init__(**kwargs)
        self.key_manager = key_manager
        self._heads_uid: str | None = None
        self._tails_uid: str | None = None
        self._coin_name: str = generate_coin_name()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label("Assign Coin Names", id="title"),
            Label("Select HEADS and TAILS for each coin, then click Assign:", id="instructions"),
            Vertical(id="tag_list"),
            Rule(),
            Vertical(
                Label("", id="heads_label"),
                Label("", id="tails_label"),
                Label("", id="coin_name_display"),
                Button("New Name", id="btn_new_name", variant="default"),
                id="assignment_box",
            ),
            Label("", id="error_label"),
            Label("", id="success_label"),
            Horizontal(
                Button("Assign Coin", id="btn_assign", variant="success"),
                Button("Clear", id="btn_clear", variant="default"),
                id="action_row",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Coin Naming"
        self._refresh_tag_list()
        self._refresh_assignment_display()

    def _get_unassigned_tags(self):
        return [t for t in self.key_manager.list_tags() if not t.coin_name]

    def _refresh_tag_list(self) -> None:
        tag_list = self.query_one("#tag_list", Vertical)
        tag_list.remove_children()
        tags = self._get_unassigned_tags()
        if not tags:
            tag_list.mount(Label("[dim]No unassigned tags.[/]"))
            return
        for tag in tags:
            uid = tag.uid.uid
            date = tag.provisioned_date[:10] if tag.provisioned_date else ""
            heads_sel = self._heads_uid == uid
            tails_sel = self._tails_uid == uid
            tag_list.mount(
                Horizontal(
                    Static(
                        f"[cyan]{uid}[/] [dim]{date}[/]",
                        classes="tag_uid_label",
                    ),
                    Button(
                        "✓ HEADS" if heads_sel else "HEADS",
                        id=f"btn_heads_{uid}",
                        classes="btn_heads_selected" if heads_sel else "btn_heads",
                    ),
                    Button(
                        "✓ TAILS" if tails_sel else "TAILS",
                        id=f"btn_tails_{uid}",
                        classes="btn_tails_selected" if tails_sel else "btn_tails",
                    ),
                    classes="tag_row",
                )
            )

    def _refresh_assignment_display(self) -> None:
        h = f"HEADS:  [green bold]{self._heads_uid}[/]" if self._heads_uid else "HEADS:  [dim]not selected[/]"
        t = f"TAILS:  [yellow bold]{self._tails_uid}[/]" if self._tails_uid else "TAILS:  [dim]not selected[/]"
        self.query_one("#heads_label", Label).update(h)
        self.query_one("#tails_label", Label).update(t)
        self.query_one("#coin_name_display", Label).update(f"Coin:  {self._coin_name}")

    def _clear_status(self) -> None:
        self.query_one("#error_label", Label).update("")
        self.query_one("#error_label").remove_class("visible")
        self.query_one("#success_label", Label).update("")
        self.query_one("#success_label").remove_class("visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        if btn_id.startswith("btn_heads_"):
            uid = btn_id[len("btn_heads_"):]
            if self._tails_uid == uid:
                self._tails_uid = None
            self._heads_uid = uid
            self._refresh_tag_list()
            self._refresh_assignment_display()
            self._clear_status()

        elif btn_id.startswith("btn_tails_"):
            uid = btn_id[len("btn_tails_"):]
            if self._heads_uid == uid:
                self._heads_uid = None
            self._tails_uid = uid
            self._refresh_tag_list()
            self._refresh_assignment_display()
            self._clear_status()

        elif btn_id == "btn_new_name":
            self._coin_name = generate_coin_name()
            self._refresh_assignment_display()

        elif btn_id == "btn_assign":
            self._assign_coin()

        elif btn_id == "btn_clear":
            self._heads_uid = None
            self._tails_uid = None
            self._coin_name = generate_coin_name()
            self._refresh_tag_list()
            self._refresh_assignment_display()
            self._clear_status()

    def _assign_coin(self) -> None:
        err = self.query_one("#error_label", Label)

        if not self._heads_uid or not self._tails_uid:
            err.update("Select both a HEADS and a TAILS tag before assigning.")
            err.add_class("visible")
            return

        if self._heads_uid == self._tails_uid:
            err.update("HEADS and TAILS must be different tags.")
            err.add_class("visible")
            return

        try:
            self.key_manager.assign_coin_name(UID(self._heads_uid), self._coin_name, Outcome.HEADS)
            self.key_manager.assign_coin_name(UID(self._tails_uid), self._coin_name, Outcome.TAILS)

            success = self.query_one("#success_label", Label)
            success.update(
                f"[bold]{self._coin_name}[/]  HEADS={self._heads_uid}  TAILS={self._tails_uid}"
            )
            success.add_class("visible")

            self._heads_uid = None
            self._tails_uid = None
            self._coin_name = generate_coin_name()
            self._refresh_tag_list()
            self._refresh_assignment_display()

        except ValueError as e:
            err.update(str(e))
            err.add_class("visible")
