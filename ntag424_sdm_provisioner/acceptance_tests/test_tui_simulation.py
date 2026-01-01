import os
import pytest
from textual.pilot import Pilot
from ntag424_sdm_provisioner.tui.app import NtagProvisionerApp

@pytest.mark.asyncio
async def test_tui_simulation_mode(tmp_path):
    """Test that TUI uses simulator when env var is set."""
    # Set simulation env var
    os.environ["NTAG_SIMULATION"] = "1"
    
    # Create a temporary log file for this test run
    log_file = tmp_path / "test_tui.log"
    
    # Pass the log file path to the app to avoid polluting the project directory
    app = NtagProvisionerApp(log_file=str(log_file))
    async with app.run_test() as pilot:
        # Navigate to Read Tag screen by clicking its button.
        # This is more robust than using keyboard navigation.
        await pilot.click('Button:contains("Read Tag")')
        await pilot.pause()  # Wait for screen to change
        
        # Click Scan Tag
        await pilot.click("#btn_scan")
        await pilot.pause(2.0)  # Wait for worker to write to log
        
        # Check logs for simulation evidence
        # We verify that the log file contains the expected simulation output
        with open(log_file, "r") as f:
            log_content = f.read()
            
        assert "Version:" in log_content
        assert "Using SIMULATED card connection" in log_content
        
    # Clean up
    del os.environ["NTAG_SIMULATION"]
