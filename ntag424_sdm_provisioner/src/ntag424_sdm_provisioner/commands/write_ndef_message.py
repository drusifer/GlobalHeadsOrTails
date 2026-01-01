"""WriteNdefMessage - Write NDEF data to tag.

Supports both authenticated and unauthenticated writes.
Connection layer automatically handles chunking for large writes.
"""

import logging

from ntag424_sdm_provisioner.commands.base import (
    ApduCommand,
    AuthApduCommand,
    AuthenticatedConnection,
)
from ntag424_sdm_provisioner.constants import SuccessResponse


log = logging.getLogger(__name__)


class _WriteNdefChunk(AuthApduCommand):
    """(INTERNAL) Command to write a single chunk of NDEF data.

    Uses native WriteData (0x8D) command per NXP Section 10.8.2:
    - Supports CommMode.MAC (required for authenticated writes)
    - Specifies FileNo directly (no ISOSelectFile needed)

    Command format:
      CLA=90, INS=8D, P1=00, P2=00
      Data = FileNo(1) || Offset(3 LE) || Length(3 LE) || Data || MAC(8)
    """

    NDEF_FILE_NO = 0x02  # NDEF file is always file 02

    def __init__(self, offset: int, chunk: bytes, use_escape: bool = True):
        super().__init__(use_escape)
        self._offset = offset
        self._chunk = chunk

    def __str__(self) -> str:
        return f"_WriteNdefChunk(offset={self._offset}, size={len(self._chunk)})"

    def get_command_byte(self) -> int:
        return 0x8D  # WriteData (native NTAG424 command)

    def get_p1(self) -> int:
        return 0x00  # Always 0 for WriteData

    def get_p2(self) -> int:
        return 0x00  # Always 0 for WriteData

    def get_unencrypted_header(self) -> bytes:
        """WriteData header per NXP Section 10.8.2 Table 81.

        FileNo(1) || Offset(3 LE) || Length(3 LE)

        This is included in MAC calculation but NOT encrypted.
        """
        file_no = bytes([self.NDEF_FILE_NO])
        offset_bytes = self._offset.to_bytes(3, byteorder="little")
        length_bytes = len(self._chunk).to_bytes(3, byteorder="little")
        return file_no + offset_bytes + length_bytes

    def needs_encryption(self) -> bool:
        return False  # NDEF file is CommMode.MAC (no encryption)

    def build_command_data(self) -> bytes:
        """Return the actual data to write (goes after header, before MAC)."""
        return self._chunk

    def parse_response(self, _data: bytes) -> None:
        return  # WriteData returns no data on success


class WriteNdefMessage(ApduCommand):
    """Write NDEF message (unauthenticated).

    HAL automatically chunks large writes via connection.send().
    Standard UpdateBinary ISO command.
    """

    def __init__(self, ndef_data: bytes):
        """Initialize WriteNdefMessage.

        Args:
        ndef_data: Complete NDEF message to write.
        """
        super().__init__(use_escape=True)
        self.ndef_data = ndef_data

    def __str__(self) -> str:
        return f"WriteNdefMessage({len(self.ndef_data)} bytes)"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return f"WriteNdefMessage ({len(self.ndef_data)} bytes)"

    @property
    def sequence_description(self) -> str:
        return f"Write {len(self.ndef_data)} bytes of NDEF data"

    def get_sequence_params(self) -> dict[str, str]:
        return {"length": str(len(self.ndef_data))}

    # --- ApduCommand Implementation ---
    def build_apdu(self) -> list:
        """Build UpdateBinary APDU.

        HAL detects large data and automatically chunks if needed.
        This just specifies: write this data at offset 0.
        """
        # ISO UpdateBinary format:
        # [CLA] [INS] [P1=offset_high] [P2=offset_low] [Lc] [Data]

        data_len = len(self.ndef_data)
        lc = data_len if data_len < 256 else 0  # Lc byte (0 means 256)

        # For large writes, HAL will detect and split into chunks automatically
        return [
            0x00,  # CLA: ISO7816
            0xD6,  # INS: UpdateBinary
            0x00,  # P1: Offset high (0)
            0x00,  # P2: Offset low (0)
            lc,  # Lc: Length byte
        ] + list(self.ndef_data)

    def parse_response(self, _data: bytes, _sw1: int, _sw2: int) -> SuccessResponse:
        """Parse response after write."""
        return SuccessResponse(f"NDEF written ({len(self.ndef_data)} bytes)")


class WriteNdefMessageAuth(AuthApduCommand):
    """Write NDEF message (authenticated).

    This uses CommMode.Plain with MAC-only protection. The payload remains
    unencrypted per NT4H2421Gx Section 10.5 (UpdateBinary), but access rights
    enforce that the command is accepted only inside a secure messaging session.
    """

    def __init__(self, ndef_data: bytes):
        super().__init__(use_escape=True)
        self.ndef_data = ndef_data

    def __str__(self) -> str:
        return f"WriteNdefMessageAuth({len(self.ndef_data)} bytes)"

    def execute(self, auth_conn: AuthenticatedConnection) -> SuccessResponse:
        """Execute the chunked write for the NDEF message.

        This overrides the default `send` mechanism to manually handle chunking,
        as the NDEF write command often exceeds single APDU limits.
        """
        log.debug(f"Executing chunked NDEF write for {len(self.ndef_data)} bytes")
        chunk_size = 52  # Conservative chunk size for APDU
        offset = 0
        while offset < len(self.ndef_data):
            chunk = self.ndef_data[offset : offset + chunk_size]
            log.debug(f"Writing NDEF chunk: offset={offset}, size={len(chunk)}")

            chunk_cmd = _WriteNdefChunk(offset, chunk, self.use_escape)
            auth_conn.send(chunk_cmd)  # Use the generic send for each chunk

            offset += len(chunk)

        log.info(
            f"Successfully wrote {len(self.ndef_data)} bytes in {offset // chunk_size + 1} chunks."
        )
        return SuccessResponse(f"NDEF written (auth, {len(self.ndef_data)} bytes)")

    # --- Sequenceable Protocol ---
