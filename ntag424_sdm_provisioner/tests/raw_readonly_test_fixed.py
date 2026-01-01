"""
RAW PYSCARD TEST - with CORRECT session key derivation per datasheet.

Implements the CORRECT 32-byte SV formula from NXP datasheet Section 9.1.7:
SV1 = A5||5A||00||01||00||80||RndA[15..14]||(RndA[13..8] XOR RndB[15..10])||RndB[9..0]||RndA[7..0]
"""

import os
from smartcard.System import readers
from smartcard.util import toHexString

# All crypto from verified primitives module
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_cmac,
    derive_session_keys,
    decrypt_rndb,
    rotate_left,
    encrypt_auth_response,
    decrypt_auth_response
)


def test_with_correct_derivation():
    """Test GetKeyVersion with CORRECT session key derivation."""
    
    print("\n" + "="*70)
    print("RAW PYSCARD - CORRECT SESSION KEY DERIVATION")
    print("="*70)
    print()
    
    connection = readers()[0].createConnection()
    connection.connect()
    
    # Select PICC
    apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x90, 0x00):
        return False
    print("Select PICC: [OK]\n")
    
    # Authenticate
    print("Authenticate:")
    factory_key = bytes(16)
    
    # Phase 1
    apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x91, 0xAF):
        return False
    
    # Use crypto_primitives for all auth crypto
    encrypted_rndb = bytes(response[:16])
    rndb = decrypt_rndb(encrypted_rndb, factory_key)
    rndb_rotated = rotate_left(rndb)
    rnda = os.urandom(16)
    
    print(f"  RndA: {rnda.hex()}")
    print(f"  RndB: {rndb.hex()}")
    
    # Phase 2
    encrypted = encrypt_auth_response(rnda, rndb_rotated, factory_key)
    
    apdu = [0x90, 0xAF, 0x00, 0x00, 0x20, *list(encrypted), 0x00]
    response, sw1, sw2 = connection.transmit(apdu)
    if (sw1, sw2) != (0x91, 0x00):
        return False
    
    # Decrypt card response
    response_dec = decrypt_auth_response(bytes(response), factory_key)
    ti = response_dec[0:4]
    
    print(f"  Ti: {ti.hex()}")
    print("  Auth: [OK]\n")
    
    # Derive session keys using crypto_primitives
    print("Session Key Derivation (from crypto_primitives):")
    session_enc_key, session_mac_key = derive_session_keys(factory_key, rnda, rndb)
    
    print(f"  Session ENC: {session_enc_key.hex()}")
    print(f"  Session MAC: {session_mac_key.hex()}\n")
    
    # GetKeyVersion
    print("GetKeyVersion:")
    cmd = 0x64
    cmd_ctr = 0
    key_no = 0
    
    cmac_truncated = calculate_cmac(
        cmd=cmd,
        cmd_ctr=cmd_ctr,
        ti=ti,
        cmd_header=bytes([key_no]),
        encrypted_data=b'',
        session_mac_key=session_mac_key
    )
    
    print(f"  CMAC: {cmac_truncated.hex()}")
    
    apdu = [0x90, cmd, 0x00, 0x00, 0x09, key_no, *list(cmac_truncated), 0x00]
    print(f"  APDU: {toHexString(apdu)}\n")
    
    response, sw1, sw2 = connection.transmit(apdu)
    print(f"  Response: SW={sw1:02X}{sw2:02X}")
    
    if (sw1, sw2) == (0x91, 0x00):
        print("\n" + "="*70)
        print("SUCCESS! GETKEYVERSION WORKED!")
        print("="*70)
        print("\nThe bug was in session key derivation!")
        print("We were using 8-byte SV, should be 32-byte SV with XOR.")
        return True
    else:
        print(f"\n[FAILED] {sw1:02X}{sw2:02X}")
        return False


if __name__ == '__main__':
    success = test_with_correct_derivation()
    exit(0 if success else 1)

