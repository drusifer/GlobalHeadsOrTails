"""Unit tests for DNA_Calc reference implementation."""

import pytest

from tests.dna_calc_reference import CRC32, DNA_Calc


class TestCRC32:
    """Test CRC32 calculation."""
    
    def test_crc32_empty(self):
        """Test CRC32 of empty data."""
        data = bytearray(16)
        crc = CRC32.calculate(data, 0)
        assert isinstance(crc, int)
        # CRC32 with init=0xFFFFFFFF and final XOR gives specific value
        # For 0 bytes processed, returns ~0xFFFFFFFF = 0x00000000
        assert crc == 0x00000000
    
    def test_crc32_known_value(self):
        """Test CRC32 with known value."""
        # Test with simple data: [1, 0, 0, ..., 0] (16 bytes)
        data = bytearray(16)
        data[0] = 1
        crc = CRC32.calculate(data, 16)
        assert isinstance(crc, int)
        assert crc & 0xFFFFFFFF == crc  # Ensure 32-bit
    
    def test_crc32_length_limit(self):
        """Test that CRC32 respects length parameter."""
        data = bytearray([0xFF] * 32)
        crc1 = CRC32.calculate(data, 16)
        crc2 = CRC32.calculate(data, 32)
        # Different lengths should give different CRCs
        assert crc1 != crc2


class TestDNACalc:
    """Test DNA_Calc class for change key operations."""
    
    @pytest.fixture
    def auth_keys(self):
        """Provide test authentication keys."""
        return {
            'sesAuthEncKey': bytearray(16),  # All zeros for testing
            'sesAuthMacKey': bytearray(16),  # All zeros for testing
            'ti': bytearray([0x12, 0x34, 0x56, 0x78])  # Transaction identifier
        }
    
    @pytest.fixture
    def dna_calc(self, auth_keys):
        """Create DNA_Calc instance."""
        return DNA_Calc(
            auth_keys['sesAuthEncKey'],
            auth_keys['sesAuthMacKey'],
            auth_keys['ti']
        )
    
    def test_init(self, dna_calc):
        """Test DNA_Calc initialization."""
        assert dna_calc.CmdCtr == bytearray([0x00, 0x00])
        assert len(dna_calc.SesAuthEncKey) == 16
        assert len(dna_calc.SesAuthMacKey) == 16
        assert len(dna_calc.TI) == 4
    
    def test_get_full_change_key(self, dna_calc):
        """Test get_full_change_key with default new key."""
        # This should create a key [1, 0, 0, ..., 0]
        result = dna_calc.get_full_change_key()
        assert isinstance(result, (bytes, bytearray))
        assert len(result) == 40  # 32 bytes encrypted data + 8 bytes CMAC
    
    def test_full_change_key_key_number_0(self, auth_keys):
        """Test full_change_key for key number 0 (master key)."""
        dna_calc = DNA_Calc(
            auth_keys['sesAuthEncKey'],
            auth_keys['sesAuthMacKey'],
            auth_keys['ti']
        )
        
        newKey = bytearray(16)
        newKey[0] = 1  # [1, 0, 0, ..., 0]
        newKeyVersion = 1
        
        result = dna_calc.full_change_key(
            keyNumber=0,
            newKey=newKey,
            oldKey=None,
            newKeyVersion=newKeyVersion
        )
        
        assert isinstance(result, (bytes, bytearray))
        assert len(result) == 40  # 32 bytes encrypted data + 8 bytes CMAC
    
    def test_full_change_key_key_number_1(self, auth_keys):
        """Test full_change_key for key number 1 (requires XOR with old key)."""
        dna_calc = DNA_Calc(
            auth_keys['sesAuthEncKey'],
            auth_keys['sesAuthMacKey'],
            auth_keys['ti']
        )
        
        oldKey = bytearray(16)  # All zeros
        newKey = bytearray(16)
        newKey[0] = 1  # [1, 0, 0, ..., 0]
        newKeyVersion = 1
        
        result = dna_calc.full_change_key(
            keyNumber=1,
            newKey=newKey,
            oldKey=oldKey,
            newKeyVersion=newKeyVersion
        )
        
        assert isinstance(result, (bytes, bytearray))
        assert len(result) == 40  # 32 bytes encrypted data + 8 bytes CMAC
