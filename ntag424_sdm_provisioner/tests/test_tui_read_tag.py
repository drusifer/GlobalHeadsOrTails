import pytest

from ntag424_sdm_provisioner.tui.app import NtagProvisionerApp


@pytest.mark.asyncio
async def test_read_tag_navigation():
    """Test navigation to Read Tag screen."""
    app = NtagProvisionerApp()
    async with app.run_test() as pilot:
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
async def test_read_tag_screen_elements():
    """Test read tag screen has required elements."""
    app = NtagProvisionerApp()
    async with app.run_test() as pilot:
        # Navigate to screen
        await pilot.click("#btn_read")
        
        # Verify required elements exist
        assert app.screen.query_one("#btn_scan")
        assert app.screen.query_one("#status_label")
        assert app.screen.query_one("#log_view")
