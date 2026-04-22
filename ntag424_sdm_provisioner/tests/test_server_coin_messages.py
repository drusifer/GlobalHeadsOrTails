"""Integration tests for §14 Custom Coin Messages — CoinMessageService and POST /api/coin/messages."""
import shutil
from pathlib import Path

import pytest

from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, Outcome, TagKeys, UID
from ntag424_sdm_provisioner.server.app import create_app
from ntag424_sdm_provisioner.server.coin_message_service import CoinMessageService


COIN_A = "HAPPY-HAWK-001"
UID_A_HEADS = "0401000000001A"
UID_A_TAILS = "0401000000001B"


@pytest.fixture
def svc(tmp_path):
    db = tmp_path / "test.db"
    return CoinMessageService(db_path=str(db))


@pytest.fixture
def app_ctx(tmp_path):
    db_path = tmp_path / "test.db"
    key_csv = tmp_path / "keys.csv"
    km = CsvKeyManager(csv_path=str(key_csv))
    km.save_tag_keys(TagKeys(
        uid=UID(UID_A_HEADS), outcome=Outcome.HEADS, coin_name=COIN_A,
        picc_master_key="0" * 32, app_read_key="0" * 32, sdm_mac_key="0" * 32,
    ))
    km.save_tag_keys(TagKeys(
        uid=UID(UID_A_TAILS), outcome=Outcome.TAILS, coin_name=COIN_A,
        picc_master_key="0" * 32, app_read_key="0" * 32, sdm_mac_key="0" * 32,
    ))
    app = create_app(key_csv_path=str(key_csv), db_path=str(db_path))
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client, app.coin_message_service


def api_flip(client, uid: str, ctr: int, outcome: str):
    return client.get(f"/api/flip?uid={uid}&ctr={ctr:08x}&cmac=DEADBEEF&drew_test_outcome={outcome}")


# --- CoinMessageService unit tests ---

def test_get_messages_returns_empty_strings_when_not_set(svc):
    h, t = svc.get_messages("UNKNOWN-COIN")
    assert h == ""
    assert t == ""


def test_set_and_get_messages_roundtrip(svc):
    svc.set_messages("COIN-1", "YES!", "NOPE")
    h, t = svc.get_messages("COIN-1")
    assert h == "YES!"
    assert t == "NOPE"


def test_set_messages_strips_whitespace(svc):
    svc.set_messages("COIN-2", "  Hi  ", "  Bye  ")
    h, t = svc.get_messages("COIN-2")
    assert h == "Hi"
    assert t == "Bye"


def test_set_messages_upsert_overwrites(svc):
    svc.set_messages("COIN-3", "First", "First")
    svc.set_messages("COIN-3", "Second", "Second")
    h, t = svc.get_messages("COIN-3")
    assert h == "Second"
    assert t == "Second"


def test_set_messages_clears_with_empty_string(svc):
    svc.set_messages("COIN-4", "Custom", "Other")
    svc.set_messages("COIN-4", "", "")
    h, t = svc.get_messages("COIN-4")
    assert h == ""
    assert t == ""


def test_emoji_stored_and_retrieved_correctly(svc):
    svc.set_messages("COIN-5", "🎉 YES!", "😢 NO")
    h, t = svc.get_messages("COIN-5")
    assert h == "🎉 YES!"
    assert t == "😢 NO"


# --- validate_tap_auth ---

def test_validate_tap_auth_returns_false_with_no_scan_history(app_ctx):
    _, svc = app_ctx
    assert svc.validate_tap_auth(COIN_A, "DEADBEEF", "00000001") is False


def test_validate_tap_auth_returns_true_after_flip(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    assert svc.validate_tap_auth(COIN_A, "DEADBEEF", "00000001") is True


def test_validate_tap_auth_returns_false_wrong_cmac(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    assert svc.validate_tap_auth(COIN_A, "WRONGCMAC", "00000001") is False


def test_validate_tap_auth_returns_false_wrong_counter(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    assert svc.validate_tap_auth(COIN_A, "DEADBEEF", "00000002") is False


def test_validate_tap_auth_invalid_ctr_hex_returns_false(app_ctx):
    _, svc = app_ctx
    assert svc.validate_tap_auth(COIN_A, "DEADBEEF", "NOTAHEX") is False


# --- POST /api/coin/messages route ---

def test_set_coin_messages_requires_auth(app_ctx):
    client, _ = app_ctx
    resp = client.post("/api/coin/messages", json={
        "coin_name": COIN_A, "cmac": "DEADBEEF", "ctr": "00000001",
        "heads_message": "GO!", "tails_message": "No!",
    })
    assert resp.status_code == 401
    assert resp.get_json()["error"] == "auth_failed"


def test_set_coin_messages_saves_after_valid_tap(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    resp = client.post("/api/coin/messages", json={
        "coin_name": COIN_A, "cmac": "DEADBEEF", "ctr": "00000001",
        "heads_message": "WINNER!", "tails_message": "loser",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["heads_message"] == "WINNER!"
    assert data["tails_message"] == "loser"
    h, t = svc.get_messages(COIN_A)
    assert h == "WINNER!"
    assert t == "loser"


def test_set_coin_messages_missing_fields_returns_400(app_ctx):
    client, _ = app_ctx
    resp = client.post("/api/coin/messages", json={"coin_name": COIN_A})
    assert resp.status_code == 400


def test_set_coin_messages_rejects_message_over_50_chars(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    long_msg = "A" * 51
    resp = client.post("/api/coin/messages", json={
        "coin_name": COIN_A, "cmac": "DEADBEEF", "ctr": "00000001",
        "heads_message": long_msg, "tails_message": "OK",
    })
    assert resp.status_code == 400
    assert "50" in resp.get_json()["error"]


def test_set_coin_messages_accepts_emoji_within_limit(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    emoji_msg = "🎉" * 50
    resp = client.post("/api/coin/messages", json={
        "coin_name": COIN_A, "cmac": "DEADBEEF", "ctr": "00000001",
        "heads_message": emoji_msg, "tails_message": "",
    })
    assert resp.status_code == 200


def test_api_flip_response_includes_messages(app_ctx):
    client, svc = app_ctx
    api_flip(client, UID_A_HEADS, 1, "heads")
    svc.set_messages(COIN_A, "Custom Head", "Custom Tail")
    resp = api_flip(client, UID_A_HEADS, 2, "heads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["heads_message"] == "Custom Head"
    assert data["tails_message"] == "Custom Tail"


def test_api_flip_response_messages_empty_when_not_set(app_ctx):
    client, _ = app_ctx
    resp = api_flip(client, UID_A_HEADS, 1, "heads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["heads_message"] == ""
    assert data["tails_message"] == ""
