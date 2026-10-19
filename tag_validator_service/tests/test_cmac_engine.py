"""Unit tests for NTAG 424 DNA SDM CMAC engine."""

import pytest

from tag_validator.crypto.cmac_engine import (
    build_system_vector,
    calculate_sdm_cmac,
    truncate_cmac,
    verify_sdm_cmac,
)

KNOWN_UID = "043F13E2151990"
KNOWN_K3 = "99e88808adc7885bc7065d739a25e1d0"
KNOWN_CTR = 1


def test_build_system_vector_valid():
    sv2 = build_system_vector(KNOWN_UID, KNOWN_CTR)
    assert len(sv2) == 16
    assert sv2[:6] == bytes.fromhex("3CC300010080")
    assert sv2[6:13] == bytes.fromhex(KNOWN_UID)
    # Counter 1 -> 000001 in hex BE -> 010000 in LE
    assert sv2[13:] == bytes.fromhex("010000")


def test_build_system_vector_formatting():
    # Supports hyphenated or lowercase UIDs
    sv1 = build_system_vector("04-3F-13-E2-15-19-90", 42)
    sv2 = build_system_vector("043f13e2151990", 42)
    assert sv1 == sv2


def test_build_system_vector_invalid_uid():
    with pytest.raises(ValueError, match="14 hex characters"):
        build_system_vector("043F13E215", 1)

    with pytest.raises(ValueError, match="Invalid hex"):
        build_system_vector("043F13E21519ZZ", 1)


def test_build_system_vector_invalid_counter():
    with pytest.raises(ValueError, match="Counter out of valid"):
        build_system_vector(KNOWN_UID, -1)

    with pytest.raises(ValueError, match="Counter out of valid"):
        build_system_vector(KNOWN_UID, 0x1000000)


def test_truncate_cmac():
    full_16 = bytes(range(16))
    truncated = truncate_cmac(full_16)
    assert len(truncated) == 8
    # Odd indices: 1, 3, 5, 7, 9, 11, 13, 15
    assert list(truncated) == [1, 3, 5, 7, 9, 11, 13, 15]

    with pytest.raises(ValueError, match="16 bytes"):
        truncate_cmac(b"short")


def test_cmac_calculation_and_verification():
    cmac_val = calculate_sdm_cmac(KNOWN_UID, KNOWN_CTR, KNOWN_K3)
    assert len(cmac_val) == 16  # 8 bytes = 16 hex chars

    # Valid check
    is_valid, calc = verify_sdm_cmac(KNOWN_UID, KNOWN_CTR, KNOWN_K3, cmac_val)
    assert is_valid is True
    assert calc == cmac_val

    # Case-insensitive received cmac check
    is_valid_lower, _ = verify_sdm_cmac(KNOWN_UID, KNOWN_CTR, KNOWN_K3, cmac_val.lower())
    assert is_valid_lower is True

    # Tampered CMAC check
    bad_cmac = "0000000000000000" if cmac_val != "0000000000000000" else "FFFFFFFFFFFFFFFF"
    is_valid_bad, _ = verify_sdm_cmac(KNOWN_UID, KNOWN_CTR, KNOWN_K3, bad_cmac)
    assert is_valid_bad is False

    # Counter mismatch check
    is_valid_wrong_ctr, _ = verify_sdm_cmac(KNOWN_UID, KNOWN_CTR + 1, KNOWN_K3, cmac_val)
    assert is_valid_wrong_ctr is False
