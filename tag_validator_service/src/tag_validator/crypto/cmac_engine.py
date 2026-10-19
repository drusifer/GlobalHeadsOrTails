"""NTAG 424 DNA SDM CMAC Cryptographic Calculations.

Strictly follows NXP AN12196 Section 9.3.9.1 and AN12343 specifications.
Provides constant-time verification of SDM CMAC signatures.
"""

from __future__ import annotations

import hmac
import logging

log = logging.getLogger(__name__)

# Try importing cryptography first, fallback to pycryptodome
try:
    from cryptography.hazmat.primitives import cmac as crypto_cmac
    from cryptography.hazmat.primitives.ciphers import algorithms

    def _cmac_aes(key: bytes, data: bytes) -> bytes:
        c = crypto_cmac.CMAC(algorithms.AES(key))
        c.update(data)
        return c.finalize()

except ImportError:
    try:
        from Crypto.Cipher import AES  # type: ignore
        from Crypto.Hash import CMAC  # type: ignore

        def _cmac_aes(key: bytes, data: bytes) -> bytes:
            c = CMAC.new(key, ciphermod=AES)
            c.update(data)
            return c.digest()

    except ImportError as exc:
        raise ImportError(
            "Either 'cryptography' or 'pycryptodome' must be installed."
        ) from exc


def build_system_vector(uid: str, counter: int) -> bytes:
    """Constructs the 16-byte System Vector (SV2) for NTAG 424 DNA SDM.

    Per NXP AN12196 Section 9.3.9.1:
    SV2 = 3Ch || C3h || 00h || 01h || 00h || 80h || UID(7 bytes) || SDMReadCtr(3 bytes LE)

    Args:
        uid: 14-character hex string representing the 7-byte Tag UID (e.g., '04B7664A2F7080').
        counter: Non-negative integer counter value (0 to 16,777,215).

    Returns:
        16 bytes System Vector.
    """
    clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
    if len(clean_uid) != 14:
        raise ValueError(f"UID must be 14 hex characters (7 bytes), got: '{uid}'")

    try:
        uid_bytes = bytes.fromhex(clean_uid)
    except ValueError as e:
        raise ValueError(f"Invalid hex characters in UID: '{uid}'") from e

    if counter < 0 or counter > 0xFFFFFF:
        raise ValueError(f"Counter out of valid 24-bit range [0, 16777215]: {counter}")

    sv_header = bytes.fromhex("3CC300010080")
    ctr_hex = f"{counter:06X}"
    ctr_bytes_le = bytes.fromhex(ctr_hex)[::-1]  # Little-Endian LSB first

    sv2 = sv_header + uid_bytes + ctr_bytes_le
    if len(sv2) != 16:
        raise ValueError(f"Constructed SV2 length is {len(sv2)}, expected 16")

    return sv2


def calculate_session_key(sv2: bytes, sdm_mac_key: bytes) -> bytes:
    """Derives the 16-byte Session MAC Key using SV2 and Tag Key 3.

    Session_Key = AES-128-CMAC(SV2, key=sdm_mac_key)
    """
    if len(sv2) != 16:
        raise ValueError(f"SV2 must be 16 bytes, got {len(sv2)}")
    if len(sdm_mac_key) != 16:
        raise ValueError(f"sdm_mac_key (K3) must be 16 bytes (32 hex chars), got {len(sdm_mac_key)}")

    return _cmac_aes(sdm_mac_key, sv2)


def calculate_full_cmac(message: bytes, session_key: bytes) -> bytes:
    """Calculates full 16-byte CMAC over message using session key."""
    if len(session_key) != 16:
        raise ValueError(f"session_key must be 16 bytes, got {len(session_key)}")
    return _cmac_aes(session_key, message)


def truncate_cmac(cmac_full: bytes) -> bytes:
    """Truncates CMAC from 16 bytes to 8 bytes per NXP AN12196.

    Extracts odd byte indices (1-indexed even-numbered bytes):
    indices: [1, 3, 5, 7, 9, 11, 13, 15]
    """
    if len(cmac_full) != 16:
        raise ValueError(f"cmac_full must be 16 bytes, got {len(cmac_full)}")
    return bytes([cmac_full[i] for i in range(1, 16, 2)])


def calculate_sdm_cmac(uid: str, counter: int, k3_hex: str) -> str:
    """Executes full SDM CMAC calculation and returns the 16-char hex truncated CMAC."""
    clean_k3 = k3_hex.strip().replace(" ", "").upper()
    if len(clean_k3) != 32:
        raise ValueError(f"K3 key must be 32 hex characters (16 bytes), got {len(clean_k3)}")

    k3_bytes = bytes.fromhex(clean_k3)
    sv2 = build_system_vector(uid, counter)
    session_key = calculate_session_key(sv2, k3_bytes)

    counter_hex = f"{counter:06X}"
    clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
    cmac_message = f"{clean_uid}&ctr={counter_hex}&cmac=".encode("ascii")

    full_cmac = calculate_full_cmac(cmac_message, session_key)
    truncated = truncate_cmac(full_cmac)
    return truncated.hex().upper()


def verify_sdm_cmac(
    uid: str,
    counter: int,
    k3_hex: str,
    received_cmac: str,
) -> tuple[bool, str]:
    """Verifies received CMAC against expected calculated CMAC in constant time.

    Returns:
        (is_valid: bool, calculated_cmac: str)
    """
    clean_received = received_cmac.strip().replace(" ", "").upper()
    calculated = calculate_sdm_cmac(uid, counter, k3_hex)

    is_valid = hmac.compare_digest(calculated, clean_received)
    return is_valid, calculated
