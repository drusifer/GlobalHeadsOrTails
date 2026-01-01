#!/usr/bin/env python3
"""
Test automatic chunking in HAL layer.

Verifies:
- Small writes (<= 52 bytes) sent as single APDU
- Large writes (> 52 bytes) automatically chunked
- WriteNdefMessage uses standard command pattern
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ntag424_sdm_provisioner.commands.write_ndef_message import WriteNdefMessage
from ntag424_sdm_provisioner.hal import NTag424CardConnection
from ntag424_sdm_provisioner.sequence_logger import create_sequence_logger


class MockConnection:
    """Mock pyscard connection to test chunking detection."""
    
    def __init__(self):
        self.calls = []
        self.last_apdu = None
    
    def control(self, ioctl, apdu):
        """Mock control() for escape commands."""
        return self._mock_transmit(apdu)
    
    def transmit(self, apdu):
        """Mock transmit() for regular commands."""
        return self._mock_transmit(apdu)
    
    def _mock_transmit(self, apdu):
        """Common transmit logic."""
        self.calls.append({
            'apdu': list(apdu),
            'length': len(apdu) - 5 if len(apdu) > 5 else 0
        })
        self.last_apdu = apdu
        # Return success (data, sw1, sw2)
        return ([], 0x90, 0x00)


def test_small_write_no_chunking():
    """Test that small writes (<= 52 bytes) don't chunk."""
    print("\nTest 1: Small write (no chunking needed)")
    print("="*70)
    
    # Create small NDEF message (< 52 bytes)
    small_data = b'\x03\x10\xD1\x01\x0C\x55\x04test.com' + b'\xFE'
    print(f"Data size: {len(small_data)} bytes (< 52, no chunking needed)")
    
    # Create command
    cmd = WriteNdefMessage(small_data)
    apdu = cmd.build_apdu()
    
    print(f"APDU length: {len(apdu)} (header=5 + data={len(small_data)})")
    print(f"INS: 0x{apdu[1]:02X} (UpdateBinary)")
    
    # Verify structure
    assert apdu[0] == 0x00, "CLA should be 0x00"
    assert apdu[1] == 0xD6, "INS should be 0xD6 (UpdateBinary)"
    assert apdu[2] == 0x00, "P1 (offset high) should be 0"
    assert apdu[3] == 0x00, "P2 (offset low) should be 0"
    assert list(apdu[5:]) == list(small_data), "Data should match"
    
    print("[OK] Small write APDU structure correct")
    
    # Check if HAL would chunk this
    seq = create_sequence_logger("AutoChunking")
    conn = NTag424CardConnection(None, seq)
    needs_chunk = conn._needs_chunking(apdu)
    
    print(f"Needs chunking: {needs_chunk}")
    assert not needs_chunk, "Small write should NOT need chunking"
    
    print("[OK] Test passed - small writes not chunked")


def test_large_write_auto_chunking():
    """Test that large writes (> 52 bytes) are automatically chunked."""
    print("\nTest 2: Large write (auto-chunking)")
    print("="*70)
    
    # Create large NDEF message (> 52 bytes)  
    large_url = "https://example.com/very/long/path/that/exceeds/the/chunk/size/limit/for/nfc/readers"
    large_data = b'\x03\x50\xD1\x01\x4C\x55\x04' + large_url.encode() + b'\xFE'
    print(f"Data size: {len(large_data)} bytes (> 52, needs chunking)")
    
    # Create command
    cmd = WriteNdefMessage(large_data)
    apdu = cmd.build_apdu()
    
    print(f"APDU length: {len(apdu)}")
    
    # Check if HAL would chunk this
    seq = create_sequence_logger("AutoChunking")
    conn = NTag424CardConnection(None, seq)
    needs_chunk = conn._needs_chunking(apdu)
    
    print(f"Needs chunking: {needs_chunk}")
    assert needs_chunk, "Large write SHOULD need chunking"
    
    # Verify chunk extraction
    extracted_data = bytes(apdu[5:])
    assert extracted_data == large_data, "Extracted data should match original"
    
    print(f"Would split into ~{(len(large_data) + 51) // 52} chunks of 52 bytes")
    print("[OK] Test passed - large writes detected for chunking")


def test_chunk_extraction():
    """Test that HAL correctly extracts components for chunking."""
    print("\nTest 3: Chunk parameter extraction")
    print("="*70)
    
    # Create large write
    data = b'A' * 100
    cmd = WriteNdefMessage(data)
    apdu = cmd.build_apdu()
    
    # Create real connection with mock send
    mock_conn = MockConnection()
    seq = create_sequence_logger("AutoChunking")
    conn = NTag424CardConnection(mock_conn, seq)
    
    # Call _send_chunked_write directly
    sw1, sw2 = conn._send_chunked_write(apdu, use_escape=True)
    
    print(f"Status: {sw1:02X}{sw2:02X}")
    print(f"APDU calls recorded: {len(mock_conn.calls)}")
    
    # Verify chunks were sent (may include retries, just check > 1)
    assert len(mock_conn.calls) >= 2, f"Should have at least 2 chunk calls (got {len(mock_conn.calls)})"
    
    print(f"[OK] Chunked write executed: {len(mock_conn.calls)} APDU calls")
    print("[OK] Test passed - chunking parameters extracted correctly")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Testing HAL Auto-Chunking")
    print("="*70)
    
    try:
        test_small_write_no_chunking()
        test_large_write_auto_chunking()
        test_chunk_extraction()
        
        print("\n" + "="*70)
        print("[OK] ALL TESTS PASSED")
        print("="*70)
        return 0
    
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

