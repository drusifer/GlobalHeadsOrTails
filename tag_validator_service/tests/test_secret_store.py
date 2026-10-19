"""Unit tests for secret store adapters and TagSecret model with WORM semantics."""

import pytest

from tag_validator.models import TagSecret
from tag_validator.store.base import KeyConflictError
from tag_validator.store.memory_store import MemorySecretStore

TEST_UID = "04B7664A2F7080"
TEST_K3 = "825F8399CF2CACF92232B79C406170AF"
DIFFERENT_K3 = "11112222333344445555666677778888"


def test_tag_secret_model():
    sec = TagSecret(uid=TEST_UID, k3=TEST_K3)
    assert sec.uid == TEST_UID
    assert sec.k3 == TEST_K3
    assert sec.status == "active"
    assert sec.secret_name == f"tag-key-{TEST_UID.lower()}"
    assert sec.masked_k3() == "825F...70AF"

    # Test K8s base64 encoding and decoding round-trip
    k8s_data = sec.to_k8s_secret_data()
    assert "uid" in k8s_data
    assert "k3" in k8s_data
    assert "status" in k8s_data

    decoded_sec = TagSecret.from_k8s_secret_data(k8s_data)
    assert decoded_sec.uid == sec.uid
    assert decoded_sec.k3 == sec.k3
    assert decoded_sec.status == sec.status


def test_memory_secret_store_worm_and_soft_delete():
    store = MemorySecretStore()
    assert store.is_healthy() is True

    sec = TagSecret(uid=TEST_UID, k3=TEST_K3)
    assert store.save_key(sec) is True

    # Get by UID
    retrieved = store.get_key(TEST_UID)
    assert retrieved is not None
    assert retrieved.uid == TEST_UID
    assert retrieved.k3 == TEST_K3
    assert retrieved.status == "active"

    # WORM check: saving identical key is idempotent
    assert store.save_key(sec) is True

    # WORM check: attempting to overwrite with differing key raises KeyConflictError
    conflicting_sec = TagSecret(uid=TEST_UID, k3=DIFFERENT_K3)
    with pytest.raises(KeyConflictError):
        store.save_key(conflicting_sec)

    # Case-insensitive / formatting tolerance on get
    assert store.get_key("04-b7-66-4a-2f-70-80") is not None

    # List UIDs (active only)
    uids = store.list_uids()
    assert TEST_UID in uids

    # Soft-Delete (tombstone)
    assert store.delete_key(TEST_UID) is True
    # Default get_key filters out deleted
    assert store.get_key(TEST_UID) is None
    # include_deleted=True still accesses the vault record
    tombstone = store.get_key(TEST_UID, include_deleted=True)
    assert tombstone is not None
    assert tombstone.status == "deleted"
    assert tombstone.deleted_at is not None

    # List active vs all
    assert TEST_UID not in store.list_uids(include_deleted=False)
    assert TEST_UID in store.list_uids(include_deleted=True)

    # Undelete
    assert store.undelete_key(TEST_UID) is True
    restored = store.get_key(TEST_UID)
    assert restored is not None
    assert restored.status == "active"
    assert restored.deleted_at is None
    assert TEST_UID in store.list_uids(include_deleted=False)

