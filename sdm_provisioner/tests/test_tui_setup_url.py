"""Unit tests for SetupUrlScreen quick presets (Flip Game URL vs Biz Card URL)."""
from unittest.mock import MagicMock
import pytest

from sdm_provisioner.constants import BIZ_CARD_BASE_URL, GAME_COIN_BASE_URL
from sdm_provisioner.service_key_manager import ServiceKeyManager
from sdm_provisioner.tui.app import NtagProvisionerApp
from textual.widgets import Button, Input


@pytest.fixture
def mock_km():
    km = MagicMock(spec=ServiceKeyManager)
    km.list_tags.return_value = []
    return km


@pytest.mark.asyncio
async def test_setup_url_screen_preset_buttons(mock_km):
    """Verify SetupUrlScreen provides preset buttons and toggles URL input correctly."""
    app = NtagProvisionerApp(key_manager=mock_km)
    async with app.run_test(size=(120, 40)) as pilot:
        # Navigate to Setup URL screen
        await pilot.click("#btn_setup_url")
        assert app.screen.id == "setup_url"

        url_input = app.screen.query_one("#url_input", Input)
        btn_flip = app.screen.query_one("#btn_preset_flip", Button)
        btn_biz = app.screen.query_one("#btn_preset_biz", Button)

        # Initial state should be Flip default
        assert url_input.value == GAME_COIN_BASE_URL
        assert btn_flip.variant == "primary"
        assert btn_biz.variant == "default"

        # Click Biz preset button
        await pilot.click("#btn_preset_biz")
        assert url_input.value == BIZ_CARD_BASE_URL
        assert url_input.value == "https://gs.works/contact"
        assert btn_biz.variant == "primary"
        assert btn_flip.variant == "default"

        # Click Flip preset button
        await pilot.click("#btn_preset_flip")
        assert url_input.value == GAME_COIN_BASE_URL
        assert btn_flip.variant == "primary"
        assert btn_biz.variant == "default"


@pytest.mark.asyncio
async def test_setup_url_screen_keyboard_actions(mock_km):
    """Verify action methods for selecting presets work on SetupUrlScreen."""
    app = NtagProvisionerApp(key_manager=mock_km)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#btn_setup_url")
        screen = app.screen
        url_input = screen.query_one("#url_input", Input)

        screen.action_select_preset_biz()
        assert url_input.value == BIZ_CARD_BASE_URL

        screen.action_select_preset_flip()
        assert url_input.value == GAME_COIN_BASE_URL


@pytest.mark.asyncio
async def test_setup_url_screen_input_changed_highlights(mock_km):
    """Verify typing custom or preset URLs reactively updates button styling."""
    app = NtagProvisionerApp(key_manager=mock_km)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#btn_setup_url")
        screen = app.screen
        url_input = screen.query_one("#url_input", Input)
        btn_flip = screen.query_one("#btn_preset_flip", Button)
        btn_biz = screen.query_one("#btn_preset_biz", Button)

        # Type custom URL
        url_input.value = "https://custom.example.com"
        await pilot.pause()
        assert btn_flip.variant == "default"
        assert btn_biz.variant == "default"

        # Type Biz URL
        url_input.value = BIZ_CARD_BASE_URL
        await pilot.pause()
        assert btn_biz.variant == "primary"
        assert btn_flip.variant == "default"

        # Type Flip URL
        url_input.value = GAME_COIN_BASE_URL
        await pilot.pause()
        assert btn_flip.variant == "primary"
        assert btn_biz.variant == "default"
