"""
Tests for WriteDataAuth command.

TDD: Write tests first, then implement.
"""

import pytest


class TestWriteDataAuthCommand:
    """Test WriteDataAuth command construction per NXP Section 10.8.2."""

    def test_command_byte_is_0x8D(self):
        """WriteData uses INS=0x8D, not ISOUpdateBinary (0xD6)."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"test")
        assert cmd.get_command_byte() == 0x8D

    def test_header_format_ndef_file(self):
        """Header includes FileNo + Offset(3) + Length(3) in LSB order."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"X" * 80)
        header = cmd.get_unencrypted_header()

        # FileNo(1) + Offset(3 LSB) + Length(3 LSB) = 7 bytes
        assert len(header) == 7
        assert header == bytes([
            0x02,              # FileNo = NDEF file
            0x00, 0x00, 0x00,  # Offset = 0 (LSB first)
            0x50, 0x00, 0x00,  # Length = 80 = 0x50 (LSB first)
        ])

    def test_header_with_offset(self):
        """Test header with non-zero offset."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x02, offset=256, data=b"X" * 10)
        header = cmd.get_unencrypted_header()

        assert header == bytes([
            0x02,              # FileNo
            0x00, 0x01, 0x00,  # Offset = 256 = 0x0100 (LSB first)
            0x0A, 0x00, 0x00,  # Length = 10 = 0x0A (LSB first)
        ])

    def test_needs_encryption_false_for_mac_mode(self):
        """CommMode.MAC = plaintext data + MAC, no encryption."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"test")
        assert cmd.needs_encryption() is False

    def test_build_command_data_returns_payload(self):
        """Command data is the raw NDEF payload."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        ndef_data = b"\x00\x4E\x03\x4B" + b"X" * 76
        cmd = WriteDataAuth(file_no=0x02, offset=0, data=ndef_data)

        assert cmd.build_command_data() == ndef_data

    def test_implements_auth_apdu_command(self):
        """WriteDataAuth must implement AuthApduCommand interface."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth
        from ntag424_sdm_provisioner.commands.base import AuthApduCommand

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"test")
        assert isinstance(cmd, AuthApduCommand)

    def test_implements_sequenceable(self):
        """WriteDataAuth should implement Sequenceable for logging."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"X" * 80)

        assert hasattr(cmd, 'sequence_name')
        assert hasattr(cmd, 'sequence_description')
        assert "WriteData" in cmd.sequence_name
        assert "80" in cmd.sequence_description  # Should mention data length

    def test_parse_response_returns_success(self):
        """Parse response should return SuccessResponse."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth
        from ntag424_sdm_provisioner.constants import SuccessResponse

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"X" * 80)
        result = cmd.parse_response(b"")

        assert isinstance(result, SuccessResponse)


class TestWriteDataAuthFileNumbers:
    """Test different file numbers."""

    def test_ndef_file_0x02(self):
        """NDEF file is 0x02."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"test")
        assert cmd.get_unencrypted_header()[0] == 0x02

    def test_cc_file_0x01(self):
        """CC file is 0x01."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x01, offset=0, data=b"test")
        assert cmd.get_unencrypted_header()[0] == 0x01

    def test_proprietary_file_0x03(self):
        """Proprietary file is 0x03."""
        from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth

        cmd = WriteDataAuth(file_no=0x03, offset=0, data=b"test")
        assert cmd.get_unencrypted_header()[0] == 0x03

