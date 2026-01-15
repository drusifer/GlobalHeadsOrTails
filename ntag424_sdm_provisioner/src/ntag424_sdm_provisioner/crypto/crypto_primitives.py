"""NTAG424 DNA Cryptographic Primitives.

Verified implementations of crypto operations per NXP specifications (AN12196, AN12343).
These functions have been tested against official NXP test vectors and match exactly.

All functions follow the NTAG424 DNA / MIFARE DESFire EV2 specifications.
"""

import zlib
import math
from collections import Counter

from Crypto.Cipher import AES  # nosec
from Crypto.Hash import CMAC  # nosec


def calculate_iv_for_command(ti: bytes, cmd_ctr: int, session_enc_key: bytes) -> bytes:
    """Calculate IV for command encryption per NXP spec.

    IV = E(KSesAuthENC, zero_iv, A5 5A || TI || CmdCtr || 0x00*8)

    Args:
        ti: Transaction Identifier (4 bytes)
        cmd_ctr: Command counter (0-65535)
        session_enc_key: Session encryption key (16 bytes)

    Returns:
        Encrypted IV (16 bytes)

    Reference:
        AN12196 Table 26, Step 12
        AN12343 Table 40, Row 18
    """
    # Build plaintext IV: A5 5A || TI || CmdCtr || zeros
    plaintext_iv = bytearray(16)
    plaintext_iv[0] = 0xA5
    plaintext_iv[1] = 0x5A
    plaintext_iv[2:6] = ti
    plaintext_iv[6:8] = cmd_ctr.to_bytes(2, byteorder="little")
    # Rest is zeros

    # Encrypt with zero IV
    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=b"\x00" * 16)
    iv_encrypted = cipher.encrypt(bytes(plaintext_iv))

    return iv_encrypted


def encrypt_key_data(key_data: bytes, iv: bytes, session_enc_key: bytes) -> bytes:
    """Encrypt key data using AES-CBC.

    Args:
        key_data: Plaintext key data (must be multiple of 16 bytes)
        iv: Initialization vector (16 bytes)
        session_enc_key: Session encryption key (16 bytes)

    Returns:
        Encrypted data (same length as input)

    Reference:
        AN12196 Table 26, Step 13
        AN12343 Table 40, Row 20
    """
    if len(key_data) % 16 != 0:
        raise ValueError(f"key_data must be multiple of 16 bytes, got {len(key_data)}")

    cipher = AES.new(session_enc_key, AES.MODE_CBC, iv=iv)
    encrypted = cipher.encrypt(key_data)

    return encrypted


def calculate_cmac_full(mac_input: bytes, session_mac_key: bytes) -> bytes:
    """Calculate full 16-byte CMAC.

    Args:
        mac_input: Data to MAC
        session_mac_key: Session MAC key (16 bytes)

    Returns:
        Full CMAC (16 bytes)

    Reference:
        AN12196 Table 26, Step 15
    """
    cmac_obj = CMAC.new(session_mac_key, ciphermod=AES)
    cmac_obj.update(mac_input)
    return cmac_obj.digest()


def truncate_cmac(cmac_full: bytes) -> bytes:
    """Truncate CMAC to 8 bytes per NXP AN12196 specification.

    NXP uses 1-based indexing: "even-numbered bytes" = bytes 2,4,6,8,10,12,14,16
    In Python 0-based indexing: indices 1,3,5,7,9,11,13,15

    Args:
        cmac_full: Full 16-byte CMAC

    Returns:
        Truncated 8-byte CMAC

    Reference:
        AN12196 Table 26, Step 16
        NT4H2421Gx datasheet line 852
    """
    if len(cmac_full) != 16:
        raise ValueError(f"cmac_full must be 16 bytes, got {len(cmac_full)}")

    # NXP "even-numbered bytes" (1-indexed) = Python odd indices (0-indexed)
    return bytes([cmac_full[i] for i in range(1, 16, 2)])


def calculate_cmac(
    cmd: int,
    cmd_ctr: int,
    ti: bytes,
    cmd_header: bytes,
    encrypted_data: bytes,
    session_mac_key: bytes,
) -> bytes:
    """Calculate truncated CMAC for authenticated command.

    CMAC input: Cmd || CmdCtr || TI || CmdHeader || EncryptedData

    Args:
        cmd: Command byte (e.g., 0xC4 for ChangeKey)
        cmd_ctr: Command counter (0-65535)
        ti: Transaction Identifier (4 bytes)
        cmd_header: Command header data (e.g., KeyNo for ChangeKey)
        encrypted_data: Encrypted command data
        session_mac_key: Session MAC key (16 bytes)

    Returns:
        Truncated CMAC (8 bytes)

    Reference:
        AN12196 Table 26, Steps 14-16
    """
    # Build CMAC input
    mac_input = bytearray()
    mac_input.append(cmd)
    mac_input.extend(cmd_ctr.to_bytes(2, byteorder="little"))
    mac_input.extend(ti)
    mac_input.extend(cmd_header)
    mac_input.extend(encrypted_data)

    # Calculate full CMAC
    cmac_full = calculate_cmac_full(bytes(mac_input), session_mac_key)

    # Truncate to 8 bytes
    return truncate_cmac(cmac_full)


def build_key_data(key_no: int, new_key: bytes, old_key: bytes, version: int) -> bytes:
    """Build 32-byte key data for ChangeKey command.

    Format per NXP spec:
    - Key 0: NewKey(16) + Version(1) + 0x80 + padding(14) = 32 bytes
    - Others: XOR(16) + Version(1) + CRC32(4) + 0x80 + padding(10) = 32 bytes

    Args:
        key_no: Key number (0-4)
        new_key: New key value (16 bytes)
        old_key: Old key value (16 bytes, or None for key 0)
        version: Key version (0-255)

    Returns:
        32-byte key data ready for encryption

    Reference:
        AN12196 Table 26, Step 11
        AN12343 Table 40, Row 16
        MFRC522_NTAG424DNA.cpp lines 1047-1064
    """
    if len(new_key) != 16:
        raise ValueError(f"new_key must be 16 bytes, got {len(new_key)}")

    key_data = bytearray(32)

    if key_no == 0:
        # Key 0 format: NewKey(16) + Version(1) + 0x80 + padding(14)
        key_data[0:16] = new_key
        key_data[16] = version
        key_data[17] = 0x80
        # Rest is already zeros (14 bytes)
    else:
        # Other keys format: XOR(16) + Version(1) + CRC32(4) + 0x80 + padding(10)
        if old_key is None:
            old_key = bytes(16)
        if len(old_key) != 16:
            raise ValueError(f"old_key must be 16 bytes, got {len(old_key)}")

        # XOR new and old keys
        xored = bytes(a ^ b for a, b in zip(new_key, old_key, strict=True))

        # CRC32 of new key, inverted per Arduino
        crc = zlib.crc32(new_key) ^ 0xFFFFFFFF
        crc_bytes = crc.to_bytes(4, byteorder="little")

        key_data[0:16] = xored
        key_data[16] = version
        key_data[17:21] = crc_bytes
        key_data[21] = 0x80
        # Rest is already zeros (10 bytes)

    return bytes(key_data)


def decrypt_rndb(encrypted_rndb: bytes, key: bytes) -> bytes:
    """Decrypt RndB from authentication Phase 1 response.

    Per NXP datasheet Section 9.1.5:
    Uses AES-CBC with zero IV (no padding during authentication).

    Args:
        encrypted_rndb: Encrypted RndB from card (16 bytes)
        key: Authentication key (16 bytes)

    Returns:
        Decrypted RndB (16 bytes)

    Reference:
        NXP NT4H2421Gx Section 9.1.5
        Arduino MFRC522 line 62-65
    """
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return cipher.decrypt(encrypted_rndb)


def rotate_left(data: bytes) -> bytes:
    """Rotate bytes left by 1 byte.

    Per NXP spec: "RndB rotated left by 1 byte"

    Args:
        data: Bytes to rotate (typically 16 bytes)

    Returns:
        Rotated bytes

    Reference:
        NXP NT4H2421Gx Table 28
        Arduino MFRC522 line 70-73
    """
    return data[1:] + data[:1]


def encrypt_auth_response(rnda: bytes, rndb_rotated: bytes, key: bytes) -> bytes:
    """Encrypt authentication Phase 2 response.

    Per NXP datasheet Section 9.1.5:
    Encrypts RndA || RndB' using AES-CBC with zero IV.

    Args:
        rnda: Random A from PCD (16 bytes)
        rndb_rotated: Rotated RndB (16 bytes)
        key: Authentication key (16 bytes)

    Returns:
        Encrypted 32 bytes

    Reference:
        NXP NT4H2421Gx Section 9.1.5
        Arduino MFRC522 line 76-81
    """
    plaintext = rnda + rndb_rotated
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return cipher.encrypt(plaintext)


def decrypt_auth_response(encrypted_response: bytes, key: bytes) -> bytes:
    """Decrypt authentication Phase 2 card response.

    Per NXP datasheet: Ti || RndA' || PDcap2 || PCDcap2

    Args:
        encrypted_response: Encrypted response from card (32 bytes)
        key: Authentication key (16 bytes)

    Returns:
        Decrypted 32 bytes

    Reference:
        NXP NT4H2421Gx Section 9.1.5
        Arduino MFRC522 line 96-97
    """
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return cipher.decrypt(encrypted_response)


def derive_session_keys(key: bytes, rnda: bytes, rndb: bytes) -> tuple[bytes, bytes]:
    """Derive session encryption and MAC keys from RndA, RndB.

    Uses NTAG424 DNA key derivation per NXP datasheet Section 9.1.7:
    SV1 = A5||5A||00||01||00||80||RndA[15..14]||(RndA[13..8] XOR RndB[15..10])||RndB[9..0]||RndA[7..0]
    SV2 = 5A||A5||00||01||00||80||RndA[15..14]||(RndA[13..8] XOR RndB[15..10])||RndB[9..0]||RndA[7..0]

    This is the FULL 32-byte structure with XOR operations per spec.

    Args:
        key: Authentication key (16 bytes)
        rnda: Random A from PCD (16 bytes)
        rndb: Random B from PICC (16 bytes)

    Returns:
        (session_enc_key, session_mac_key) tuple

    Reference:
        NXP NT4H2421Gx Section 9.1.7
        Arduino MFRC522_NTAG424DNA.cpp lines 2215-2244
    """
    # Build 32-byte SV1 per datasheet
    sv1 = bytearray(32)
    sv1[0] = 0xA5
    sv1[1] = 0x5A
    sv1[2:6] = b"\x00\x01\x00\x80"
    sv1[6:8] = rnda[0:2]  # RndA[15..14] (first 2 bytes)
    sv1[8:14] = rndb[0:6]  # RndB[15..10] (first 6 bytes)
    sv1[14:24] = rndb[6:16]  # RndB[9..0] (last 10 bytes)
    sv1[24:32] = rnda[8:16]  # RndA[7..0] (last 8 bytes)

    # XOR: RndA[13..8] with RndB[15..10] per datasheet
    for i in range(6):
        sv1[8 + i] ^= rnda[2 + i]

    # Build 32-byte SV2 (same structure, different label)
    sv2 = bytearray(sv1)
    sv2[0] = 0x5A
    sv2[1] = 0xA5

    # Calculate session keys using CMAC over full 32-byte SV
    cmac_enc = CMAC.new(key, ciphermod=AES)
    cmac_enc.update(bytes(sv1))
    session_enc_key = cmac_enc.digest()

    cmac_mac = CMAC.new(key, ciphermod=AES)
    cmac_mac.update(bytes(sv2))
    session_mac_key = cmac_mac.digest()

    return session_enc_key, session_mac_key


def derive_sdm_session_mac_key(
    sdm_file_read_key: bytes, uid: bytes, read_counter: bytes
) -> bytes:
    """Derive SDM session MAC key for Secure Dynamic Messaging.

    Per NXP NTAG424 DNA datasheet Section 9.3.9.1:
    SV2 = 3Ch || C3h || 00h || 01h || 00h || 80h [|| UID] [|| SDMReadCtr] [|| ZeroPadding]

    Whether or not the UID and/or SDMReadCtr are included in session vector SV2,
    depends on whether they are mirrored. This implementation assumes both are mirrored.

    Padding with zeros is done up to a multiple of 16 bytes. With 7-byte UID and
    3-byte counter, the total is 6 + 7 + 3 = 16 bytes (no padding needed).

    SesSDMFileReadMACKey = CMAC(SDMFileReadKey, SV2)

    Args:
        sdm_file_read_key: SDM File Read Key (16 bytes, Key 3)
        uid: Tag UID (7 bytes)
        read_counter: SDM Read Counter (3 bytes)

    Returns:
        Session MAC key for SDM (16 bytes)

    Reference:
        NXP NT4H2421Gx Section 9.3.9.1
        NXP_SECTION_9_SECURE_MESSAGING.md lines 845-909
    """
    if len(sdm_file_read_key) != 16:
        raise ValueError(f"sdm_file_read_key must be 16 bytes, got {len(sdm_file_read_key)}")
    if len(uid) != 7:
        raise ValueError(f"uid must be 7 bytes, got {len(uid)}")
    if len(read_counter) != 3:
        raise ValueError(f"read_counter must be 3 bytes, got {len(read_counter)}")

    # Build session vector SV2: 3C C3 00 01 00 80 || UID(7) || ReadCtr(3)
    sv2 = bytearray(16)
    sv2[0] = 0x3C
    sv2[1] = 0xC3
    sv2[2] = 0x00
    sv2[3] = 0x01
    sv2[4] = 0x00
    sv2[5] = 0x80
    sv2[6:13] = uid  # UID (7 bytes)
    sv2[13:16] = read_counter  # SDMReadCtr (3 bytes)

    # Derive session key using CMAC
    cmac_obj = CMAC.new(sdm_file_read_key, ciphermod=AES)
    cmac_obj.update(bytes(sv2))
    session_mac_key = cmac_obj.digest()

    return session_mac_key


def build_changekey_apdu(
    key_no: int,
    new_key: bytes,
    old_key: bytes,
    version: int,
    ti: bytes,
    cmd_ctr: int,
    session_enc_key: bytes,
    session_mac_key: bytes,
) -> list[int]:
    """Build complete ChangeKey APDU with encryption and CMAC.

    Args:
        key_no: Key number to change (0-4)
        new_key: New key value (16 bytes)
        old_key: Old key value (16 bytes, or None for key 0)
        version: New key version (0-255)
        ti: Transaction Identifier (4 bytes)
        cmd_ctr: Command counter (0-65535)
        session_enc_key: Session encryption key (16 bytes)
        session_mac_key: Session MAC key (16 bytes)

    Returns:
        Complete APDU as list of integers

    Reference:
        AN12196 Table 26 (complete example)
    """
    # Build 32-byte key data
    key_data = build_key_data(key_no, new_key, old_key, version)

    # Calculate IV
    iv = calculate_iv_for_command(ti, cmd_ctr, session_enc_key)

    # Encrypt key data
    encrypted = encrypt_key_data(key_data, iv, session_enc_key)

    # Calculate CMAC
    cmd_header = bytes([key_no])
    cmac = calculate_cmac(0xC4, cmd_ctr, ti, cmd_header, encrypted, session_mac_key)

    # Build APDU: CLA CMD P1 P2 Lc KeyNo Encrypted(32) CMAC(8) Le
    apdu = [
        0x90,  # CLA
        0xC4,  # CMD (ChangeKey)
        0x00,  # P1
        0x00,  # P2
        0x29,  # Lc (41 bytes: KeyNo + Encrypted + CMAC)
        key_no,  # KeyNo
        *list(encrypted),  # Encrypted data (32 bytes)
        *list(cmac),  # CMAC (8 bytes)
        0x00,  # Le
    ]

    return apdu


def calculate_entropy(data: bytes) -> float:
    """Calculates the Shannon entropy of a sequence based on its bit distribution.

    Entropy is a measure of the uncertainty or randomness in the data.
    This function calculates the fundamental entropy in "bits per bit" (a value
    between 0.0 for non-random data and 1.0 for perfectly random data) and then
    scales it to the more intuitive "bits per byte" range (0.0 to 8.0).

    A high entropy value (e.g., > 7.9 bits per byte) is a good indicator of
    cryptographic-quality randomness.

    Args:
        data: The input byte sequence.

    Returns:
        The calculated entropy as a float, in bits per byte.
    """
    if not data:
        return 0.0

    total_bits = len(data) * 8
    # Count the total number of set bits (1s) in the byte sequence
    count_of_ones = sum(bin(byte).count('1') for byte in data)

    # Handle the edge case of all 0s or all 1s, where entropy is 0
    if count_of_ones == 0 or count_of_ones == total_bits:
        return 0.0

    # Calculate probabilities of 0 and 1
    p1 = count_of_ones / total_bits
    p0 = 1.0 - p1

    # Calculate entropy in bits per bit
    entropy_per_bit = - (p0 * math.log2(p0) + p1 * math.log2(p1))

    # Scale to bits per byte for a standard 0-8 range
    return entropy_per_bit * 8


def nist_frequency_monobit_test(data: bytes, significance_level: float = 0.01) -> tuple[float, bool]:
    """Performs the NIST SP 800-22 Frequency (Monobit) Test.

    This test checks for the proportion of zeros and ones in a sequence. A truly
    random sequence is expected to have approximately the same number of zeros
    and ones.

    The test calculates a P-value, which is the probability that a perfect random
    number generator would produce a sequence less random than the one being tested.

    Args:
        data: The byte sequence to test. Must be at least 100 bits long.
        significance_level: The P-value threshold for passing the test.
                            Defaults to 0.01 per NIST recommendation.

    Returns:
        A tuple containing:
        - The calculated P-value (float).
        - A boolean indicating if the test passed (P-value >= significance_level).

    Reference:
        NIST Special Publication 800-22, Section 2.1.
    """
    n = len(data) * 8
    if n < 100:
        raise ValueError("Data must be at least 100 bits long for the Monobit test.")

    # 1. Convert the sequence of 0s and 1s to a sequence of -1s and +1s.
    #    S_n is the sum of this new sequence.
    #    A more direct way to calculate S_n is (count_of_ones - count_of_zeros).
    count_of_ones = sum(bin(byte).count('1') for byte in data)
    count_of_zeros = n - count_of_ones
    s_n = count_of_ones - count_of_zeros

    # 2. Compute the test statistic s_obs.
    s_obs = abs(s_n) / math.sqrt(n)

    # 3. Compute the P-value using the complementary error function (erfc).
    p_value = math.erfc(s_obs / math.sqrt(2))

    # 4. Determine if the test passed.
    passed = (p_value >= significance_level)

    return p_value, passed
