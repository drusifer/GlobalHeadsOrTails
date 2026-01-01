"""SUN (Secure Unique NFC) commands for Seritag NTAG424 DNA tags.

SUN is NXP's built-in security feature that provides dynamic authentication
without requiring complex EV2 authentication protocols.
"""

import urllib.parse
from logging import getLogger

from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.constants import SuccessResponse
from ntag424_sdm_provisioner.hal import NTag424CardConnection, hexb


log = getLogger(__name__)


class WriteNdefMessage(ApduCommand):
    """Write NDEF message to NTAG424 DNA tag.

    Uses standard command pattern. HAL automatically handles chunking
    for large writes via connection.send().
    """

    def __init__(self, ndef_data: bytes):
        """Initialize WriteSUN.

        Args:
        ndef_data: Complete NDEF message data to write.
        """
        super().__init__(use_escape=True)
        self.ndef_data = ndef_data

    def __str__(self) -> str:
        return f"WriteNdefMessage(length={len(self.ndef_data)} bytes)"

    def build_apdu(self) -> list:
        """Build APDU for NDEF write.

        Returns UpdateBinary command. HAL will detect large data
        and automatically chunk if needed.
        """
        # ISO UpdateBinary: CLA INS P1 P2 Lc Data
        # P1-P2 encode offset (starts at 0)
        apdu = [
            0x00,  # CLA: ISO7816
            0xD6,  # INS: UpdateBinary
            0x00,  # P1: Offset high byte (0)
            0x00,  # P2: Offset low byte (0)
            len(self.ndef_data) & 0xFF,  # Lc: Length (will be chunked by HAL)
        ] + list(self.ndef_data)

        return apdu

    def parse_response(self, _data: bytes, _sw1: int, _sw2: int) -> SuccessResponse:
        """Parse response after write completes."""
        return SuccessResponse(f"NDEF message written ({len(self.ndef_data)} bytes)")


class ReadNdefMessage(ApduCommand):
    """Read NDEF message from NTAG424 DNA tag.

    This reads the current NDEF data, which may include SUN-generated
    dynamic authentication codes if the tag has been scanned.
    """

    def __init__(self, max_length: int = 256):
        """Initialize ReadSUN.

        Args:
        max_length: Maximum number of bytes to read.
        """
        super().__init__(use_escape=True)
        self.max_length = max_length

    def __str__(self) -> str:
        return f"ReadNdefMessage(max_length={self.max_length})"

    def execute(self, connection: "NTag424CardConnection") -> bytes:
        """Read NDEF message from the tag."""
        # NDEF file is file number 2 (0x02)
        # Build APDU: 00 B0 <offset_high> <offset_low> <length>
        # ISOReadBinary uses CLA=00 (ISO 7816-4 standard), not CLA=90
        offset = 0

        # P1[7]=0: P1-P2 encodes 15-bit offset
        # For offset 0: P1=0x00, P2=0x00
        p1 = (offset >> 8) & 0x7F  # Bit 7 must be 0 for offset mode
        p2 = offset & 0xFF

        apdu = [
            0x00,
            0xB0,  # ISOReadBinary (CLA=00 for ISO standard)
            p1,  # P1 = Offset high bits (bit 7=0)
            p2,  # P2 = Offset low bits
            self.max_length,  # Le = Length to read
        ]

        log.debug(f"ReadNdefMessage APDU: {hexb(apdu)}")

        # Send command
        data, _sw1, _sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)

        return bytes(data)


class ConfigureSunSettings(ApduCommand):
    """Configure SUN (Secure Unique NFC) settings for Seritag tags.

    SUN settings control how dynamic authentication codes are generated
    and appended to NDEF messages.
    """

    def __init__(self, enable_sun: bool = True, sun_options: int = 0x00):
        """Initialize ReadSUN.

        Args:
        enable_sun: Enable SUN dynamic authentication.
        sun_options: SUN configuration options.
        """
        super().__init__(use_escape=True)
        self.enable_sun = enable_sun
        self.sun_options = sun_options

    def __str__(self) -> str:
        return f"ConfigureSunSettings(enable={self.enable_sun}, options=0x{self.sun_options:02X})"

    def execute(self, connection: "NTag424CardConnection") -> SuccessResponse:
        """Configure SUN settings."""
        # Build SUN configuration data
        # ChangeFileSettings format: 90 5F 00 00 [Lc] [FileNo] [FileOption] [AccessRights] [SDMOptions...] 00
        # FileNo must be first byte in data payload!
        file_no = 0x02  # NDEF file

        # FileOption byte (communication mode and file options)
        file_option = 0x00  # Plain communication mode

        # Access rights (4 bytes: Read, Write, ReadWrite, Change)
        # FREE access = 0xEEEE (all Eh = free access)
        access_rights = [0x0E, 0x0E, 0x0E, 0x0E]  # FREE access for all operations

        # SDM/SUN options if enabled
        if self.enable_sun:
            # SDMOptions: 1 byte
            # SMDAccessRights: 1 byte
            # Then SUN-specific options
            sdm_options = [0x01]  # Enable SDM/SUN
            sdm_access = [0x00]  # SDM access rights
            sun_config = [self.sun_options, 0x00, 0x00, 0x00]  # SUN options + reserved
            sdm_data = sdm_options + sdm_access + sun_config
        else:
            sdm_data = []

        # Build data payload: [FileNo] [FileOption] [AccessRights] [SDMOptions...]
        config_data = [file_no, file_option] + access_rights + sdm_data

        # Build APDU: 90 5F 00 00 [Lc] [config_data] 00
        apdu = (
            [
                0x90,
                0x5F,  # ChangeFileSettings command
                0x00,
                0x00,  # P1, P2
                len(config_data),  # Lc = Data length
            ]
            + config_data
            + [0x00]
        )  # Data + Le

        log.debug(f"ConfigureSunSettings APDU: {hexb(apdu)}")

        # Send command
        _, _sw1, _sw2 = self.send_command(connection, apdu, allow_alternative_ok=False)

        return SuccessResponse("SUN settings configured")


def build_ndef_uri_record(url: str) -> bytes:
    """Build NDEF URI record for Type 4 Tags (NTAG424 DNA).

    Type 4 Tag format per ISO 14443-4 / NFC Forum Type 4 Tag spec:
    [NLEN (2 bytes)] + [NDEF Record] (NO TLV wrapper!)

    Args:
        url: Complete URL (including https:// prefix)

    Returns:
        Complete NDEF message ready to write to File 2
    """
    # Strip https:// prefix (replaced by URI identifier 0x04)
    if url.startswith("https://"):
        url_body = url[8:]
        uri_prefix = 0x04
    elif url.startswith("http://"):
        url_body = url[7:]
        uri_prefix = 0x03
    else:
        url_body = url
        uri_prefix = 0x00

    url_bytes = url_body.encode("utf-8")

    # Type 4 Tag NDEF format (NO TLV wrapper):
    # [NLEN_HI] [NLEN_LO] [D1] [01] [PayloadLen] [55] [04] [URL...]
    #
    # NLEN = length of NDEF record (not including NLEN itself)
    payload_len = len(url_bytes) + 1  # +1 for URI prefix byte

    ndef_record = bytes([
        0xD1,        # NDEF Header: MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x01
        0x01,        # Type Length = 1
        payload_len, # Payload length
        0x55,        # Type = 'U' (URI)
        uri_prefix,  # URI prefix code (0x04 = https://)
    ]) + url_bytes

    nlen = len(ndef_record)

    # Build Type 4 Tag format: [NLEN (2 bytes, big-endian)] + [NDEF Record]
    type4_ndef = bytes([
        (nlen >> 8) & 0xFF,  # NLEN high byte
        nlen & 0xFF,         # NLEN low byte
    ]) + ndef_record

    return type4_ndef


def parse_sun_url(url_with_sun: str) -> dict:
    """Parse SUN-enhanced URL to extract authentication data.

    SUN appends parameters like ?uid=XXXX&c=YYYY&mac=ZZZZ to URLs.

    Args:
        url_with_sun: URL that has been enhanced by SUN system

    Returns:
        Dictionary with parsed SUN parameters
    """
    parsed = urllib.parse.urlparse(url_with_sun)
    params = urllib.parse.parse_qs(parsed.query)

    sun_data = {}

    if "uid" in params:
        sun_data["uid"] = params["uid"][0]
    if "c" in params:  # Counter
        sun_data["counter"] = int(params["c"][0], 16)  # type: ignore[assignment]
    if "mac" in params:  # MAC/CMAC
        sun_data["mac"] = params["mac"][0]

    return sun_data
