"""Unit tests for shared package contracts."""

import pytest
from shared import UID, Outcome, TagKeys, mask_key


def test_uid_from_hex_and_bytes():
    uid1 = UID("046E6B4A2F7080")
    uid2 = UID(bytes.fromhex("046E6B4A2F7080"))

    assert uid1 == uid2
    assert uid1.uid == "046E6B4A2F7080"
    assert uid1.asset_tag == "6E-6B4A"
    assert uid1.short_hex == "2F7080"
    assert uid1.matches("6E-6B4A")
    assert uid1 == "046E6B4A2F7080"


def test_uid_validation():
    with pytest.raises(ValueError, match="at least 7 bytes"):
        UID("040102")


def test_outcome_enum():
    assert Outcome("heads") == Outcome.HEADS
    assert Outcome("tails") == Outcome.TAILS
    assert Outcome("unknown") == Outcome.INVALID


def test_tag_keys_dataclass():
    tk = TagKeys(
        uid="046E6B4A2F7080",
        picc_master_key="00" * 16,
        app_read_key="11" * 16,
        sdm_mac_key="22" * 16,
        outcome="heads",
        coin_name="GOLDEN-DRAGON",
    )
    assert isinstance(tk.uid, UID)
    assert tk.outcome == Outcome.HEADS
    assert tk.get_picc_master_key_bytes() == bytes.fromhex("00" * 16)
    assert tk.get_app_read_key_bytes() == bytes.fromhex("11" * 16)
    assert tk.get_sdm_mac_key_bytes() == bytes.fromhex("22" * 16)


def test_mask_key():
    assert mask_key("0123456789ABCDEF0123456789ABCDEF") == "0123...CDEF"
    assert mask_key(None) == "None"
    assert mask_key("short") == "***"
