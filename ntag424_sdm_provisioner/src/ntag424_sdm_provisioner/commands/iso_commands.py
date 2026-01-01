"""ISO 7816-4 standard commands for NTAG424 DNA.

These commands use CLA=0x00 (ISO7816 class) and follow ISO 7816-4 specification.
"""

from enum import IntEnum

from ntag424_sdm_provisioner.commands.base import ApduCommand, AuthApduCommand
from ntag424_sdm_provisioner.constants import APDUInstruction, SuccessResponse


class ISOFileID(IntEnum):
    """ISO 7816 Elementary File IDs for NTAG424 DNA."""

    CC_FILE = 0xE103  # Capability Container
    NDEF_FILE = 0xE104  # NDEF data file
    PROP_FILE = 0xE105  # Proprietary file

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:04X})"


class ISOSelectFile(AuthApduCommand):
    """ISO 7816-4 SELECT FILE command.

    Wrapped as an AuthApduCommand to allow it to be sent within a secure
    session without breaking the command counter. It is sent with MAC only.
    """

    def __init__(self, file_id: int, use_escape: bool = True):
        super().__init__(use_escape)
        self.file_id = file_id

    def __str__(self) -> str:
        try:
            file_id_enum = ISOFileID(self.file_id)
            return f"ISOSelectFile({file_id_enum})"
        except ValueError:
            return f"ISOSelectFile(0x{self.file_id:04X})"

    def get_cla(self) -> int:
        # Override default of 0x90 for this standard ISO command
        return 0x00

    def get_command_byte(self) -> int:
        return APDUInstruction.SELECT_FILE.value  # 0xA4

    def get_p1(self) -> int:
        return 0x02  # Select EF

    def get_p2(self) -> int:
        return 0x00  # P2

    def needs_encryption(self) -> bool:
        # This command is always plain, but we send it with a MAC to
        # maintain the session counter.
        return False

    def get_unencrypted_header(self) -> bytes:
        # For a plain command sent with a MAC, the entire payload
        # is considered the "unencrypted header" for the MAC calculation.
        file_id_bytes = [
            (self.file_id >> 8) & 0xFF,  # High byte
            self.file_id & 0xFF,  # Low byte
        ]
        return bytes(file_id_bytes)

    def build_command_data(self) -> bytes:
        # The data is moved to the unencrypted header for MAC calculation
        return b""

    def build_apdu(self) -> list[int]:
        """Build APDU for plain (unauthenticated) use with card.send()."""
        file_id_high = (self.file_id >> 8) & 0xFF
        file_id_low = self.file_id & 0xFF
        return [
            0x00,  # CLA: ISO7816
            0xA4,  # INS: SELECT FILE
            0x02,  # P1: Select EF
            0x00,  # P2
            0x02,  # Lc: 2 bytes (file ID)
            file_id_high,
            file_id_low,
            0x00,  # Le
        ]

    def parse_response(self, _data: bytes) -> SuccessResponse:
        """Parse response for both card.send() and auth_conn.send() usage."""
        try:
            file_id_enum = ISOFileID(self.file_id)
            return SuccessResponse(f"{file_id_enum} selected")
        except ValueError:
            return SuccessResponse(f"File 0x{self.file_id:04X} selected")


class ISOReadBinary(ApduCommand):
    """ISO 7816-4 READ BINARY command.

    Reads binary data from the currently selected Elementary File.
    Must call ISOSelectFile first to select the target file.
    """

    def __init__(self, offset: int, length: int, use_escape: bool = True):
        """Initialize IsoReadBinary.

        Args:
        offset: Starting offset in the file (0-based).
        length: Number of bytes to read (max 256).
        use_escape: Whether to use escape command (default True for ACR122U).
        """
        super().__init__(use_escape)
        self.offset = offset
        self.length = length

    def __str__(self) -> str:
        return f"ISOReadBinary(offset={self.offset}, length={self.length})"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return f"ISOReadBinary (offset={self.offset}, len={self.length})"

    @property
    def sequence_description(self) -> str:
        return f"Read {self.length} bytes from offset {self.offset}"

    def get_sequence_params(self) -> dict[str, str]:
        return {"offset": str(self.offset), "length": str(self.length)}

    # --- ApduCommand Implementation ---
    def build_apdu(self) -> list:
        """Build APDU for new connection.send(command) pattern."""
        return [
            0x00,  # CLA: ISO7816
            0xB0,  # INS: READ_BINARY
            (self.offset >> 8) & 0xFF,  # P1: Offset high byte
            self.offset & 0xFF,  # P2: Offset low byte
            self.length if self.length <= 255 else 0,  # Le: Expected length (0=256)
        ]

    def parse_response(self, data: bytes, _sw1: int, _sw2: int) -> bytes:
        """Parse response for new connection.send(command) pattern."""
        return data
