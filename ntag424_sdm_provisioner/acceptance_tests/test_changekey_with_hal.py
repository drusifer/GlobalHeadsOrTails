"""
Test ChangeKey using our production auth session but with verified crypto.

This authenticates using our production code, then injects verified crypto for ChangeKey.
"""

import sys
from pathlib import Path

# Add tests directory to path for crypto_components import
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu
from ntag424_sdm_provisioner.sequence_logger import create_sequence_logger
from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager


def test_changekey_after_auth():
    """
    1. Authenticate using our production auth code (we know this works)
    2. Use the session keys from auth
    3. Build ChangeKey APDU using verified crypto primitives
    4. Send it and see if it works
    """
    
    print("\n=== TESTING CHANGEKEY AFTER PRODUCTION AUTH ===\n")
    
    # Use Simulator
    seq = create_sequence_logger("ChangeKeyAfterAuth")
    with SeritagCardManager(seq) as card:
        # Step 1: Select PICC
        print("Step 1: Selecting PICC Application...")
        card.send(SelectPiccApplication())
        print("  [OK] Selected\n")
        
        # Step 2: Authenticate using production code
        print("Step 2: Authenticating with production code...")
        factory_key = bytes(16)
        key_no = 0
        
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, key_no)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Session ENC key: {session.session_keys.session_enc_key.hex()}")
        print(f"  Session MAC key: {session.session_keys.session_mac_key.hex()}")
        print(f"  [OK] Authenticated!\n")
        
        # Step 3: ChangeKey using VERIFIED crypto primitives
        print("Step 3: Executing ChangeKey with verified crypto...")
        
        new_key = bytes([1] + [0]*15)  # Simple test key
        key_version = 0x01
        cmd_ctr = 0  # First command after auth
        
        # Build APDU using VERIFIED crypto from crypto_components
        apdu = build_changekey_apdu(
            key_no=0,
            new_key=new_key,
            old_key=None,
            version=key_version,
            ti=session.session_keys.ti,
            cmd_ctr=cmd_ctr,
            session_enc_key=session.session_keys.session_enc_key,
            session_mac_key=session.session_keys.session_mac_key
        )
        
        print(f"  APDU length: {len(apdu)} bytes")
        print(f"  Full APDU:")
        # Print in lines of 16 bytes
        for i in range(0, len(apdu), 16):
            chunk = apdu[i:i+16]
            print(f"    {' '.join(f'{b:02X}' for b in chunk)}")
        print()
        
        # Send the APDU
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=False)
        
        print(f"  Response: SW={sw1:02X}{sw2:02X}")
        
        if (sw1, sw2) == (0x91, 0x00):
            print("\n" + "="*60)
            print("SUCCESS! CHANGEKEY WORKED!")
            print("="*60)
            print("\nVerified crypto primitives work with real tag!")
            print("Key 0 changed successfully.")
            return True
        else:
            print(f"\n[ERROR] ChangeKey failed with {sw1:02X}{sw2:02X}")
            error_names = {
                0x911E: "INTEGRITY_ERROR - CMAC verification failed",
                0x917E: "LENGTH_ERROR - Wrong data length",
                0x919E: "PARAMETER_ERROR - Invalid parameter",
                0x91AD: "AUTHENTICATION_DELAY - Too many attempts",
            }
            error_code = (sw1 << 8) | sw2
            if error_code in error_names:
                print(f"       ({error_names[error_code]})")
            
            print("\nDespite crypto matching NXP specs, ChangeKey still fails.")
            print("Need to investigate session state or APDU sequence...")
            return False


if __name__ == '__main__':
    try:
        success = test_changekey_after_auth()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

