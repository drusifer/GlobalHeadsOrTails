"""TDD tests for STORY-GSW-12 (/api/vip/validate and /api/vip/send with ntfy.sh)."""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from Crypto.Cipher import AES
from Crypto.Hash import CMAC

from game_server.csv_key_manager import (
    CsvKeyManager,
    Outcome,
    TagKeys,
    UID,
    build_system_vector,
    calculate_cmac_full,
    truncate_cmac,
)
from game_server.app import create_app

CONTACT_UID = "043F13E2151990"
CONTACT_SDM_MAC_KEY = "99e88808adc7885bc7065d739a25e1d0"


def _compute_valid_cmac(uid_hex: str, counter: int, sdm_mac_key_hex: str) -> str:
    uid = UID(uid_hex)
    sv = build_system_vector(uid, counter)
    session_mac_key = calculate_cmac_full(sv, bytes.fromhex(sdm_mac_key_hex))
    data_to_mac = f"{uid.uid}&ctr={counter:06X}&cmac=".encode("ascii")
    cobj = CMAC.new(session_mac_key, ciphermod=AES)
    cobj.update(data_to_mac)
    return truncate_cmac(cobj.digest()).hex().upper()


@pytest.fixture
def vip_client(tmp_path: Path):
    db_path = tmp_path / "test_vip.db"
    csv_path = tmp_path / "test_tag_keys.csv"

    km = CsvKeyManager(csv_path=str(csv_path))
    km.save_tag_keys(
        TagKeys(
            uid=UID(CONTACT_UID),
            picc_master_key="f0fffd0aac340080eb22094665b6d101",
            app_read_key="c024fd41584c72d7be0aa5e29165a526",
            sdm_mac_key=CONTACT_SDM_MAC_KEY,
            outcome=Outcome.INVALID,
            coin_name="",
            status="provisioned",
            notes="https://gs.works/contact",
        )
    )

    coin_csv = tmp_path / "coin_keys.csv"
    app = create_app(key_csv_path=str(coin_csv), db_path=str(db_path), vip_key_csv_path=str(csv_path))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, app


def test_vip_validate_accepts_valid_contact_tag_cmac(vip_client):
    client, _ = vip_client
    ctr = 7
    cmac = _compute_valid_cmac(CONTACT_UID, ctr, CONTACT_SDM_MAC_KEY)

    resp = client.get(f"/api/vip/validate?uid={CONTACT_UID}&ctr={ctr:06X}&cmac={cmac}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["valid"] is True
    assert data["vip"] is True
    assert data["uid"] == CONTACT_UID
    assert data["counter"] == ctr


def test_vip_validate_rejects_tampered_cmac_and_missing_params(vip_client):
    client, _ = vip_client
    resp_missing = client.get("/api/vip/validate?cmac=DEADBEEF")
    assert resp_missing.status_code == 400
    assert resp_missing.get_json()["valid"] is False

    resp_bad = client.get(
        f"/api/vip/validate?uid={CONTACT_UID}&ctr=000007&cmac=0000000000000000"
    )
    assert resp_bad.status_code == 401
    assert resp_bad.get_json()["valid"] is False


def test_vip_send_dispatches_ntfy_and_enforces_counter_anti_replay(vip_client):
    client, _ = vip_client
    ctr = 12
    cmac = _compute_valid_cmac(CONTACT_UID, ctr, CONTACT_SDM_MAC_KEY)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        resp = client.post(
            "/api/vip/send",
            json={
                "uid": CONTACT_UID,
                "ctr": f"{ctr:06X}",
                "cmac": cmac,
                "sender": "Commissioner Gordon",
                "message": "Need help at Gotham City Hall immediately.",
            },
        )
        assert resp.status_code == 200
        assert resp.get_json() == {"ok": True}
        assert mock_urlopen.call_count == 1
        req = mock_urlopen.call_args[0][0]
        assert "ntfy.sh/" in req.full_url
        assert b"Commissioner Gordon" in req.data
        assert b"Need help at Gotham City Hall immediately." in req.data

        # Replaying the same counter (or lower) must be rejected on both validate and send
        resp_replay_val = client.get(
            f"/api/vip/validate?uid={CONTACT_UID}&ctr={ctr:06X}&cmac={cmac}"
        )
        assert resp_replay_val.status_code == 401
        assert resp_replay_val.get_json()["valid"] is False

        resp_replay_send = client.post(
            "/api/vip/send",
            json={
                "uid": CONTACT_UID,
                "ctr": f"{ctr:06X}",
                "cmac": cmac,
                "sender": "Commissioner Gordon",
                "message": "Replay attempt",
            },
        )
        assert resp_replay_send.status_code == 401
        assert resp_replay_send.get_json()["ok"] is False


def test_vip_send_preserves_message_in_sqlite_when_ntfy_fails(vip_client):
    client, app = vip_client
    ctr = 20
    cmac = _compute_valid_cmac(CONTACT_UID, ctr, CONTACT_SDM_MAC_KEY)

    with patch("urllib.request.urlopen", side_effect=OSError("ntfy timeout")):
        resp = client.post(
            "/api/vip/send",
            json={
                "uid": CONTACT_UID,
                "ctr": f"{ctr:06X}",
                "cmac": cmac,
                "sender": "Bruce",
                "message": "Offline test message",
            },
        )
        assert resp.status_code == 502
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"] == "notification_delivery_failed"

    messages = app.vip_service.list_messages()
    assert len(messages) == 1
    assert messages[0]["sender"] == "Bruce"
    assert messages[0]["ntfy_status"] == "failed"
