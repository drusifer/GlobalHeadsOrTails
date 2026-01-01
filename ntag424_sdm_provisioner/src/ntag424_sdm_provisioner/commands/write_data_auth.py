"""WriteDataAuth - Authenticated write to StandardData files.

Uses native WriteData command (0x8D) which supports CommMode.MAC and CommMode.Full.
This is the correct command for authenticated NDEF writes (not ISOUpdateBinary 0xD6).

Per NXP NT4H2421Gx Datasheet Section 10.8.2:
- INS: 0x8D
- Format: [90 8D 00 00 Lc] [FileNo] [Offset:3] [Length:3] [Data] [Le]
- Communication: Per file configuration (Plain/MAC/Full)
"""

from ntag424_sdm_provisioner.commands.base import AuthApduCommand
from ntag424_sdm_provisioner.constants import SuccessResponse


class WriteDataAuth(AuthApduCommand):
    """Native WriteData (0x8D) with CommMode.MAC support.

    APDU Format per Section 10.8.2:
        [90 8D 00 00 Lc] [FileNo] [Offset:3 LSB] [Length:3 LSB] [Data] [MAC:8] [00]

    For CommMode.MAC:
        - Data is sent in plaintext
        - 8-byte truncated CMAC appended
        - MAC covers: CMD || CmdCtr || TI || Header || Data

    Note: WriteData addresses files by FileNo, no prior ISOSelectFile needed.
    """

    def __init__(self, file_no: int, offset: int, data: bytes):
        """Initialize WriteData command.

        Args:
            file_no: Target file number (0x01=CC, 0x02=NDEF, 0x03=Proprietary)
            offset: Byte offset within file (0 to start)
            data: Data to write
        """
        # use_escape=False for transmit mode - supports larger frames than control mode
        # ACR122U control mode limit is ~55 bytes, transmit mode supports up to 248 bytes
        super().__init__(use_escape=False)
        self.file_no = file_no
        self.offset = offset
        self.data = data

    def __str__(self) -> str:
        return (
            f"WriteDataAuth(file=0x{self.file_no:02X}, offset={self.offset}, len={len(self.data)})"
        )

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return f"WriteData (file 0x{self.file_no:02X})"

    @property
    def sequence_description(self) -> str:
        return f"Write {len(self.data)} bytes to file 0x{self.file_no:02X} at offset {self.offset}"

    def get_sequence_params(self) -> dict[str, str]:
        return {
            "file_no": f"0x{self.file_no:02X}",
            "offset": str(self.offset),
            "length": str(len(self.data)),
        }

    # --- AuthApduCommand Implementation ---
    def get_command_byte(self) -> int:
        """INS for WriteData (0x8D)."""
        return 0x8D

    def get_unencrypted_header(self) -> bytes:
        """Build header: FileNo + Offset(3 bytes LSB) + Length(3 bytes LSB).

        Returns 7 bytes total.
        """
        return bytes(
            [
                self.file_no,
                self.offset & 0xFF,
                (self.offset >> 8) & 0xFF,
                (self.offset >> 16) & 0xFF,
                len(self.data) & 0xFF,
                (len(self.data) >> 8) & 0xFF,
                (len(self.data) >> 16) & 0xFF,
            ]
        )

    def needs_encryption(self) -> bool:
        """CommMode.MAC = plaintext data + MAC, no encryption needed.

        For NDEF file with standard SDM config, data is not encrypted,
        only authenticated with CMAC.
        """
        return False

    def build_command_data(self) -> bytes:
        """Return the data payload to write."""
        return self.data

    def parse_response(self, _data: bytes) -> SuccessResponse:
        """WriteData returns no data on success."""
        return SuccessResponse(
            f"WriteData OK ({len(self.data)} bytes to file 0x{self.file_no:02X})"
        )
