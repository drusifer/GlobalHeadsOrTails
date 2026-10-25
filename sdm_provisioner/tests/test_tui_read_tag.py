from unittest.mock import MagicMock
import pytest

from sdm_provisioner.service_key_manager import ServiceKeyManager
from sdm_provisioner.tui.app import NtagProvisionerApp


@pytest.fixture
def mock_km():
    km = MagicMock(spec=ServiceKeyManager)
    km.list_tags.return_value = []
    return km


@pytest.mark.asyncio
async def test_read_tag_navigation(mock_km):
    """Test navigation to Read Tag screen."""
    app = NtagProvisionerApp(key_manager=mock_km)
    async with app.run_test(size=(120, 40)) as pilot:
        # Check initial state
        assert app.screen.id == "menu"
        
        # Click Read Tag Button
        await pilot.click("#btn_read")
        
        # Check transition
        assert app.screen.id == "read_tag"
        assert app.screen.query_one("#btn_scan")
        
        # Use escape or key binding to go back (no back button in this screen)
        await pilot.press("escape")
        
        # Check return to menu
        assert app.screen.id == "menu"


@pytest.mark.asyncio
async def test_read_tag_screen_elements(mock_km):
    """Test read tag screen has required elements."""
    app = NtagProvisionerApp(key_manager=mock_km)
    async with app.run_test(size=(120, 40)) as pilot:
        # Navigate to screen
        await pilot.click("#btn_read")
        
        # Verify required elements exist
        assert app.screen.query_one("#btn_scan")
        assert app.screen.query_one("#status_label")
        assert app.screen.query_one("#log_view")
