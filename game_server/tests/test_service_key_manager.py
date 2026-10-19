"""Unit and integration tests for ServiceKeyManager."""

from unittest.mock import patch

import pytest

from game_server.csv_key_manager import UID, CsvKeyManager, Outcome, TagKeys
from game_server.app import create_app
from game_server.service_key_manager import ServiceKeyManager


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated SQLite DB path."""
    db_file = tmp_path / "test_app.db"
    return str(db_file)


class TestServiceKeyManagerInit:
    def test_init_defaults(self, temp_db):
        km = ServiceKeyManager(service_url="http://localhost:8080", db_path=temp_db)
        assert km.service_url == "http://localhost:8080"
        assert km.db_path.name == "test_app.db"

    def test_init_env_var_tag_validator_url(self, temp_db, monkeypatch):
        monkeypatch.setenv("TAG_VALIDATOR_URL", "http://validator.local:8080/")
        km = ServiceKeyManager(db_path=temp_db)
        assert km.service_url == "http://validator.local:8080"

    def test_init_env_var_key_service_url(self, temp_db, monkeypatch):
        monkeypatch.delenv("TAG_VALIDATOR_URL", raising=False)
        monkeypatch.setenv("KEY_SERVICE_URL", "http://vault.local:9000/")
        km = ServiceKeyManager(db_path=temp_db)
        assert km.service_url == "http://vault.local:9000"

    def test_invalid_scheme(self, temp_db):
        with pytest.raises(ValueError, match="Invalid service_url"):
            ServiceKeyManager(service_url="ftp://invalid", db_path=temp_db)


class TestServiceKeyManagerValidation:
    @patch("game_server.service_key_manager.validate_tag_remotely")
    def test_validate_sdm_url_success(self, mock_validate, temp_db):
        mock_validate.return_value = {
            "valid": True,
            "uid": "04AE664A2F7080",
            "counter": 12,
            "cmac_calculated": "A1B2C3D4E5F67890",
            "error": None,
        }
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)
        res = km.validate_sdm_url("04AE664A2F7080", 12, "A1B2C3D4E5F67890")

        assert res["valid"] is True
        assert res["uid"] == UID("04AE664A2F7080")
        assert res["counter"] == 12
        assert res["cmac_calculated"] == "A1B2C3D4E5F67890"
        assert res["error"] is None

    @patch("game_server.service_key_manager.validate_tag_remotely")
    def test_validate_sdm_url_failure(self, mock_validate, temp_db):
        mock_validate.return_value = {
            "valid": False,
            "uid": "04AE664A2F7080",
            "counter": 12,
            "cmac_calculated": "0000000000000000",
            "error": "CMAC mismatch",
        }
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)
        res = km.validate_sdm_url(UID("04AE664A2F7080"), 12, "FFFFFFFFFFFFFFFF")

        assert res["valid"] is False
        assert res["error"] == "CMAC mismatch"


class TestServiceKeyManagerKeyCustodyAndDomain:
    def test_get_tag_keys_with_app_db_metadata(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)
        # Seed coin metadata into app.db
        km.game_manager.set_coin("04AE664A2F7080", "CYBER-DRAGON", outcome="heads")

        with patch.object(km, "_http_request") as mock_http:
            mock_http.return_value = (200, {
                "uid": "04AE664A2F7080",
                "status": "active",
                "k3_masked": "1234567890ABCDEF...",
            })

            tag_keys = km.get_tag_keys("04AE664A2F7080")

            assert tag_keys.uid.uid == "04AE664A2F7080"
            assert tag_keys.coin_name == "CYBER-DRAGON"
            assert tag_keys.outcome == Outcome.HEADS
            assert tag_keys.status == "active"
            assert tag_keys.sdm_mac_key == "1234567890ABCDEF..."

    def test_get_tag_keys_factory_404(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)

        with patch.object(km, "_http_request") as mock_http:
            mock_http.return_value = (404, {"error": "Not found"})

            tag_keys = km.get_tag_keys("04AE664A2F7080")
            assert tag_keys.status == "factory"
            assert tag_keys.coin_name == ""
            assert tag_keys.outcome == Outcome.INVALID

    def test_generate_random_keys(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)

        with patch.object(km, "_http_request") as mock_http:
            mock_http.return_value = (201, {
                "status": "created",
                "uid": "04AE664A2F7080",
                "k3": "0123456789ABCDEF0123456789ABCDEF",
            })

            tag_keys = km.generate_random_keys(
                "04AE664A2F7080",
                coin_name="TITANIUM-TIGER",
                outcome=Outcome.HEADS,
            )

            assert tag_keys.uid.uid == "04AE664A2F7080"
            assert tag_keys.coin_name == "TITANIUM-TIGER"
            assert tag_keys.outcome == Outcome.HEADS
            assert tag_keys.sdm_mac_key == "0123456789ABCDEF0123456789ABCDEF"
            assert tag_keys.status == "provisioned"

            # Check local app.db recorded the coin identity
            coin_rec = km.game_manager.get_coin("04AE664A2F7080")
            assert coin_rec is not None
            assert coin_rec["coin_name"] == "TITANIUM-TIGER"
            assert coin_rec["outcome"] == "heads"

            # Check cached raw key for burning
            assert km.get_key("04AE664A2F7080", 2) == bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")
            assert km.get_key("04AE664A2F7080", 0) == b"\x00" * 16

    def test_save_tag_keys(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)
        tk = TagKeys(
            uid=UID("04AE664A2F7080"),
            picc_master_key="0" * 32,
            app_read_key="0" * 32,
            sdm_mac_key="A" * 32,
            coin_name="GOLDEN-GOOSE",
            outcome=Outcome.TAILS,
        )

        with patch.object(km, "_http_request") as mock_http:
            mock_http.return_value = (201, {"status": "created"})
            success = km.save_tag_keys(tk)

            assert success is True
            coin_rec = km.game_manager.get_coin("04AE664A2F7080")
            assert coin_rec["coin_name"] == "GOLDEN-GOOSE"
            assert coin_rec["outcome"] == "tails"

    def test_delete_and_undelete_key(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)

        with patch.object(km, "_http_request") as mock_http:
            mock_http.return_value = (200, {"status": "deleted"})
            assert km.delete_key("04AE664A2F7080") is True

            mock_http.return_value = (200, {"status": "restored"})
            assert km.undelete_key("04AE664A2F7080") is True

    def test_assign_coin_name_and_outcome(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)

        with patch.object(km, "list_tags", return_value=[]):
            km.assign_coin_name("04AE664A2F7080", "PHOENIX-FIRE", Outcome.HEADS)

        coin_rec = km.game_manager.get_coin("04AE664A2F7080")
        assert coin_rec["coin_name"] == "PHOENIX-FIRE"
        assert coin_rec["outcome"] == "heads"

    def test_assign_coin_name_duplicate_rejected(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)

        existing = TagKeys(
            uid=UID("04AE664A2F7080"),
            picc_master_key="0" * 32,
            app_read_key="0" * 32,
            sdm_mac_key="0" * 32,
            coin_name="PHOENIX-FIRE",
            outcome=Outcome.HEADS,
        )
        with patch.object(km, "list_tags", return_value=[existing]):
            with pytest.raises(ValueError, match="already has a heads tag"):
                km.assign_coin_name("04AE664A2F7081", "PHOENIX-FIRE", Outcome.HEADS)

    def test_list_tags_and_coins(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)

        # Seed coins in db
        km.game_manager.set_coin("04000000000001", "TWIN-STARS", outcome="heads")
        km.game_manager.set_coin("04000000000002", "TWIN-STARS", outcome="tails")

        def fake_http(_method, path, _body=None):
            if path == "/api/v1/keys":
                return 200, {"uids": ["04000000000001", "04000000000002"]}
            if "/api/v1/keys/04000000000001" in path:
                return 200, {"status": "active", "k3_masked": "1111..."}
            if "/api/v1/keys/04000000000002" in path:
                return 200, {"status": "active", "k3_masked": "2222..."}
            return 404, {}

        with patch.object(km, "_http_request", side_effect=fake_http):
            tags = km.list_tags()
            assert len(tags) == 2

            coin_tags = km.get_coin_tags("TWIN-STARS")
            assert coin_tags["heads"] is not None
            assert coin_tags["tails"] is not None

            val = km.validate_coin("TWIN-STARS")
            assert val["complete"] is True

            coins = km.list_coins()
            assert "TWIN-STARS" in coins
            assert coins["TWIN-STARS"]["complete"] is True

    def test_healthz(self, temp_db):
        km = ServiceKeyManager(service_url="http://test-service", db_path=temp_db)
        with patch.object(km, "_http_request", return_value=(200, {"status": "ok"})):
            assert km.is_healthy() is True

        with patch.object(km, "_http_request", return_value=(503, {"error": "down"})):
            assert km.is_healthy() is False


class TestServerIntegrationWithServiceKeyManager:
    def test_create_app_uses_service_key_manager_when_configured(self, temp_db):
        app = create_app(
            db_path=temp_db,
            service_url="http://remote-key-service:8080",
        )
        assert isinstance(app.key_manager, ServiceKeyManager)
        assert app.key_manager.service_url == "http://remote-key-service:8080"

    def test_create_app_falls_back_to_csv_key_manager_by_default(self, temp_db, monkeypatch):
        monkeypatch.delenv("TAG_VALIDATOR_URL", raising=False)
        monkeypatch.delenv("KEY_SERVICE_URL", raising=False)
        app = create_app(db_path=temp_db)
        assert isinstance(app.key_manager, CsvKeyManager)
