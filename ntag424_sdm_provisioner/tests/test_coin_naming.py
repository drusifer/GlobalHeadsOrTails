"""Characterization tests for coin naming feature.

Tests the new coin_name field in TagKeys and related API methods:
- assign_coin_name()
- get_coin_tags()
- validate_coin()
- list_coins()
"""

import tempfile
from pathlib import Path

import pytest

from ntag424_sdm_provisioner.csv_key_manager import (
    CsvKeyManager,
    Outcome,
    TagKeys,
    generate_coin_name,
)
from ntag424_sdm_provisioner.uid_utils import UID


@pytest.fixture
def temp_key_manager():
    """Create a temporary key manager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test_keys.csv"
        backup_path = Path(tmpdir) / "test_keys_backup.csv"
        backup_dir = Path(tmpdir) / "backups"

        km = CsvKeyManager(
            csv_path=str(csv_path),
            backup_path=str(backup_path),
            timestamped_backup_dir=str(backup_dir),
        )
        yield km


# ============================================================================
# Test 1-3: Coin Name Generation
# ============================================================================

def test_generate_coin_name_not_empty():
    """Generated coin names should not be empty."""
    name = generate_coin_name()
    assert name, "Coin name should not be empty"
    assert isinstance(name, str), "Coin name should be a string"


def test_generate_coin_name_unique():
    """Generated coin names should be unique."""
    names = {generate_coin_name() for _ in range(100)}
    assert len(names) > 90, "Most generated names should be unique"


def test_generate_coin_name_format():
    """Generated coin names should follow expected format."""
    name = generate_coin_name()
    # Should be uppercase
    assert name == name.upper(), "Coin name should be uppercase"
    # Should contain hyphens (unless fallback mode)
    assert "-" in name, "Coin name should contain hyphens"


# ============================================================================
# Test 4: assign_coin_name()
# ============================================================================

def test_assign_coin_name_valid(temp_key_manager):
    """Should successfully assign coin name and outcome to a tag."""
    uid = UID("04AE664A2F7080")
    coin_name = "SWIFT-FALCON-42"

    # Create factory tag
    factory_keys = TagKeys.from_factory_keys(uid)
    temp_key_manager.save_tag_keys(factory_keys)

    # Assign coin name
    temp_key_manager.assign_coin_name(uid, coin_name, Outcome.HEADS)

    # Verify
    keys = temp_key_manager.get_tag_keys(uid)
    assert keys.coin_name == coin_name
    assert keys.outcome == Outcome.HEADS


def test_assign_coin_name_duplicate_outcome_raises(temp_key_manager):
    """Should raise ValueError if trying to assign duplicate outcome to same coin."""
    uid1 = UID("04AE664A2F7080")
    uid2 = UID("04AE664A2F7081")
    coin_name = "SWIFT-FALCON-42"

    # Create two tags
    keys1 = TagKeys.from_factory_keys(uid1)
    keys2 = TagKeys.from_factory_keys(uid2)
    temp_key_manager.save_tag_keys(keys1)
    temp_key_manager.save_tag_keys(keys2)

    # Assign HEADS to first tag
    temp_key_manager.assign_coin_name(uid1, coin_name, Outcome.HEADS)

    # Try to assign HEADS to second tag - should raise
    with pytest.raises(ValueError, match="already has a heads tag"):
        temp_key_manager.assign_coin_name(uid2, coin_name, Outcome.HEADS)


def test_assign_coin_name_invalid_outcome_raises(temp_key_manager):
    """Should raise ValueError if outcome is INVALID."""
    uid = UID("04AE664A2F7080")
    keys = TagKeys.from_factory_keys(uid)
    temp_key_manager.save_tag_keys(keys)

    with pytest.raises(ValueError, match="must be HEADS or TAILS"):
        temp_key_manager.assign_coin_name(uid, "COIN-001", Outcome.INVALID)


# ============================================================================
# Test 5-6: get_coin_tags()
# ============================================================================

def test_get_coin_tags_complete(temp_key_manager):
    """Should return both heads and tails for a complete coin."""
    uid_heads = UID("04AE664A2F7080")
    uid_tails = UID("04AE664A2F7081")
    coin_name = "SWIFT-FALCON-42"

    # Create and assign both tags
    keys_heads = TagKeys.from_factory_keys(uid_heads)
    keys_tails = TagKeys.from_factory_keys(uid_tails)
    temp_key_manager.save_tag_keys(keys_heads)
    temp_key_manager.save_tag_keys(keys_tails)

    temp_key_manager.assign_coin_name(uid_heads, coin_name, Outcome.HEADS)
    temp_key_manager.assign_coin_name(uid_tails, coin_name, Outcome.TAILS)

    # Get coin tags
    coin_tags = temp_key_manager.get_coin_tags(coin_name)

    assert coin_tags['heads'] is not None
    assert coin_tags['tails'] is not None
    assert coin_tags['heads'].uid.uid == uid_heads.uid
    assert coin_tags['tails'].uid.uid == uid_tails.uid


def test_get_coin_tags_incomplete(temp_key_manager):
    """Should return None for missing side of incomplete coin."""
    uid_heads = UID("04AE664A2F7080")
    coin_name = "SWIFT-FALCON-42"

    # Create and assign only heads
    keys_heads = TagKeys.from_factory_keys(uid_heads)
    temp_key_manager.save_tag_keys(keys_heads)
    temp_key_manager.assign_coin_name(uid_heads, coin_name, Outcome.HEADS)

    # Get coin tags
    coin_tags = temp_key_manager.get_coin_tags(coin_name)

    assert coin_tags['heads'] is not None
    assert coin_tags['tails'] is None


# ============================================================================
# Test 7-8: validate_coin()
# ============================================================================

def test_validate_coin_complete(temp_key_manager):
    """Should report coin as complete when both sides are provisioned."""
    uid_heads = UID("04AE664A2F7080")
    uid_tails = UID("04AE664A2F7081")
    coin_name = "SWIFT-FALCON-42"

    # Create provisioned tags
    keys_heads = temp_key_manager.generate_random_keys(uid_heads, coin_name, Outcome.HEADS)
    keys_tails = temp_key_manager.generate_random_keys(uid_tails, coin_name, Outcome.TAILS)
    keys_heads.status = "provisioned"
    keys_tails.status = "provisioned"
    temp_key_manager.save_tag_keys(keys_heads)
    temp_key_manager.save_tag_keys(keys_tails)

    # Validate
    result = temp_key_manager.validate_coin(coin_name)

    assert result['complete'] is True
    assert len(result['issues']) == 0


def test_validate_coin_incomplete(temp_key_manager):
    """Should report coin as incomplete when missing a side."""
    uid_heads = UID("04AE664A2F7080")
    coin_name = "SWIFT-FALCON-42"

    # Create only heads tag
    keys_heads = temp_key_manager.generate_random_keys(uid_heads, coin_name, Outcome.HEADS)
    keys_heads.status = "provisioned"
    temp_key_manager.save_tag_keys(keys_heads)

    # Validate
    result = temp_key_manager.validate_coin(coin_name)

    assert result['complete'] is False
    assert "Missing tails tag" in result['issues']


def test_validate_coin_not_provisioned(temp_key_manager):
    """Should report issue when tag exists but not provisioned."""
    uid_heads = UID("04AE664A2F7080")
    uid_tails = UID("04AE664A2F7081")
    coin_name = "SWIFT-FALCON-42"

    # Create tags but don't provision them
    keys_heads = TagKeys.from_factory_keys(uid_heads)
    keys_tails = TagKeys.from_factory_keys(uid_tails)
    keys_heads.coin_name = coin_name
    keys_heads.outcome = Outcome.HEADS
    keys_tails.coin_name = coin_name
    keys_tails.outcome = Outcome.TAILS
    temp_key_manager.save_tag_keys(keys_heads)
    temp_key_manager.save_tag_keys(keys_tails)

    # Validate
    result = temp_key_manager.validate_coin(coin_name)

    assert result['complete'] is False
    assert any("not provisioned" in issue for issue in result['issues'])


# ============================================================================
# Test 9: list_coins()
# ============================================================================

def test_list_coins_summary(temp_key_manager):
    """Should list all coins with their completion status."""
    # Create complete coin
    uid1_heads = UID("04AE664A2F7080")
    uid1_tails = UID("04AE664A2F7081")
    coin1 = "SWIFT-FALCON-42"

    keys1h = temp_key_manager.generate_random_keys(uid1_heads, coin1, Outcome.HEADS)
    keys1t = temp_key_manager.generate_random_keys(uid1_tails, coin1, Outcome.TAILS)
    temp_key_manager.save_tag_keys(keys1h)
    temp_key_manager.save_tag_keys(keys1t)

    # Create incomplete coin
    uid2_heads = UID("04AE664A2F7082")
    coin2 = "BOLD-EAGLE-99"

    keys2h = temp_key_manager.generate_random_keys(uid2_heads, coin2, Outcome.HEADS)
    temp_key_manager.save_tag_keys(keys2h)

    # Create unassigned tag
    uid3 = UID("04AE664A2F7083")
    keys3 = TagKeys.from_factory_keys(uid3)
    temp_key_manager.save_tag_keys(keys3)

    # List coins
    coins = temp_key_manager.list_coins()

    assert coin1 in coins
    assert coins[coin1]['complete'] is True
    assert coins[coin1]['heads_uid'] == uid1_heads.uid
    assert coins[coin1]['tails_uid'] == uid1_tails.uid

    assert coin2 in coins
    assert coins[coin2]['complete'] is False
    assert coins[coin2]['heads_uid'] == uid2_heads.uid
    assert coins[coin2]['tails_uid'] is None

    assert "" in coins  # Unassigned tags
    assert coins[""]["unassigned_count"] == 1


# ============================================================================
# Test 10: Backwards Compatibility
# ============================================================================

def test_backwards_compatibility_missing_coin_name(temp_key_manager):
    """Should handle tags with missing coin_name field gracefully."""
    uid = UID("04AE664A2F7080")

    # Manually create CSV entry without coin_name field (simulate old data)
    old_keys = TagKeys.from_factory_keys(uid)
    # Temporarily remove coin_name from the saved data
    temp_key_manager.save_tag_keys(old_keys)

    # Read back - should default to empty string
    keys = temp_key_manager.get_tag_keys(uid)
    assert keys.coin_name == ""  # Should default to empty, not crash


# ============================================================================
# Test 11: TagKeys __str__() Method
# ============================================================================

def test_tagkeys_str_with_coin_name():
    """TagKeys __str__ should display coin name."""
    uid = UID("04AE664A2F7080")
    keys = TagKeys(
        uid=uid,
        picc_master_key="A" * 32,
        app_read_key="B" * 32,
        sdm_mac_key="C" * 32,
        outcome=Outcome.HEADS,
        coin_name="SWIFT-FALCON-42",
        provisioned_date="2026-01-27T12:00:00",
        status="provisioned"
    )

    output = str(keys)
    assert "SWIFT-FALCON-42" in output
    assert "heads" in output


def test_tagkeys_str_without_coin_name():
    """TagKeys __str__ should show 'Unassigned' when no coin name."""
    uid = UID("04AE664A2F7080")
    keys = TagKeys.from_factory_keys(uid)

    output = str(keys)
    assert "Unassigned" in output
