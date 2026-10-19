"""Unit tests for secret store adapters and TagSecret model."""

from tag_validator.models import TagSecret
from tag_validator.store.memory_store import MemorySecretStore

TEST_UID = "04B7664A2F7080"
TEST_K3 = "825F8399CF2CACF92232B79C406170AF"


def test_tag_secret_model():
    sec = TagSecret(uid=TEST_UID, k3=TEST_K3, coin_name="SWIFT-FALCON-42")
    assert sec.uid == TEST_UID
    assert sec.k3 == TEST_K3
    assert sec.secret_name == f"tag-key-{TEST_UID.lower()}"
    assert sec.masked_k3() == "825F...70AF"

    # Test K8s base64 encoding and decoding round-trip
    k8s_data = sec.to_k8s_secret_data()
    assert "uid" in k8s_data
    assert "k3" in k8s_data

    decoded_sec = TagSecret.from_k8s_secret_data(k8s_data)
    assert decoded_sec.uid == sec.uid
    assert decoded_sec.k3 == sec.k3
    assert decoded_sec.coin_name == sec.coin_name


def test_memory_secret_store():
    store = MemorySecretStore()
    assert store.is_healthy() is True

    sec = TagSecret(uid=TEST_UID, k3=TEST_K3, coin_name="ALPHA-1")
    assert store.save_key(sec) is True

    # Get by UID
    retrieved = store.get_key(TEST_UID)
    assert retrieved is not None
    assert retrieved.uid == TEST_UID
    assert retrieved.k3 == TEST_K3

    # Case-insensitive / formatting tolerance on get
    assert store.get_key("04-b7-66-4a-2f-70-80") is not None

    # List UIDs
    uids = store.list_uids()
    assert TEST_UID in uids

    # Delete
    assert store.delete_key(TEST_UID) is True
    assert store.get_key(TEST_UID) is None
    assert store.delete_key(TEST_UID) is False
