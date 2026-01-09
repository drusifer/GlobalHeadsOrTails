"""Unit tests for crypto components using NXP specification test vectors.

Test vectors from:
- AN12196 Table 26: ChangeKey example (Key 0, counter=3)
- AN12343 Table 40: ChangeKey example (Key 0, counter=0)
"""

import pytest

from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    build_changekey_apdu,
    build_key_data,
    calculate_cmac_full,
    calculate_iv_for_command,
    encrypt_key_data,
    truncate_cmac,
)


class TestAN12196Vectors:
    """Test against AN12196 Table 26 example"""
    
    # Test values from AN12196 Table 26
    TI = bytes.fromhex("7614281A")
    CMD_CTR = 3
    SESSION_ENC_KEY = bytes.fromhex("4CF3CB41A22583A61E89B158D252FC53")
    SESSION_MAC_KEY = bytes.fromhex("5529860B2FC5FB6154B7F28361D30BF9")
    NEW_KEY = bytes.fromhex("5004BF991F408672B1EF00F08F9E8647")
    KEY_VERSION = 0x01
    
    def test_iv_calculation(self):
        """Test IV calculation against AN12196 Step 12"""
        iv = calculate_iv_for_command(self.TI, self.CMD_CTR, self.SESSION_ENC_KEY)
        
        # Expected from AN12196 Step 12
        expected_iv = bytes.fromhex("01602D579423B2797BE8B478B0B4D27B")
        
        assert iv == expected_iv, f"IV mismatch:\nGot:      {iv.hex()}\nExpected: {expected_iv.hex()}"
    
    def test_key_data_format(self):
        """Test key data construction for Key 0"""
        key_data = build_key_data(0, self.NEW_KEY, None, self.KEY_VERSION)
        
        # Expected from AN12196 Step 11
        expected = bytes.fromhex("5004BF991F408672B1EF00F08F9E864701800000000000000000000000000000")
        
        assert key_data == expected, f"Key data mismatch:\nGot:      {key_data.hex()}\nExpected: {expected.hex()}"
    
    def test_encryption(self):
        """Test key data encryption against AN12196 Step 13"""
        plaintext = bytes.fromhex("5004BF991F408672B1EF00F08F9E864701800000000000000000000000000000")
        iv = bytes.fromhex("01602D579423B2797BE8B478B0B4D27B")
        
        encrypted = encrypt_key_data(plaintext, iv, self.SESSION_ENC_KEY)
        
        # Expected from AN12196 Step 13
        expected = bytes.fromhex("C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD")
        
        assert encrypted == expected, f"Encrypted mismatch:\nGot:      {encrypted.hex()}\nExpected: {expected.hex()}"
    
    def test_cmac_full(self):
        """Test full CMAC calculation against AN12196 Step 15"""
        # MAC Input from Step 14: Cmd || CmdCtr || TI || CmdHeader || EncryptedData
        mac_input = bytes.fromhex("C40300" + "7614281A" + "00" + "C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD")
        
        cmac_full = calculate_cmac_full(mac_input, self.SESSION_MAC_KEY)
        
        # Expected from AN12196 Step 15
        expected = bytes.fromhex("B7A60161F202EC3489BD4BEDEF64BB32")
        
        assert cmac_full == expected, f"CMAC full mismatch:\nGot:      {cmac_full.hex()}\nExpected: {expected.hex()}"
    
    def test_cmac_truncation(self):
        """Test CMAC truncation (even-numbered bytes) against AN12196 Step 16"""
        cmac_full = bytes.fromhex("B7A60161F202EC3489BD4BEDEF64BB32")
        
        cmac_truncated = truncate_cmac(cmac_full)
        
        # Expected from AN12196 Step 16: "even-numbered bytes"
        # Indices 1,3,5,7,9,11,13,15: A6 61 02 34 BD ED 64 32
        expected = bytes.fromhex("A6610234BDED6432")
        
        assert cmac_truncated == expected, f"CMAC truncated mismatch:\nGot:      {cmac_truncated.hex()}\nExpected: {expected.hex()}"
    
    def test_complete_changekey_apdu(self):
        """Test complete ChangeKey APDU against AN12196 Step 17"""
        apdu = build_changekey_apdu(
            key_no=0,
            new_key=self.NEW_KEY,
            old_key=None,
            version=self.KEY_VERSION,
            ti=self.TI,
            cmd_ctr=self.CMD_CTR,
            session_enc_key=self.SESSION_ENC_KEY,
            session_mac_key=self.SESSION_MAC_KEY
        )
        
        # Expected from AN12196 Step 17
        # Data portion: KeyNo || Encrypted || CMAC
        expected_data = bytes.fromhex("00" + "C0EB4DEEFEDDF0B513A03A95A75491818580503190D4D05053FF75668A01D6FD" + "A6610234BDED6432")
        
        # Extract data portion from APDU (skip CLA CMD P1 P2 Lc, take until Le)
        apdu_data = bytes(apdu[5:-1])
        
        assert apdu_data == expected_data, f"APDU data mismatch:\nGot:      {apdu_data.hex()}\nExpected: {expected_data.hex()}"
        
        # Verify structure
        assert apdu[0] == 0x90, "CLA should be 0x90"
        assert apdu[1] == 0xC4, "CMD should be 0xC4 (ChangeKey)"
        assert apdu[4] == 0x29, "Lc should be 0x29 (41 bytes)"
        assert len(apdu) == 47, f"APDU should be 47 bytes, got {len(apdu)}"


class TestAN12343Vectors:
    """Test against AN12343 Table 40 example"""
    
    # Test values from AN12343 Table 40
    TI = bytes.fromhex("94297F4D")
    CMD_CTR = 0  # After auth
    SESSION_ENC_KEY = bytes.fromhex("E156C8522F7C8DC82B0C99BA847DE723")
    SESSION_MAC_KEY = bytes.fromhex("45D50C1570000D2F173DF949288E3CAD")
    NEW_KEY = bytes.fromhex("01234567890123456789012345678901")
    KEY_VERSION = 0x00
    
    def test_iv_calculation(self):
        """Test IV calculation against AN12343 Table 40"""
        iv = calculate_iv_for_command(self.TI, self.CMD_CTR, self.SESSION_ENC_KEY)
        
        # Expected from AN12343 Row 18
        expected_iv = bytes.fromhex("BF4A2FB89311ED58E9DCBE56FC17794C")
        
        assert iv == expected_iv, f"IV mismatch:\nGot:      {iv.hex()}\nExpected: {expected_iv.hex()}"
    
    def test_key_data_format(self):
        """Test key data construction for Key 0"""
        key_data = build_key_data(0, self.NEW_KEY, None, self.KEY_VERSION)
        
        # Expected from AN12343 Row 16
        expected = bytes.fromhex("0123456789012345678901234567890100800000000000000000000000000000")
        
        assert key_data == expected, f"Key data mismatch:\nGot:      {key_data.hex()}\nExpected: {expected.hex()}"
    
    def test_encryption(self):
        """Test key data encryption against AN12343 Table 40"""
        plaintext = bytes.fromhex("0123456789012345678901234567890100800000000000000000000000000000")
        iv = bytes.fromhex("BF4A2FB89311ED58E9DCBE56FC17794C")
        
        encrypted = encrypt_key_data(plaintext, iv, self.SESSION_ENC_KEY)
        
        # Expected from AN12343 Row 20
        expected = bytes.fromhex("BF5400DC97A1FBD65BE870716D6F11F8161BB4CA472856DB94AB94B2EC1A13E6")
        
        assert encrypted == expected, f"Encrypted mismatch:\nGot:      {encrypted.hex()}\nExpected: {expected.hex()}"
    
    def test_cmac_truncation_value(self):
        """Test CMAC truncation result against AN12343 Table 40"""
        # MAC Input from Row 22
        mac_input = bytes.fromhex("C40000" + "94297F4D" + "00" + "BF5400DC97A1FBD65BE870716D6F11F8161BB4CA472856DB94AB94B2EC1A13E6")
        
        cmac_full = calculate_cmac_full(mac_input, self.SESSION_MAC_KEY)
        cmac_truncated = truncate_cmac(cmac_full)
        
        # Expected from AN12343 Row 23
        expected = bytes.fromhex("27CE07CF56C11091")
        
        assert cmac_truncated == expected, f"CMAC truncated mismatch:\nGot:      {cmac_truncated.hex()}\nExpected: {expected.hex()}"





if __name__ == '__main__':
    pytest.main([__file__, '-v'])

