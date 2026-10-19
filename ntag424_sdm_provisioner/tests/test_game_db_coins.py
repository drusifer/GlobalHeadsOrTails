"""Tests for SQLite app.db coins table and tag validator client adapter."""

import tempfile
from pathlib import Path

from ntag424_sdm_provisioner.server.game_state_manager import SqliteGameStateManager
from ntag424_sdm_provisioner.server.tag_validator_client import validate_tag_remotely


def test_coins_table_and_identity_decoupling():
    """Verify first-class coin identity storage in app.db decoupled from key service."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "app.db"
        gm = SqliteGameStateManager(db_path=str(db_path))

        # Assign coin identity directly into app.db
        gm.set_coin("04DEADBEEF0001", "MYSTIC-PHOENIX", clan="Ember", rarity="rare")

        # Read back identity
        coin = gm.get_coin("04DEADBEEF0001")
        assert coin is not None
        assert coin["coin_name"] == "MYSTIC-PHOENIX"
        assert coin["clan"] == "Ember"
        assert coin["rarity"] == "rare"

        # get_state resolves coin_name even before scan_logs exist
        state = gm.get_state("04DEADBEEF0001")
        assert state.coin_name == "MYSTIC-PHOENIX"

        # Log a scan and ensure outcome and counter update properly
        gm.update_state("04DEADBEEF0001", counter=1, outcome="heads", coin_name="MYSTIC-PHOENIX")
        state_after = gm.get_state("04DEADBEEF0001")
        assert state_after.last_counter == 1
        assert state_after.outcome == "heads"
        assert state_after.coin_name == "MYSTIC-PHOENIX"


def test_tag_validator_client_offline_fallback():
    """Verify client adapter returns structured error response when key service is offline."""
    result = validate_tag_remotely(
        uid="04B7664A2F7080",
        counter=1,
        cmac="C099B6D1E57E1F4F",
        service_url="http://127.0.0.1:59999",  # unreachable port
        timeout_sec=0.5,
    )
    assert result["valid"] is False
    assert "error" in result
    assert result["uid"] == "04B7664A2F7080"
