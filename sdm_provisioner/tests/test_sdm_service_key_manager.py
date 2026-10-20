"""Unit tests for sdm_provisioner.service_key_manager.ServiceKeyManager."""

from unittest.mock import MagicMock, patch
import pytest

from sdm_provisioner.service_key_manager import ServiceKeyManager, generate_coin_name
from sdm_provisioner.uid_utils import UID
from shared.outcome import Outcome
from shared.models import TagKeys
from tag_validator.client import TagValidatorClient


@pytest.fixture
def mock_client():
    client = MagicMock(spec=TagValidatorClient)
    client.is_healthy.return_value = True
    return client


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "app.db")


def test_strict_mode_unreachable_raises_connection_error(temp_db):
    client = MagicMock(spec=TagValidatorClient)
    client.is_healthy.return_value = False

    with pytest.raises(ConnectionError, match="make run-tag-validator"):
        ServiceKeyManager(
            service_url="http://localhost:8080",
            db_path=temp_db,
            strict=True,
            client=client,
        )


def test_non_strict_mode_allows_offline(temp_db):
    client = MagicMock(spec=TagValidatorClient)
    client.is_healthy.return_value = False

    mgr = ServiceKeyManager(
        service_url="http://localhost:8080",
        db_path=temp_db,
        strict=False,
        client=client,
    )
    assert mgr.is_healthy() is False


def test_get_key_raw_bytes(mock_client, temp_db):
    test_uid = "04AABBCCDDEEFF"
    mock_client.get_key.return_value = {
        "uid": test_uid,
        "k0": "00112233445566778899AABBCCDDEEFF",
        "k1": "FFEEDDCCBBAA99887766554433221100",
        "k3": "1234567890ABCDEF1234567890ABCDEF",
        "status": "active",
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)

    k0_bytes = mgr.get_key(test_uid, 0)
    assert k0_bytes == bytes.fromhex("00112233445566778899AABBCCDDEEFF")

    k1_bytes = mgr.get_key(test_uid, 1)
    assert k1_bytes == bytes.fromhex("FFEEDDCCBBAA99887766554433221100")

    k3_bytes = mgr.get_key(test_uid, 3)
    assert k3_bytes == bytes.fromhex("1234567890ABCDEF1234567890ABCDEF")

    # Key 2 and 4 always 0s
    assert mgr.get_key(test_uid, 2) == b"\x00" * 16
    assert mgr.get_key(test_uid, 4) == b"\x00" * 16


def test_get_tag_keys_with_app_db_metadata(mock_client, temp_db):
    test_uid = "04112233445566"
    mock_client.get_key.return_value = {
        "uid": test_uid,
        "k0": "00" * 16,
        "k1": "11" * 16,
        "k3": "33" * 16,
        "status": "provisioned",
        "created_at": "2026-10-20T10:00:00Z",
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    mgr.coin_store.set_coin(test_uid, "EAGLE-42", outcome="heads")

    tag_keys = mgr.get_tag_keys(test_uid)
    assert tag_keys.uid.uid == test_uid
    assert tag_keys.coin_name == "EAGLE-42"
    assert tag_keys.outcome == Outcome.HEADS
    assert tag_keys.sdm_mac_key == "33" * 16
    assert tag_keys.status == "provisioned"


def test_get_tag_keys_factory_fallback(mock_client, temp_db):
    test_uid = "04999999999999"
    mock_client.get_key.return_value = None

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    tag_keys = mgr.get_tag_keys(test_uid)
    assert tag_keys.uid.uid == test_uid
    assert tag_keys.status == "factory"
    assert tag_keys.picc_master_key == "0" * 32


def test_generate_random_keys(mock_client, temp_db):
    test_uid = "04A1B2C3D4E5F6"
    mock_client.generate_key.return_value = {
        "status": "created",
        "uid": test_uid,
        "k0": "A0" * 16,
        "k1": "B1" * 16,
        "k3": "C3" * 16,
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    keys = mgr.generate_random_keys(test_uid, coin_name="FALCON-9", outcome=Outcome.TAILS)

    assert keys.uid.uid == test_uid
    assert keys.coin_name == "FALCON-9"
    assert keys.outcome == Outcome.TAILS
    assert keys.picc_master_key == "A0" * 16
    assert keys.sdm_mac_key == "C3" * 16

    # Verify persisted to app.db
    coin = mgr.coin_store.get_coin(test_uid)
    assert coin["coin_name"] == "FALCON-9"
    assert coin["outcome"] == "tails"


def test_two_phase_provision_tag_keys_only(mock_client, temp_db):
    test_uid = "04010203040506"
    mock_client.get_key.return_value = None
    mock_client.generate_key.return_value = {
        "status": "created",
        "uid": test_uid,
        "k0": "00" * 16,
        "k1": "11" * 16,
        "k3": "33" * 16,
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)

    with mgr.provision_tag(test_uid, url=None, coin_name="HAWK-1", outcome=Outcome.HEADS) as staged:
        assert staged.uid.uid == test_uid
        assert staged.coin_name == "HAWK-1"
        assert staged.outcome == Outcome.HEADS

    # Succeeded -> status should be keys_configured
    assert mock_client.save_key.called
    saved_args = mock_client.save_key.call_args[1]
    assert saved_args["status"] == "keys_configured"


def test_two_phase_provision_tag_with_url(mock_client, temp_db):
    test_uid = "04010203040506"
    mock_client.get_key.return_value = {
        "uid": test_uid,
        "k0": "00" * 16,
        "k1": "11" * 16,
        "k3": "33" * 16,
        "status": "keys_configured",
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)

    with mgr.provision_tag(test_uid, url="https://game.heads-or-tails.app", coin_name="HAWK-1", outcome=Outcome.HEADS) as staged:
        assert staged.status == "pending"

    # Succeeded -> status should be provisioned with URL note
    assert mock_client.save_key.called
    saved_args = mock_client.save_key.call_args[1]
    assert saved_args["status"] == "provisioned"


def test_provision_tag_failure_rolls_back(mock_client, temp_db):
    test_uid = "04010203040506"
    mock_client.get_key.return_value = None
    mock_client.generate_key.return_value = {
        "status": "created",
        "uid": test_uid,
        "k0": "00" * 16,
        "k1": "11" * 16,
        "k3": "33" * 16,
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)

    with pytest.raises(RuntimeError, match="APDU Write Failed"):
        with mgr.provision_tag(test_uid, url=None, coin_name="FAIL-1", outcome=Outcome.HEADS):
            raise RuntimeError("APDU Write Failed")


def test_validate_sdm_url(mock_client, temp_db):
    mock_client.validate_tag.return_value = {
        "valid": True,
        "uid": "04AE664A2F7080",
        "counter": 5,
        "cmac_calculated": "1122334455667788",
    }

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    res = mgr.validate_sdm_url("04AE664A2F7080", counter=5, cmac="1122334455667788")

    assert res["valid"] is True
    assert res["counter"] == 5
    assert res["cmac_calculated"] == "1122334455667788"


def test_assign_coin_name_and_duplicate_rejection(mock_client, temp_db):
    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    mock_client.list_keys.return_value = ["04111111111111", "04222222222222"]
    mock_client.get_key.return_value = None

    mgr.assign_coin_name("04111111111111", "COIN-ALPHA", Outcome.HEADS)

    # Assigning TAILS to second tag of same coin is allowed
    mgr.assign_coin_name("04222222222222", "COIN-ALPHA", Outcome.TAILS)

    # Attempting to assign duplicate HEADS to another tag must raise ValueError
    with pytest.raises(ValueError, match="already has a heads tag"):
        mgr.assign_coin_name("04333333333333", "COIN-ALPHA", Outcome.HEADS)


def test_coin_listing_and_completeness(mock_client, temp_db):
    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    mock_client.list_keys.return_value = ["04111111111111", "04222222222222", "04333333333333"]
    mock_client.get_key.return_value = None

    mgr.assign_coin_name("04111111111111", "COIN-COMPLETE", Outcome.HEADS)
    mgr.assign_coin_name("04222222222222", "COIN-COMPLETE", Outcome.TAILS)
    mgr.assign_coin_name("04333333333333", "COIN-INCOMPLETE", Outcome.HEADS)

    coins = mgr.list_coins()
    assert coins["COIN-COMPLETE"]["complete"] is True
    assert coins["COIN-COMPLETE"]["heads_uid"] == "04111111111111"
    assert coins["COIN-COMPLETE"]["tails_uid"] == "04222222222222"

    assert coins["COIN-INCOMPLETE"]["complete"] is False

    val = mgr.validate_coin("COIN-COMPLETE")
    assert val["complete"] is True
    assert len(val["issues"]) == 0

    val_inc = mgr.validate_coin("COIN-INCOMPLETE")
    assert val_inc["complete"] is False
    assert "Missing tails tag" in val_inc["issues"]


def test_soft_delete_and_undelete(mock_client, temp_db):
    mock_client.delete_key.return_value = True
    mock_client.undelete_key.return_value = True

    mgr = ServiceKeyManager(db_path=temp_db, client=mock_client)
    assert mgr.delete_key("04112233445566") is True
    assert mgr.undelete_key("04112233445566") is True
