"""
Test session validation by trying a simple authenticated command first.

If GetKeyVersion works but ChangeKey doesn't, the issue is specific to ChangeKey.
If GetKeyVersion also fails, the session itself is broken.
"""
import pytest
from ntag424_sdm_provisioner.commands.base import AuthenticatedConnection, ApduError
from ntag424_sdm_provisioner.commands.sdm_commands import GetKeyVersion, SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.sequence_logger import create_sequence_logger


def test_session_with_simple_command():
    """
    1. Authenticate
    2. Try GetKeyVersion (simple MAC command) to validate the session.
    3. If that works, then try the more complex ChangeKey command.
    
    This helps isolate failures between basic session integrity and
    specific command implementations.
    """
    
    print("\n=== TESTING SESSION VALIDATION ===\n")
    
    seq = create_sequence_logger("SessionValidation")
    with CardManager(seq) as card:
        # Step 1: Select and Authenticate
        print("Step 1: Selecting PICC...")
        card.send(SelectPiccApplication())
        print("  [OK]\n")
        
        print("Step 2: Authenticating...")
        factory_key = bytes(16)
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, 0)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Counter: {session.session_keys.cmd_counter}")
        print("  [OK]\n")
        
        auth_conn = AuthenticatedConnection(card, session)
        
        # Step 3: Try GetKeyVersion (simple command)
        print("Step 3: Testing GetKeyVersion...")
        try:
            version_response = auth_conn.send(GetKeyVersion(0))
            print(f"  Key 0 version: {version_response.version}")
            print(f"  Counter after: {session.session_keys.cmd_counter}")
            print("  [OK] GetKeyVersion worked!")
            print("\nSession is VALID! Authenticated commands work.")
        except ApduError as e:
            pytest.fail(f"GetKeyVersion failed, indicating a broken session or CMAC error: {e}", pytrace=False)
        
        # Step 4: Now try ChangeKey
        print("\nStep 4: Testing ChangeKey...")
        from ntag424_sdm_provisioner.commands.change_key import ChangeKey
        
        new_key = bytes([1] + [0]*15)
        
        try:
            result = auth_conn.send(ChangeKey(0, new_key, None, 0x01))
            print(f"  [OK] ChangeKey worked! {result}")
            print("\n" + "="*60)
            print("SUCCESS! CHANGEKEY WORKED!")
            print("="*60)
        except ApduError as e:
            pytest.fail(
                "GetKeyVersion succeeded but ChangeKey failed. "
                f"The issue is specific to the ChangeKey implementation. Error: {e}",
                pytrace=False
            )
