"""
Test ChangeKey by changing Key 0 to the SAME value (factory to factory).

This eliminates any issues with key derivation - if this fails,
ChangeKey command itself has a problem.
"""
import pytest

from ntag424_sdm_provisioner.commands.sdm_commands import SelectPiccApplication
from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession
from ntag424_sdm_provisioner.crypto.crypto_primitives import build_changekey_apdu
from ntag424_sdm_provisioner.sequence_logger import create_sequence_logger
from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager


def test_changekey_same_value():
    """
    Change Key 0 from factory (0x00*16) to factory (0x00*16).
    
    This should work if our crypto is correct.
    """
    
    print("\n=== TESTING CHANGEKEY TO SAME VALUE ===\n")
    
    # Use Simulator
    seq = create_sequence_logger("ChangeKeySameValue")
    with SeritagCardManager(seq) as card:
        # Select and Auth
        print("Step 1: Select and Authenticate...")
        card.send(SelectPiccApplication())
        
        factory_key = bytes(16)
        session = Ntag424AuthSession(factory_key)
        session.authenticate(card, 0)
        
        print(f"  Ti: {session.session_keys.ti.hex()}")
        print(f"  Counter: {session.session_keys.cmd_counter}")
        
        # Change Key 0 to itself
        print("Step 2: ChangeKey(0, factory_key -> factory_key)...")
        
        # Build APDU manually
        apdu = build_changekey_apdu(
            key_no=0,
            new_key=factory_key,  # Same as old!
            old_key=None,
            version=0x00,
            ti=session.session_keys.ti,
            cmd_ctr=session.session_keys.cmd_counter,
            session_enc_key=session.session_keys.session_enc_key,
            session_mac_key=session.session_keys.session_mac_key
        )
        
        print(f"  APDU: {' '.join(f'{b:02X}' for b in apdu[:20])}...")
        
        # Send it
        response, sw1, sw2 = card.send_apdu(apdu, use_escape=True)
        print(f"  Response: SW={sw1:02X}{sw2:02X}")
        
        assert (sw1, sw2) == (0x91, 0x00), f"Failed with {sw1:02X}{sw2:02X}"
