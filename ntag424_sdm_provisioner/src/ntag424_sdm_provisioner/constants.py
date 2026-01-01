from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from logging import getLogger
from typing import Final
from urllib.parse import parse_qs, urlparse

from ntag424_sdm_provisioner.uid_utils import uid_to_asset_tag


log = getLogger(__name__)



def calculate_ntag424_offsets(url_template: str):
    """Calculates the NTAG 424 DNA SDM offsets for a given URL template.

    Assumes standard NDEF File 2 structure with 'https://' prefix.
    """
    # --- CONSTANTS ---
    # 1. The protocol 'https://' is 8 characters.
    #    In NDEF, this is replaced by a single byte (0x04).
    PROTOCOL_STRING = "https://"
    PROTOCOL_LEN = len(PROTOCOL_STRING)
    
    # 2. Type 4 Tag NDEF Header (7 Bytes)
    #    [NLEN_HI] [NLEN_LO] [D1] [01] [PayloadLen] [55] [04]
    #    Type 4 Tag (ISO 14443-4) format - NO TLV wrapper:
    #      - 2 bytes: NLEN (big-endian length of NDEF message)
    #      - 1 byte: D1 = NDEF Record Header (MB=1, ME=1, SR=1, TNF=Well-Known)
    #      - 1 byte: 01 = Type Length
    #      - 1 byte: Payload Length
    #      - 1 byte: 55 = Type 'U' (URI Record)
    #      - 1 byte: 04 = URI Prefix (https://)
    #    NOTE: Type 2 Tags use TLV (03/FE), but Type 4 Tags do NOT!
    NDEF_HEADER_LEN = 7  # Type 4 Tag: 2 (NLEN) + 5 (NDEF record header) 

    # --- VALIDATION ---
    if not url_template.startswith(PROTOCOL_STRING):
        print("Error: URL must start with 'https://' for this calculation.")
        return

    # --- FIND PLACEHOLDERS ---
    # We look for the keys (e.g., 'uid=') and add the length of the key
    # to find where the value (000000...) begins.
    
    try:
        # UID Offset (PICC Data)
        uid_key = "uid="
        uid_start_index = url_template.index(uid_key) + len(uid_key)
        
        # Counter Offset (SDM Read Ctr)
        ctr_key = "ctr="
        ctr_start_index = url_template.index(ctr_key) + len(ctr_key)
        
        # CMAC Offset (SDM MAC)
        cmac_key = "cmac="
        cmac_start_index = url_template.index(cmac_key) + len(cmac_key)
        
    except ValueError as e:
        print(f"Error: Could not find one of the placeholders (uid, ctr, cmac). {e}")
        return

    # --- CALCULATE PHYSICAL FILE OFFSETS ---
    # Formula: Index_in_String - Length_of_Protocol + NDEF_Header_Length
    
    picc_offset = uid_start_index - PROTOCOL_LEN + NDEF_HEADER_LEN
    ctr_offset  = ctr_start_index - PROTOCOL_LEN + NDEF_HEADER_LEN
    cmac_offset = cmac_start_index - PROTOCOL_LEN + NDEF_HEADER_LEN

    # --- OUTPUT ---
    log.debug("-" * 60)
    log.debug(f"URL Template Length: {len(url_template)} chars")
    log.debug("-" * 60)
    log.debug(f"1. SDM Mirror UID Offset (PICC):    {picc_offset}")
    log.debug(f"2. SDM Read Ctr Offset:           {ctr_offset}")
    log.debug(f"3. SDM MAC Offset (CMAC):         {cmac_offset}")
    log.debug("-" * 60)
    log.debug("CRITICAL SETTING:")
    log.debug(f"4. SDM MAC Input Offset:          {picc_offset}")
    log.debug("   (CMAC calculated from UID start to CMAC start)")
    log.debug("-" * 60)
    return SDMOffsets(
        uid_offset=picc_offset,
        picc_data_offset=picc_offset,
        read_ctr_offset=ctr_offset,
        mac_input_offset=picc_offset,  # CMAC starts at UID position
        mac_offset=cmac_offset
    )

# ============================================================================
# Status Words (SW1 SW2)
# ============================================================================


class StatusWord(IntEnum):
    """ISO 7816-4 Status Words.

    Stored as 16-bit value: (SW1 << 8) | SW2.
    """

    # Success
    OK = 0x9000  # Operation successful
    OK_ALTERNATIVE = 0x9100  # Alternative success (some cards)

    # More data available (chaining)
    MORE_DATA_AVAILABLE = 0x91AF  # Additional frame available (DESFire)

    # Warnings
    NO_INFORMATION = 0x6300  # No information given
    FILE_FILLED = 0x6381  # File filled up by last write

    # Execution errors
    AUTHENTICATION_ERROR = 0x6300  # Authentication failed
    WRONG_LENGTH = 0x6700  # Wrong length (Lc or Le)
    SECURITY_STATUS_NOT_SATISFIED = 0x6982  # Security condition not satisfied
    FILE_NOT_FOUND = 0x6A82  # File or application not found
    WRONG_PARAMETERS = 0x6A86  # Incorrect P1 P2
    WRONG_LE_FIELD = 0x6C00  # Wrong Le field
    INS_NOT_SUPPORTED = 0x6D00  # Instruction not supported
    CLA_NOT_SUPPORTED = 0x6E00  # Class not supported
    COMMAND_NOT_ALLOWED = 0x6986  # Command not allowed

    # DESFire specific
    PERMISSION_DENIED = 0x9D00  # Permission denied
    PARAMETER_ERROR = 0x9E00  # Parameter error
    APPLICATION_NOT_FOUND = 0x9DA0  # Application not found
    INTEGRITY_ERROR = 0x9E1E  # Integrity error
    NO_SUCH_KEY = 0x9E40  # Key does not exist
    DUPLICATE_ERROR = 0x9EDE  # Duplicate entry

    # NTAG424 DNA specific (per NXP specification)
    NTAG_INTEGRITY_ERROR = 0x911E  # CRC or MAC does not match data
    NTAG_ILLEGAL_COMMAND_CODE = 0x911C  # Command code not supported
    NTAG_LENGTH_ERROR = 0x917E  # Length of command string invalid
    NTAG_NO_SUCH_KEY = 0x9140  # Invalid key number specified
    NTAG_PERMISSION_DENIED = 0x919D  # Current configuration/status does not allow command
    NTAG_PARAMETER_ERROR = 0x919E  # Value of parameter(s) invalid
    NTAG_AUTHENTICATION_DELAY = 0x91AD  # Currently not allowed to authenticate (delay not spent)
    NTAG_AUTHENTICATION_ERROR = 0x91AE  # Current authentication status does not allow command
    NTAG_BOUNDARY_ERROR = 0x91BE  # Attempt to read/write beyond file limits
    NTAG_COMMAND_ABORTED = 0x91CA  # Previous command was not fully completed (frames missing)
    NTAG_FILE_NOT_FOUND = 0x91F0  # Specified file number does not exist

    @classmethod
    def from_bytes(  # type: ignore[override]
        cls,
        sw1: int | bytes | bytearray,
        sw2: int | None = None,
        byteorder: str = "big",
        *,
        signed: bool = False,
    ) -> "StatusWord":
        """Create StatusWord from SW1 and SW2 bytes.

        Supports both custom two-int usage and standard int.from_bytes().
        """
        if isinstance(sw1, (bytes, bytearray)):
            value = int.from_bytes(sw1, byteorder, signed=signed)  # type: ignore[arg-type]
        elif isinstance(sw1, int) and isinstance(sw2, int):
            value = (sw1 << 8) | sw2
        else:
            raise TypeError(f"Invalid arguments: sw1={type(sw1)}, sw2={type(sw2)}")
        try:
            return cls(value)
        except ValueError:
            return value  # type: ignore[return-value]

    def to_tuple(self) -> tuple[int, int]:
        """Convert to (SW1, SW2) tuple."""
        return (self.value >> 8) & 0xFF, self.value & 0xFF

    def is_success(self) -> bool:
        """Check if status indicates success."""
        return self in [StatusWord.OK, StatusWord.OK_ALTERNATIVE]

    def is_error(self) -> bool:
        """Check if status indicates an error."""
        return not self.is_success() and self != StatusWord.MORE_DATA_AVAILABLE

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:04X})"


class StatusWordPair(Enum):
    """Status word pairs as Enum for better code readability and debugging.

    Each value is a (SW1, SW2) tuple that can be compared directly with tuples.
    """

    # Success codes
    SW_OK = (0x90, 0x00)
    SW_OK_ALTERNATIVE = (0x91, 0x00)

    # Chaining/continuation
    SW_ADDITIONAL_FRAME = (0x91, 0xAF)

    # Common errors
    SW_AUTH_FAILED = (0x91, 0x7E)
    SW_OPERATION_FAILED = (0x63, 0x00)
    SW_WRONG_LENGTH = (0x67, 0x00)
    SW_FUNC_NOT_SUPPORTED = (0x6A, 0x81)
    SW_FILE_NOT_FOUND = (0x6A, 0x82)

    def __eq__(self, other):
        """Allow comparison with tuples: if (sw1, sw2) == StatusWordPair.SW_OK."""
        if isinstance(other, tuple) and len(other) == 2:
            return self.value == other
        return super().__eq__(other)

    def __hash__(self):
        """Make hashable for use in sets/dicts."""
        return hash(self.value)

    def to_status_word(self) -> StatusWord:
        """Convert to StatusWord enum."""
        sw1, sw2 = self.value
        return StatusWord.from_bytes(sw1, sw2)

    def __str__(self) -> str:
        sw1, sw2 = self.value
        return f"{self.name} (0x{sw1:02X}{sw2:02X})"

    def __repr__(self) -> str:
        return f"StatusWordPair.{self.name}"


# Export enum members as module-level constants for backward compatibility
SW_OK = StatusWordPair.SW_OK
SW_OK_ALTERNATIVE = StatusWordPair.SW_OK_ALTERNATIVE
SW_ADDITIONAL_FRAME = StatusWordPair.SW_ADDITIONAL_FRAME
SW_AUTH_FAILED = StatusWordPair.SW_AUTH_FAILED
SW_OPERATION_FAILED = StatusWordPair.SW_OPERATION_FAILED
SW_WRONG_LENGTH = StatusWordPair.SW_WRONG_LENGTH
SW_FUNC_NOT_SUPPORTED = StatusWordPair.SW_FUNC_NOT_SUPPORTED
SW_FILE_NOT_FOUND = StatusWordPair.SW_FILE_NOT_FOUND


# ============================================================================
# APDU Command Codes
# ============================================================================


class APDUClass(IntEnum):
    """APDU Class bytes."""

    ISO7816 = 0x00  # Standard ISO 7816-4
    PROPRIETARY = 0x80  # Proprietary class
    DESFIRE = 0x90  # DESFire native


class APDUInstruction(IntEnum):
    """APDU Instruction bytes (INS) for NTAG424 DNA commands."""

    # ISO 7816-4 standard commands
    SELECT_FILE = 0xA4  # ISO 7816-4 SELECT FILE

    # NTAG424 DNA specific commands
    AUTHENTICATE_EV2_FIRST = 0x71  # AuthenticateEV2First Phase 1
    AUTHENTICATE_EV2_NONFIRST = 0x77  # AuthenticateEV2NonFirst Phase 1
    AUTHENTICATE_PHASE2 = 0xAF  # Authenticate Phase 2 (common)
    CHANGE_FILE_SETTINGS = 0x5F  # ChangeFileSettings
    CHANGE_KEY = 0xC4  # ChangeKey
    GET_FILE_COUNTERS = 0xC1  # GetFileCounters

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# Tag Status
# ============================================================================


class TagStatus(Enum):
    """Status of an NTAG424 DNA tag relative to our provisioning system."""

    FACTORY = "factory"  # Tag has factory default keys
    PROVISIONED = "provisioned"  # Tag has been provisioned with custom keys
    UNKNOWN = "unknown"  # Unable to determine status


# ============================================================================
# File Numbers
# ============================================================================


class FileNo(IntEnum):
    """File numbers for NTAG424 DNA files."""

    CC_FILE = 0x01  # Capability Container file
    NDEF_FILE = 0x02  # NDEF file (File 2)
    PROPRIETARY_FILE = 0x03  # Proprietary file (File 3)


# ============================================================================
# File Types
# ============================================================================


class FileType(IntEnum):
    """File types for NTAG424 DNA."""

    STANDARD_DATA = 0x00  # Standard data file
    BACKUP_DATA = 0x01  # Backup data file
    VALUE = 0x02  # Value file
    LINEAR_RECORD = 0x03  # Linear record file
    CYCLIC_RECORD = 0x04  # Cyclic record file


# ============================================================================
# Access Rights
# ============================================================================


class AccessRight(IntEnum):
    """Access condition values for NTAG424 DNA files.

    Values 0x0-0x4: Key number (0-4)
    Value 0xE: Free access
    Value 0xF: No access / RFU
    """

    KEY_0 = 0x0
    KEY_1 = 0x1
    KEY_2 = 0x2
    KEY_3 = 0x3
    KEY_4 = 0x4
    FREE = 0xE
    NEVER = 0xF


@dataclass
class AccessRights:
    """NTAG424 DNA access rights (2 bytes / 4 nibbles).

    Byte layout:
        Byte 1 [7:4]: Read access
        Byte 1 [3:0]: Write access
        Byte 0 [7:4]: ReadWrite access
        Byte 0 [3:0]: Change access (ChangeFileSettings)
    """

    read: AccessRight = AccessRight.FREE
    write: AccessRight = AccessRight.KEY_0
    read_write: AccessRight = AccessRight.FREE
    change: AccessRight = AccessRight.KEY_0

    def __post_init__(self):
        """Convert int values to AccessRight enums if needed."""
        for field in ["read", "write", "read_write", "change"]:
            val = getattr(self, field)
            if not isinstance(val, AccessRight):
                setattr(self, field, AccessRight(val))

    def to_bytes(self) -> bytes:
        """Convert to NTAG424 2-byte format.

        Wire format (transmission order):
        - First byte:  [Read|Write]     (Byte 1 in spec)
        - Second byte: [ReadWrite|Change] (Byte 0 in spec)

        CRITICAL FIX (2025-12-07): Fixed endianness - was returning [byte0, byte1]
        but should be [byte1, byte0] to match wire protocol. This caused
        PARAMETER_ERROR (0x919E) in ChangeFileSettings.
        """
        byte0 = (self.read_write << 4) | self.change  # RW|Change
        byte1 = (self.read << 4) | self.write          # Read|Write
        return bytes([byte1, byte0])  # Wire order: byte1 first!

    @classmethod
    def from_bytes(cls, data: bytes) -> "AccessRights":
        """Parse from 2-byte format.

        CRITICAL FIX (2025-12-07): Updated to match corrected to_bytes() endianness.
        Wire format: [byte1, byte0] = [Read|Write, ReadWrite|Change]
        """
        if len(data) != 2:
            raise ValueError("Access rights must be 2 bytes")

        byte1, byte0 = data  # Wire order: [byte1, byte0]

        return cls(
            read=AccessRight((byte1 >> 4) & 0xF),
            write=AccessRight(byte1 & 0xF),
            read_write=AccessRight((byte0 >> 4) & 0xF),
            change=AccessRight(byte0 & 0xF),
        )

    def __str__(self) -> str:
        return (
            f"Read={self.read.name}, "
            f"Write={self.write.name}, "
            f"RW={self.read_write.name}, "
            f"Change={self.change.name}"
        )


# ============================================================================
# Access Rights Presets
# ============================================================================


class AccessRightsPresets:
    """Common access rights configurations."""

    FREE_READ_KEY0_WRITE = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.KEY_0,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE,
    )

    KEY0_ALL = AccessRights(
        read=AccessRight.KEY_0,
        write=AccessRight.KEY_0,
        read_write=AccessRight.KEY_0,
        change=AccessRight.KEY_0,
    )

    FREE_ALL = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.FREE,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE,
    )

    READ_ONLY_FREE = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.NEVER,
        read_write=AccessRight.NEVER,
        change=AccessRight.NEVER,
    )


# ============================================================================
# Communication Modes
# ============================================================================


class CommMode(IntEnum):
    """Communication modes for file access.

    Defines the level of security for communication between PCD and PICC.
    Stored in bits [1:0] of FileOption byte.
    """

    PLAIN = 0x00  # No protection: message transmitted in plain text
    MAC = 0x01  # MAC protection for integrity and authenticity
    FULL = 0x03  # Full protection: integrity, authenticity, and confidentiality

    def requires_auth(self) -> bool:
        """Check if this mode requires authentication."""
        return self in [CommMode.MAC, CommMode.FULL]

    @classmethod
    def from_file_option(cls, file_option: int) -> "CommMode":
        """Extract CommMode from FileOption byte (bits [1:0])."""
        return cls(file_option & 0x03)

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# SDM Options
# ============================================================================


class SDMOption(IntFlag):
    """SDM configuration options (bit flags).

    Can be combined using bitwise OR: SDMOption.ENABLED | SDMOption.UID_MIRROR.
    """

    NONE = 0x00
    ENCODING_ASCII = 0x01  # Bit 0: ASCII encoding
    ENC_FILE_DATA = 0x10  # Bit 4: Encrypt file data
    READ_COUNTER_LIMIT = 0x20  # Bit 5: Enable counter limit
    READ_COUNTER = 0x40  # Bit 6: Mirror read counter (FIXED!)
    UID_MIRROR = 0x80  # Bit 7: Mirror UID in NDEF

    # Common combinations (Note: ENABLED goes in FileOption, not SDMOption!)
    BASIC_SDM = UID_MIRROR
    SDM_WITH_COUNTER = UID_MIRROR | READ_COUNTER


# ============================================================================
# NDEF Constants
# ============================================================================


class NdefUriPrefix(IntEnum):
    """NDEF URI identifier codes."""

    NONE = 0x00
    HTTP_WWW = 0x01  # http://www.
    HTTPS_WWW = 0x02  # https://www.
    HTTP = 0x03  # http://
    HTTPS = 0x04  # https://
    TEL = 0x05  # tel:
    MAILTO = 0x06  # mailto:
    FTP_ANON = 0x0D  # ftp://anonymous:anonymous@
    FTP = 0x0E  # ftp://
    FTPS = 0x0F  # ftps://
    SFTP = 0x10  # sftp://

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"

    def to_prefix_string(self) -> str:
        """Convert prefix code to actual URL prefix string."""
        prefix_strings = {
            NdefUriPrefix.NONE: "",
            NdefUriPrefix.HTTP_WWW: "http://www.",
            NdefUriPrefix.HTTPS_WWW: "https://www.",
            NdefUriPrefix.HTTP: "http://",
            NdefUriPrefix.HTTPS: "https://",
            NdefUriPrefix.TEL: "tel:",
            NdefUriPrefix.MAILTO: "mailto:",
            NdefUriPrefix.FTP_ANON: "ftp://anonymous:anonymous@",
            NdefUriPrefix.FTP: "ftp://",
            NdefUriPrefix.FTPS: "ftps://",
            NdefUriPrefix.SFTP: "sftp://",
        }
        return prefix_strings.get(self, "")


class NdefRecordType(IntEnum):
    """NDEF Record Type Name Format (TNF)."""

    EMPTY = 0x00
    WELL_KNOWN = 0x01  # NFC Forum well-known type
    MIME_MEDIA = 0x02
    ABSOLUTE_URI = 0x03
    EXTERNAL = 0x04
    UNKNOWN = 0x05
    UNCHANGED = 0x06
    RESERVED = 0x07

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class NdefTLV(IntEnum):
    """NDEF TLV types for Type 4 Tags."""

    NULL = 0x00
    LOCK_CONTROL = 0x01
    MEMORY_CONTROL = 0x02
    NDEF_MESSAGE = 0x03
    PROPRIETARY = 0xFD
    TERMINATOR = 0xFE

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class NdefRecordHeader(IntEnum):
    """NDEF Record Header flags (first byte of NDEF record).

    Standard URI record header for Android NFC:
    - MB (Message Begin) = 1
    - ME (Message End) = 1
    - SR (Short Record) = 1
    - TNF (Type Name Format) = 1 (Well-Known)
    Result: 0xD1
    """
    URI_SHORT_SINGLE = 0xD1  # MB=1, ME=1, SR=1, TNF=Well-Known

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class NdefWellKnownType(IntEnum):
    """NDEF Well-Known Type values."""

    TEXT = 0x54  # 'T'
    URI = 0x55   # 'U'
    SMART_POSTER = 0x53  # 'S'

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


class CCFileTLV(IntEnum):
    """Capability Container File TLV types."""

    NDEF_FILE_CONTROL = 0x04  # Points to NDEF file (File 2)
    PROPRIETARY_FILE_CONTROL = 0x05  # Points to proprietary file (File 3)

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# ============================================================================
# Memory Sizes
# ============================================================================


class MemorySize:
    """Standard memory sizes for NTAG424 DNA variants."""

    NTAG424_DNA = 416  # 416 bytes user memory
    NTAG424_DNA_TT = 416  # TamperTag variant


# ============================================================================
# Application IDs
# ============================================================================


class ApplicationID:
    """Application IDs for NTAG424 DNA."""

    PICC_APP: Final[bytes] = b"\x00\x00\x00"  # Main PICC application


# ============================================================================
# Error Categories
# ============================================================================


class ErrorCategory(IntEnum):
    """Categories of errors for better error handling."""

    COMMUNICATION = 1  # Reader/card communication error
    AUTHENTICATION = 2  # Authentication failed
    PERMISSION = 3  # Permission denied
    PARAMETER = 4  # Invalid parameter
    STATE = 5  # Invalid state for operation
    INTEGRITY = 6  # Data integrity error
    NOT_FOUND = 7  # File/app not found
    HARDWARE = 8  # Hardware error

    def __str__(self) -> str:
        return f"{self.name} (0x{self.value:02X})"


# Map status words to error categories
STATUS_WORD_CATEGORIES = {
    StatusWord.AUTHENTICATION_ERROR: ErrorCategory.AUTHENTICATION,
    StatusWord.PERMISSION_DENIED: ErrorCategory.PERMISSION,
    StatusWord.SECURITY_STATUS_NOT_SATISFIED: ErrorCategory.AUTHENTICATION,
    StatusWord.FILE_NOT_FOUND: ErrorCategory.NOT_FOUND,
    StatusWord.APPLICATION_NOT_FOUND: ErrorCategory.NOT_FOUND,
    StatusWord.WRONG_PARAMETERS: ErrorCategory.PARAMETER,
    StatusWord.PARAMETER_ERROR: ErrorCategory.PARAMETER,
    StatusWord.WRONG_LENGTH: ErrorCategory.PARAMETER,
    StatusWord.COMMAND_NOT_ALLOWED: ErrorCategory.STATE,
    StatusWord.INTEGRITY_ERROR: ErrorCategory.INTEGRITY,
    StatusWord.NO_SUCH_KEY: ErrorCategory.NOT_FOUND,
    # NTAG424 DNA specific mappings
    StatusWord.NTAG_INTEGRITY_ERROR: ErrorCategory.INTEGRITY,
    StatusWord.NTAG_ILLEGAL_COMMAND_CODE: ErrorCategory.COMMUNICATION,
    StatusWord.NTAG_LENGTH_ERROR: ErrorCategory.PARAMETER,
    StatusWord.NTAG_NO_SUCH_KEY: ErrorCategory.NOT_FOUND,
    StatusWord.NTAG_PERMISSION_DENIED: ErrorCategory.PERMISSION,
    StatusWord.NTAG_PARAMETER_ERROR: ErrorCategory.PARAMETER,
    StatusWord.NTAG_AUTHENTICATION_DELAY: ErrorCategory.STATE,
    StatusWord.NTAG_AUTHENTICATION_ERROR: ErrorCategory.AUTHENTICATION,
    StatusWord.NTAG_BOUNDARY_ERROR: ErrorCategory.PARAMETER,
    StatusWord.NTAG_COMMAND_ABORTED: ErrorCategory.STATE,
    StatusWord.NTAG_FILE_NOT_FOUND: ErrorCategory.NOT_FOUND,
}


def get_error_category(sw: StatusWord) -> ErrorCategory:
    """Get error category for a status word."""
    return STATUS_WORD_CATEGORIES.get(sw, ErrorCategory.COMMUNICATION)


# ============================================================================
# Response Dataclasses
# ============================================================================


@dataclass
class SuccessResponse:
    """Response for successful operations."""

    message: str

    def __str__(self) -> str:
        return f"SuccessResponse(message='{self.message}')"


@dataclass
class AuthenticationChallengeResponse:
    """Response from EV2 authentication first phase."""

    key_no_used: int
    challenge: bytes

    def __str__(self) -> str:
        return f"AuthenticationChallengeResponse(key_no={self.key_no_used}, challenge={self.challenge.hex().upper()})"


@dataclass
class AuthenticationResponse:
    """Response from EV2 authentication second phase."""

    ti: bytes  # Transaction Identifier (4 bytes)
    rnda_rotated: bytes  # RndA rotated by tag (16 bytes)
    pdcap: bytes  # PICC Data Capabilities (variable length)
    pcdcap: bytes  # PCD Capabilities (variable length)

    def __str__(self) -> str:
        return f"AuthenticationResponse(ti={self.ti.hex().upper()}, rnda_rotated={self.rnda_rotated.hex().upper()[:8]}..., pdcap_len={len(self.pdcap)}, pcdcap_len={len(self.pcdcap)})"


# NOTE: Ntag424VersionInfo moved to commands/get_chip_version.py
# Import directly: from ntag424_sdm_provisioner.commands.get_chip_version import Ntag424VersionInfo


@dataclass
class Ntag424VersionInfo:
    """Version information from NTAG424 DNA chip."""

    hw_vendor_id: int
    hw_type: int
    hw_subtype: int
    hw_major_version: int
    hw_minor_version: int
    hw_storage_size: int
    hw_protocol: int
    sw_vendor_id: int
    sw_type: int
    sw_subtype: int
    sw_major_version: int
    sw_minor_version: int
    sw_storage_size: int
    sw_protocol: int
    uid: bytes
    batch_no: bytes
    fab_week: int
    fab_year: int

    def __str__(self) -> str:
        asset_tag = uid_to_asset_tag(self.uid)
        return (
            f"Ntag424VersionInfo(\n"
            f"  UID: {self.uid.hex().upper()} [Tag: {asset_tag}],\n"
            f"  Hardware: {self.hw_major_version}.{self.hw_minor_version} ({self.hw_storage_size}B),\n"
            f"  Software: {self.sw_major_version}.{self.sw_minor_version} ({self.sw_storage_size}B),\n"
            f"  Batch: {self.batch_no.hex().upper()},\n"
            f"  Fab: Week {self.fab_week}, Year {self.fab_year}\n"
            f"  {'=' * 60}\n"
            f"\n"
            f"CHIP INFORMATION:\n"
            f"  UID: {self.uid.hex().upper()}\n"
            f"  Asset Tag: {asset_tag} <- Write on label\n"
            f"  Hardware Protocol: {self.hw_protocol}\n"
            f"  Software Protocol: {self.sw_protocol}\n"
            f"  Hardware Type: {self.hw_type}\n"
            f"  Software Type: {self.sw_type}\n"
            f"\n"
            f")"
        )


@dataclass
class ReadDataResponse:
    """Response from file read operations."""

    file_no: int
    offset: int
    data: bytes

    cmd_counter: int = 0

    def __str__(self) -> str:
        return f"ReadDataResponse(file_no={self.file_no}, offset={self.offset}, data_len={len(self.data)}, data={self.data.hex().upper()[:32]}{'...' if len(self.data) > 16 else ''})"


# ============================================================================
# File Options
# ============================================================================


class FileOption(IntFlag):
    """File option flags for SDM configuration.

    Note: These combine FileOption byte (bits 1-0 = CommMode, bit 6 = SDM enable)
    with SDMOptions byte (bits for UID/counter mirroring).

    FileOption byte:
    - Bit 6: SDM enabled (0x40)
    - Bits 1-0: CommMode

    SDMOptions byte:
    - Bit 7: UID mirror (0x80)
    - Bit 6: Read counter (0x40)
    - Bit 5: Counter limit (0x20)
    - Bit 4: Encrypt file data (0x10)
    """

    SDM_ENABLED = 0x40  # FileOption bit 6
    UID_MIRROR = 0x80  # SDMOptions bit 7
    READ_COUNTER = 0x40  # SDMOptions bit 6 (FIXED from 0x20!)
    READ_COUNTER_LIMIT = 0x20  # SDMOptions bit 5
    ENC_FILE_DATA = 0x10  # SDMOptions bit 4


@dataclass
class FileSettingsResponse:
    """Response from GetFileSettings command."""

    file_no: int
    file_type: int
    file_option: int
    access_rights: bytes
    file_size: int
    sdm_options: int | None = None
    sdm_access_rights: bytes | None = None
    uid_offset: int | None = None
    read_ctr_offset: int | None = None
    picc_data_offset: int | None = None
    mac_input_offset: int | None = None
    enc_offset: int | None = None
    enc_length: int | None = None
    mac_offset: int | None = None
    read_ctr_limit: int | None = None

    def get_comm_mode(self) -> "CommMode":
        """Get the communication mode for this file.

        Extracts CommMode from file_option bits [1:0].

        Returns:
            CommMode enum value (PLAIN, MAC, or FULL)
        """
        return CommMode.from_file_option(self.file_option)

    def requires_authentication(self) -> bool:
        """Check if this file requires authentication for access.

        Returns:
            True if CommMode is MAC or FULL
        """
        return self.get_comm_mode().requires_auth()

    def __str__(self) -> str:
        lines = [
            f"File 0x{self.file_no:02X} Settings:",
            f"  File Type: 0x{self.file_type:02X} ({FileType(self.file_type).name if self.file_type in [ft.value for ft in FileType] else 'UNKNOWN'})",
            f"  File Option: 0x{self.file_option:02X}",
            f"  Comm Mode: {self.get_comm_mode()}",
            f"  File Size: {self.file_size} bytes",
        ]

        # Parse and display access rights
        lines.append(f"  Access Rights: {self.access_rights.hex().upper()}")
        try:
            access_rights = AccessRights.from_bytes(self.access_rights)
            lines.append(f"    Read:      {access_rights.read.name} (0x{access_rights.read:X})")
            lines.append(f"    Write:     {access_rights.write.name} (0x{access_rights.write:X})")
            lines.append(f"    ReadWrite: {access_rights.read_write.name} (0x{access_rights.read_write:X})")
            lines.append(f"    Change:    {access_rights.change.name} (0x{access_rights.change:X})")
        except Exception as e:
            lines.append(f"    (Could not parse: {e})")

        # SDM information
        sdm_enabled = bool(self.file_option & FileOption.SDM_ENABLED)
        lines.append(f"  SDM Enabled: {'YES' if sdm_enabled else 'NO'}")

        if sdm_enabled and self.sdm_options is not None:
            lines.append(f"  SDM Options: 0x{self.sdm_options:02X}")

            # Decode SDM options
            sdm_features = []
            if self.sdm_options & FileOption.UID_MIRROR:
                sdm_features.append("UID")
            if self.sdm_options & FileOption.READ_COUNTER:
                sdm_features.append("Counter")
            if self.sdm_options & 0x01:  # ASCII encoding
                sdm_features.append("ASCII")
            if sdm_features:
                lines.append(f"    Features: {', '.join(sdm_features)}")

            if self.sdm_access_rights:
                lines.append(f"  SDM Access Rights: {self.sdm_access_rights.hex().upper()}")
                # Parse SDM access rights
                try:
                    meta_read = (self.sdm_access_rights[1] >> 4) & 0x0F
                    file_read = self.sdm_access_rights[1] & 0x0F
                    ctr_ret = (self.sdm_access_rights[0] >> 4) & 0x0F
                    lines.append(
                        f"    MetaRead:  {AccessRight(meta_read).name} (0x{meta_read:01X})"
                    )
                    lines.append(
                        f"    FileRead:  {AccessRight(file_read).name} (0x{file_read:01X})"
                    )
                    lines.append(f"    CtrRet:    {AccessRight(ctr_ret).name} (0x{ctr_ret:01X})")
                except Exception:
                    pass

            if self.uid_offset is not None:
                lines.append(f"  UID Offset: {self.uid_offset}")
            if self.read_ctr_offset is not None:
                lines.append(f"  Read Counter Offset: {self.read_ctr_offset}")
            if self.picc_data_offset is not None:
                lines.append(f"  PICC Data Offset: {self.picc_data_offset}")
            if self.mac_input_offset is not None:
                lines.append(f"  MAC Input Offset: {self.mac_input_offset}")
            if self.enc_offset is not None:
                lines.append(f"  Encryption Offset: {self.enc_offset}")
                if self.enc_length is not None:
                    lines.append(f"  Encryption Length: {self.enc_length}")
            if self.mac_offset is not None:
                lines.append(f"  MAC Offset: {self.mac_offset}")
            if self.read_ctr_limit is not None:
                lines.append(f"  Read Counter Limit: {self.read_ctr_limit}")

        return "\n".join(lines)


@dataclass
class KeyVersionResponse:
    """Response from GetKeyVersion command."""

    key_no: int
    version: int

    def __str__(self) -> str:
        return f"Key 0x{self.key_no:02X} Version: 0x{self.version:02X}"


# ============================================================================
# Configuration Dataclasses
# ============================================================================


@dataclass
class SDMOffsets:
    """SDM offset configuration with sane defaults."""

    uid_offset: int = 0
    read_ctr_offset: int = 0
    picc_data_offset: int = 0
    mac_input_offset: int = 0
    mac_offset: int = 0
    enc_offset: int = 0

class SDMUrl:
    """SDM-enabled URL with parameters."""

    def __init__(self, base_url: str, uid: str, read_ctr: str, cmac: str, enc: str = ""):
        self.base_url = base_url
        self.uid = uid
        self.read_ctr = read_ctr
        self.cmac = cmac
        self.enc = enc

    @classmethod
    def from_url(cls, url: str) -> "SDMUrl":
        """Create a template from an existing SDM URL.

        Extracts the base URL and placeholders from a real SDM URL.

        Args:
            url: SDM URL from tag scan (e.g., "https://example.com?uid=...&ctr=...&cmac=...")

        Returns:
            SDMUrl with extracted base URL and placeholder patterns
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Extract base URL (scheme + netloc + path)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return cls(
            base_url=base_url,
            uid = params["uid"][0],
            read_ctr = params["ctr"][0],
            enc = params.get("enc", [''])[0],  # May not be present
            cmac = params.get("cmac")[0]  # May not be present 
        )

    def __str__(self) -> str:
        return (
            f"SDMUrl(\n"
            f"  URL: {self.generate_url()}\n"
            f"  UID: {self.uid}\n"
            f"  Read Counter: {self.read_ctr}\n"
            f"  CMAC: {self.cmac}\n"
            f"  Encrypted Data: {self.enc}\n"
            f")"
        )
        
    def generate_url( self ) -> str:
        """Generate a complete URL with provided values or placeholders.

        Args:
            uid: UID string (14 hex chars), defaults to placeholder
            read_ctr: Read counter value, defaults to placeholder as int
            cmac: CMAC string (16 hex chars), defaults to placeholder
            enc_data: Encrypted data string (optional)

        Returns:
            Complete URL string
        """
        enc_str = f"&enc={self.enc}" if self.enc else ""
        url = f"{self.base_url}?uid={self.uid}&ctr={self.read_ctr}{enc_str}&cmac={self.cmac}"
        log.debug(f"URL is: {url}")
        return url

    def calculate_offsets(self) -> SDMOffsets:
        """Calculate SDM offsets based on URL template structure.

        The offsets are byte positions in the NDEF file where SDM data (UID, Counter, CMAC)
        will be dynamically injected by the tag when scanned.

        Returns:
            SDMOffsets with calculated byte positions for SDM parameters
        """
        # Build full URL with correct parameter order: uid, ctr, cmac
        full_url = self.generate_url()
        log.debug(f"[SDM Offsets] Full Template URL: {full_url[:256]}...")


        offsets = calculate_ntag424_offsets(full_url)

        log.info(f"[SDM Offsets] Calculated offsets: {offsets=}")

        return offsets

    def build_cmac_message(self) -> bytes:
        """Build the message for CMAC calculation based on URL structure.

        Per NTAG424 DNA spec Section 9.3.8.1:
        SDMMAC = MACt(SesSDMFileReadMACKey; DynamicFileData[SDMMACInputOffset ... SDMMACOffset - 1])

        Where DynamicFileData is the NDEF file content with UID and Counter already replaced.
        The message is built by reconstructing the parameter string in the exact order they
        appear in the URL: uid_value&ctr=ctr_value&cmac=

        The NDEF file stores URLs WITHOUT the https:// prefix (replaced by code 0x04).

        Args:
            uid: Tag UID bytes (7 bytes) - not used, kept for compatibility
            counter: Read counter bytes (3 bytes) - not used, kept for compatibility
            url: Full SDM URL from tag scan with real UID, Counter, and CMAC values

        Returns:
            Message bytes ready for CMAC calculation: UID_value&ctr=CTR_value&cmac=
        """
        # Rebuild the message portion as it appears in the NDEF file
        # From SDMMACInputOffset (UID value) to SDMMACOffset-1 (just before CMAC value)
        # Format: UID_value&ctr=CTR_value&enc=ENC_value&cmac= (enc is optional)

        # Only include &enc= if enc data is present
        enc_str = f"&enc={self.enc}" if self.enc else ""
        message = f"{self.uid}&ctr={self.ctr}{enc_str}&cmac=".encode("ascii")
        log.debug(f"[SDM CMAC] Built CMAC message: {message.decode('ascii')}")
        return message


def parse_ndef_file_data(ndef_data: bytes) -> tuple[bytes, dict]:
    """Parse raw NDEF file data and extract the NDEF record.

    Handles multiple NDEF formats for backward compatibility:
    - Type 4 Tag (new): [NLEN (2 bytes)] + [D1 01 ...] (no TLV)
    - Type 4 Tag (old): [NLEN (2 bytes)] + [03] [Len] [D1 01 ...] [FE] (with TLV)
    - Type 2 Tag: [03] [Len] [D1 01 ...] [FE] (TLV only, no NLEN)

    Args:
        ndef_data: Raw NDEF file bytes (File 2 content)

    Returns:
        Tuple of (ndef_record, parse_info) where:
        - ndef_record: The NDEF record bytes starting with D1
        - parse_info: Dict with parsing details for diagnostics
    """
    parse_info = {
        "format": "unknown",
        "nlen": None,
        "has_tlv": False,
        "ndef_record_offset": 0,
        "valid": False,
    }

    if len(ndef_data) < 7:
        parse_info["error"] = "Data too short"
        return b"", parse_info

    data_to_parse = ndef_data
    offset = 0

    # Detect and skip 2-byte NLEN prefix if present (Type 4 Tag format)
    if len(ndef_data) >= 2:
        potential_nlen = (ndef_data[0] << 8) | ndef_data[1]
        byte_after_nlen = ndef_data[2] if len(ndef_data) > 2 else 0

        # Valid NLEN: reasonable length and byte 2 is either D1 (new) or 03 (old TLV)
        if 0 < potential_nlen <= len(ndef_data) - 2:
            if byte_after_nlen == 0xD1:
                # Type 4 Tag NEW format: [NLEN] + [D1 01 ...]
                parse_info["format"] = "type4_new"
                parse_info["nlen"] = potential_nlen
                parse_info["has_tlv"] = False
                data_to_parse = ndef_data[2:]
                offset = 2
            elif byte_after_nlen == 0x03:
                # Type 4 Tag OLD format: [NLEN] + [03] [Len] [D1 ...]
                parse_info["format"] = "type4_old"
                parse_info["nlen"] = potential_nlen
                parse_info["has_tlv"] = True
                data_to_parse = ndef_data[2:]
                offset = 2

    # Skip TLV wrapper if present
    if len(data_to_parse) >= 2 and data_to_parse[0] == 0x03:
        tlv_len = data_to_parse[1]
        parse_info["has_tlv"] = True
        parse_info["tlv_length"] = tlv_len
        if parse_info["format"] == "unknown":
            parse_info["format"] = "type2_tlv"
        data_to_parse = data_to_parse[2:]
        offset += 2

    # Find NDEF record start (D1 01 ...)
    ndef_start = -1
    for i in range(len(data_to_parse) - 1):
        if data_to_parse[i] == 0xD1 and data_to_parse[i + 1] == 0x01:
            ndef_start = i
            break

    if ndef_start == -1:
        parse_info["error"] = "No NDEF record found (D1 01)"
        return b"", parse_info

    parse_info["ndef_record_offset"] = offset + ndef_start
    parse_info["valid"] = True

    # Extract the NDEF record
    ndef_record = data_to_parse[ndef_start:]

    # Remove terminator if present
    if len(ndef_record) > 0 and ndef_record[-1] == 0xFE:
        ndef_record = ndef_record[:-1]

    return ndef_record, parse_info


def validate_ndef_uri_record(ndef_record: bytes) -> dict:
    """Validate an NDEF URI record structure.

    Args:
        ndef_record: NDEF record bytes (should start with D1)

    Returns:
        Dict with validation results for each field
    """
    result = {
        "valid": False,
        "ndef_header": {"value": None, "valid": False, "expected": 0xD1},
        "type_length": {"value": None, "valid": False, "expected": 0x01},
        "payload_length": {"value": None, "valid": False},
        "uri_type": {"value": None, "valid": False, "expected": 0x55},
        "uri_prefix": {"value": None, "valid": False, "expected": 0x04},
    }

    if len(ndef_record) < 5:
        result["error"] = "Record too short"
        return result

    # Parse NDEF URI record: D1 01 [payload_len] 55 [prefix] [URI]
    result["ndef_header"]["value"] = ndef_record[0]
    result["ndef_header"]["valid"] = ndef_record[0] == 0xD1

    result["type_length"]["value"] = ndef_record[1]
    result["type_length"]["valid"] = ndef_record[1] == 0x01

    result["payload_length"]["value"] = ndef_record[2]
    result["payload_length"]["valid"] = ndef_record[2] > 0

    result["uri_type"]["value"] = ndef_record[3]
    result["uri_type"]["valid"] = ndef_record[3] == 0x55

    if len(ndef_record) >= 5:
        result["uri_prefix"]["value"] = ndef_record[4]
        result["uri_prefix"]["valid"] = ndef_record[4] == 0x04  # https://

    result["valid"] = all([
        result["ndef_header"]["valid"],
        result["type_length"]["valid"],
        result["payload_length"]["valid"],
        result["uri_type"]["valid"],
        result["uri_prefix"]["valid"],
    ])

    return result


def _extract_url_from_ndef_data(ndef_data: bytes) -> str:
    """Extract URL string from raw NDEF data bytes.

    Supports multiple NDEF formats for backward compatibility:
    - Type 4 Tag (new): [NLEN (2 bytes)] + [D1 01 ...] (no TLV)
    - Type 4 Tag (old): [NLEN (2 bytes)] + [03] [Len] [D1 01 ...] [FE] (with TLV)
    - Type 2 Tag: [03] [Len] [D1 01 ...] [FE] (TLV only, no NLEN)

    Args:
        ndef_data: Raw NDEF file bytes

    Returns:
        Extracted URL string, or empty string if extraction fails
    """
    log.debug(f"Extracting URL from NDEF data of {len(ndef_data)} bytes: {ndef_data.hex().upper()[:64]}...")

    if len(ndef_data) < 4:
        return ""

    data_to_parse = ndef_data

    # Detect and skip 2-byte NLEN prefix if present (Type 4 Tag format)
    # NLEN is a big-endian 2-byte length field at the start of File 2
    if len(ndef_data) >= 2:
        potential_nlen = (ndef_data[0] << 8) | ndef_data[1]
        # Valid NLEN: points within remaining data and byte 2 is either D1 (new) or 03 (old TLV)
        if 0 < potential_nlen <= len(ndef_data) - 2:
            byte_after_nlen = ndef_data[2] if len(ndef_data) > 2 else 0
            if byte_after_nlen == 0xD1 or byte_after_nlen == 0x03:
                data_to_parse = ndef_data[2:]
                log.debug(f"Detected Type 4 Tag NLEN={potential_nlen}, data starts with 0x{byte_after_nlen:02X}")

    # Skip TLV wrapper if present (old format or Type 2 Tag)
    # TLV: [03] [Len] [NDEF Record] [FE]
    if len(data_to_parse) >= 2 and data_to_parse[0] == 0x03:
        tlv_len = data_to_parse[1]
        data_to_parse = data_to_parse[2:]  # Skip TLV tag and length
        log.debug(f"Skipped TLV wrapper (03 {tlv_len:02X})")

    # Find NDEF record start (D1 01 ...)
    start_idx = 0
    for i in range(len(data_to_parse) - 1):
        if data_to_parse[i] == 0xD1 and data_to_parse[i + 1] == 0x01:
            start_idx = i
            log.debug(f"Found NDEF record start @ offset {start_idx}")
            break

    if start_idx == 0 and data_to_parse[0] != 0xD1:
        log.error("No NDEF record start sequence found (D1 01)")
        return ""

    # Parse NDEF URI record
    # Format: D1 01 [payload_len] 55 [prefix] [URI]
    try:
        payload_len = data_to_parse[start_idx + 2]
        prefix_code = data_to_parse[start_idx + 4]
        uri_bytes = data_to_parse[start_idx + 5 : start_idx + 5 + payload_len - 1]
        log.debug(f"Reading payload: len={payload_len}, prefix_code=0x{prefix_code:02X}, uri_bytes={uri_bytes.hex().upper()}")

        # Decode prefix
        prefixes = {
            0x00: "",
            0x01: "http://www.",
            0x02: "https://www.",
            0x03: "http://",
            0x04: "https://",
        }
        prefix = prefixes.get(prefix_code, "")
        log.debug(f"URI Prefix: {prefix} (code 0x{prefix_code:02X})")

        # Decode URI
        uri = uri_bytes.decode("utf-8", errors="replace")

        # Remove terminator if present
        uri = uri.removesuffix("\xfe")

        log.debug(f"URI: {uri}")
        return prefix + uri

    except Exception:
        return ""

@dataclass
class SDMUrlTemplate(SDMUrl):
    """Template for building SDM-enabled URLs.

    Contains the base URL and placeholders for SDM parameters.
    """

    base_url: str = ""
    uid_placeholder: str = "00000000000000"
    read_ctr_placeholder: str = "000000"  # 6-character hex string placeholder
    cmac_placeholder: str = "0000000000000000"
    enc_placeholder: str = "" # Optional encrypted data placeholder

    def __init__(self, base_url: str):
        super().__init__(
            base_url=base_url,
            uid=self.uid_placeholder,
            read_ctr=self.read_ctr_placeholder,
            cmac=self.cmac_placeholder,
            enc=self.enc_placeholder
        )

    def build_url(self) -> str:
        """Build URL with placeholder values (for NDEF provisioning).

        Returns:
            URL string with placeholder values
        """
        return self.generate_url()

class SDMConfiguration:
    """Configuration for Secure Dynamic Messaging.

    Full-featured class for SDM configuration with methods for:
    - Building NDEF records
    - Building file settings payloads
    - Parsing from NDEF data
    - Extracting from tag responses
    """

    def __init__(
        self,
        file_no: int,
        comm_mode: CommMode,
        access_rights: AccessRights,
        enable_sdm: bool,
        sdm_options: int,
        sdm_url: SDMUrl,
        url: str = "",
    ):
        """Initialize SDM configuration.

        Args:
            file_no: File number (typically 0x02 for NDEF)
            comm_mode: Communication mode (Plain, MAC, or Full)
            access_rights: AccessRights object or 2-byte encoding
            enable_sdm: Whether SDM is enabled
            sdm_options: SDM options byte (UID_MIRROR, READ_COUNTER, etc.)
            offsets: SDM offsets (SDMOffsets object or dict)
            url: Optional URL string (for parsing)
            template: Optional URL template
        """
        self.file_no = file_no
        self.comm_mode: CommMode = comm_mode
        self.enable_sdm = enable_sdm
        self.sdm_url: SDMUrl = sdm_url
        self.sdm_options = sdm_options

        self.offsets: SDMOffsets = self.sdm_url.calculate_offsets()

        self.url = url
        if not url:
            self.url: str = self.sdm_url.generate_url()
        self.access_rights: AccessRights = access_rights

    @property
    def base_url(self) -> str:
        """Get the base URL (without SDM parameters).

        Returns:
            Base URL if template exists, otherwise empty string
        """
        return self.sdm_url.base_url

    @property
    def parsed_values(self) -> SDMUrl:
        """Get parsed SDM values from URL (uid, counter, cmac).

        Returns:
            SDMUrl object with parsed values.
        """
        return self.sdm_url

    @property
    def uid(self) -> str: 
        """Get UID value from URL."""
        return self.sdm_url.uid

    @property
    def counter(self) -> int:
        """Get counter value from URL as integer."""
        ctr_hex = self.sdm_url.read_ctr
        return int(ctr_hex, 16)

    @property
    def cmac(self) -> str:
        """Get CMAC value from URL."""
        return self.sdm_url.cmac

    @property
    def has_sdm_parameters(self) -> bool:
        """Check if URL has SDM parameters.

        Returns:
            True if URL contains uid, ctr, and cmac parameters
        """
        return self.sdm_url.uid and self.sdm_url.read_ctr and self.sdm_url.cmac

    def get_access_rights_bytes(self) -> bytes:
        """Get access rights as bytes (internal encoding)."""
        return self.access_rights.to_bytes()

    def to_ndef_bytes(self) -> bytes:
        """Convert configuration to NDEF file bytes.

        Alias for build_ndef_record() for clarity.

        Returns:
            NDEF message bytes ready to write to tag
        """
        return self.build_ndef_record()

    def build_cmac_message(self) -> bytes:
        """Build the CMAC message for validation.

        This constructs the message that should be MAC'd according to the NXP spec:
        SDMMAC = MACt(SesSDMFileReadMACKey; DynamicFileData[SDMMACInputOffset ... SDMMACOffset - 1])

        The message is the literal bytes from the NDEF file between SDMMACInputOffset and SDMMACOffset.

        Returns:
            Message bytes ready for CMAC calculation

        Raises:
            ValueError: If required values (uid, counter) are missing or template is not available
        """
        # Use the template to build the message based on the URL structure
        return self.sdm_url.build_cmac_message()

    def build_settings_payload(self) -> bytes:
        """Build the file settings data payload for ChangeFileSettings command.

        Returns:
            Byte array ready to send to card
        """
        # Start with FileOption byte (combines CommMode and SDM enable bit)
        # FileOption: Bit 6 = SDM enabled, Bits 1-0 = CommMode
        file_option = int(self.comm_mode)  # Start with comm mode (bits 1-0)
        if self.enable_sdm:
            file_option |= 0x40  # Set bit 6 to enable SDM
        data = bytearray([file_option])
        # Access rights (automatically converted to bytes via get_access_rights_bytes())
        data.extend(self.get_access_rights_bytes())

        if not self.enable_sdm:
            return bytes(data)

        # SDM options byte
        # NOTE: SDM_ENABLED (0x40) goes in FileOption, NOT in SDMOptions!
        # SDMOptions should only have: UID_MIRROR (0x80), READ_COUNTER (0x40), ASCII_ENCODING (0x01), etc.
        from ntag424_sdm_provisioner.constants import FileOption
        sdm_opts = self.sdm_options or FileOption.UID_MIRROR
        # Always enable ASCII encoding (bit 0) for compatibility
        sdm_opts |= 0x01  # ASCII_ENCODING
        data.append(sdm_opts)

        # SDMAccessRights (2 bytes) - REQUIRED when SDM enabled!
        # Per NXP spec AN12196 Table 11:
        # Byte 0[7:4] = RFU (0xF = reserved)
        # Byte 0[3:0] = SDMCtrRet (E = free, allows counter retrieval without key)
        # Byte 1[7:4] = SDMMetaRead (E = plain UID mirroring, no encryption)
        # Byte 1[3:0] = SDMFileRead (3 = use Key 3 for CMAC calculation)
        #
        # CRITICAL: Per NXP spec line 480:
        # "The SDMFileRead access right, if related with an AppKey, GRANTS FREE ACCESS
        #  to ReadData and ISOReadBinary. The targeted AppKey is used for the Secure
        #  Dynamic Messaging."
        #
        # This means SDMFileRead=KEY_3 does TWO things:
        #   1. GRANTS free read access (no authentication required!) ✅
        #   2. Uses Key 3 to calculate CMAC for mirroring ✅
        #
        # The tag calculates CMAC internally and substitutes placeholders BEFORE
        # sending data to the reader. Android receives the final URL with CMAC
        # already embedded - no authentication needed from Android's side!
        #
        # Configuration for UID + Counter + CMAC with Android compatibility:
        # Byte 0 = (0xF << 4) | 0xE = 0xFE (RFU=F, CtrRet=E)
        # Byte 1 = (0xE << 4) | 0x3 = 0xE3 (MetaRead=E, FileRead=KEY_3)
        data.extend([0xFE, 0xE3])  # SDMAccessRights: FREE read + CMAC with Key 3

        # Helper to add 3-byte little-endian offset
        def add_offset(value: int):
            data.extend([value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF])

        # FIELD ORDER per NXP spec Section 10.7.1:
        # The presence of each field depends on SDMOptions bits and SDMAccessRights values

        # From spec Table 69:
        # UIDOffset [3] - Present if: (SDMOptions[Bit 7] = 1) AND (SDMMetaRead != Fh)
        # SDMReadCtrOffset [3] - Present if: (SDMOptions[Bit 6] = 1) AND (SDMMetaRead != Fh)
        # PICCDataOffset [3] - Present if: SDMMetaRead = 0..4 (encrypted)
        # SDMMACInputOffset [3] - Present if: SDMFileRead != Fh
        # SDMENCOffset [3] - Present if: SDMOptions[Bit 4] = 1
        # SDMENCLength [3] - Present if: SDMOptions[Bit 4] = 1
        # SDMMACOffset [3] - Present if: SDMFileRead != Fh
        # SDMReadCtrLimit [3] - Present if: SDMOptions[Bit 5] = 1

        # Our config: SDMMetaRead=E (plain), SDMFileRead=3 (KEY_3 for CMAC)

        # 1. UIDOffset - if UID_MIRROR and SDMMetaRead != F
        assert self.offsets is not None
        # We have SDMMetaRead=E, so this should be present
        if sdm_opts & 0x80:  # UID_MIRROR (bit 7)
            add_offset(self.offsets.uid_offset)

        # 2. SDMReadCtrOffset - if READ_COUNTER and SDMMetaRead != F
        # SDMOptions bit 6 = READ_COUNTER (0x40)
        if sdm_opts & 0x40:  # READ_COUNTER (bit 6)
            add_offset(self.offsets.read_ctr_offset)

        # 3. PICCDataOffset - ONLY if SDMMetaRead = 0..4 (encrypted)
        # We have SDMMetaRead=E (plain), so SKIP

        # 4. SDMMACInputOffset - REQUIRED since SDMFileRead=3 (not F)
        # This is where CMAC calculation starts (typically same as UID offset)
        add_offset(self.offsets.mac_input_offset)

        # 5-6. SDMENCOffset/Length - ONLY if encryption enabled (bit 4)
        # We don't have bit 4 set, so SKIP

        # 7. SDMMACOffset - REQUIRED since SDMFileRead=3 (not F)
        # This is where the CMAC placeholder is in the URL
        add_offset(self.offsets.mac_offset)

        # 8. SDMReadCtrLimit - ONLY if bit 5 set (counter limit)
        # We're not setting a limit, so SKIP

        return bytes(data)

    def build_ndef_record(self) -> bytes:
        """Build NDEF Type 4 Tag message with URI record.

        Args:
            url: Complete URL (with or without placeholders). If None, uses self.url

        Returns:
            NDEF message bytes ready to write to file (includes length field for Type 4 tags)
        """
        # URI identifier codes (0x04 = "https://")
        uri_prefix = 0x04

        url_to_use = self.sdm_url.generate_url()
        # Remove "https://" from URL since we use prefix code
        if url_to_use.startswith("https://"):
            url_content = url_to_use[8:]
        elif url_to_use.startswith("http://"):
            uri_prefix = 0x03
            url_content = url_to_use[7:]
        else:
            uri_prefix = 0x00  # No prefix
            url_content = url_to_use

        url_bytes = url_content.encode("ascii")

        # Type 4 Tag NDEF format (ISO 14443-4 / NFC Forum Type 4 Tag)
        # Structure: [NLEN (2 bytes)] + [NDEF Record]
        # NO TLV wrapper (03/FE) - that's Type 2 Tag format!
        #
        # Per ISO Compliant NDEF Reference.md:
        # Byte 0-1: NLEN (big-endian length of NDEF message)
        # Byte 2:   D1 (NDEF Header: MB=1, ME=1, SR=1, TNF=1)
        # Byte 3:   01 (Type Length)
        # Byte 4:   Payload Length (prefix byte + URL length)
        # Byte 5:   55 (Type 'U' = URI Record)
        # Byte 6:   04 (URI prefix = https://)
        # Byte 7+:  URL body (without https://)

        # Build NDEF Record (no TLV wrapper)
        payload_len = len(url_bytes) + 1  # +1 for URI prefix byte
        ndef_record = bytes([
            0xD1,        # NDEF Header: MB=1, ME=1, CF=0, SR=1, IL=0, TNF=0x01
            0x01,        # Type Length = 1
            payload_len, # Payload length
            0x55,        # Type = 'U' (URI)
            uri_prefix,  # URI prefix code (0x04 = https://)
        ]) + url_bytes

        # NLEN = length of the NDEF record (NOT including NLEN itself)
        nlen = len(ndef_record)

        # Build Type 4 Tag format: [NLEN (2 bytes, big-endian)] + [NDEF Record]
        type4_ndef = bytes([
            (nlen >> 8) & 0xFF,  # NLEN high byte
            nlen & 0xFF,         # NLEN low byte
        ]) + ndef_record

        return type4_ndef

    @classmethod
    def from_ndef_data(cls, ndef_data: bytes, file_no: int = 0x02) -> "SDMConfiguration | None":
        """Extract SDM configuration from NDEF file data.

        Args:
            ndef_data: Raw NDEF file bytes from tag
            file_no: File number (default: 0x02 for NDEF)

        Returns:
            SDMConfiguration object if SDM URL found, None otherwise
        """
        # Extract URL from NDEF data
        url = _extract_url_from_ndef_data(ndef_data)
        log.debug(f"Extracted URL from NDEF data: {url}")
        if not url:
            raise ValueError("No SDM URL found in NDEF data") 

        # Check if URL has SDM parameters
        if not ("uid=" in url and "ctr=" in url and "cmac=" in url):
            raise ValueError(f"SDM URL missing params: {url}") 

        # Parse URL to extract SDM parameters and build template
        surl = SDMUrl.from_url(url)

        # Create configuration
        return cls(
            file_no=file_no,
            comm_mode=CommMode.MAC,  # Assume MAC mode for SDM
            access_rights=AccessRightsPresets.FREE_READ_KEY0_WRITE,
            enable_sdm=True,
            sdm_options=FileOption.UID_MIRROR | FileOption.READ_COUNTER,
            sdm_url=surl,
            url=url
        )



@dataclass
class AuthSessionKeys:
    """Session keys derived from EV2 authentication."""

    session_enc_key: bytes
    session_mac_key: bytes
    ti: bytes
    cmd_counter: int = 0


# ============================================================================
# Helper Functions
# ============================================================================


def describe_status_word(sw1: int, sw2: int) -> str:
    """Get human-readable description of status word."""
    sw = StatusWord.from_bytes(sw1, sw2)

    descriptions = {
        StatusWord.OK: "Operation successful",
        StatusWord.MORE_DATA_AVAILABLE: "More data available (send AF)",
        StatusWord.AUTHENTICATION_ERROR: "Authentication failed",
        StatusWord.PERMISSION_DENIED: "Permission denied",
        StatusWord.FILE_NOT_FOUND: "File or application not found",
        StatusWord.WRONG_LENGTH: "Wrong length in command",
        StatusWord.WRONG_PARAMETERS: "Incorrect parameters (P1/P2)",
        StatusWord.COMMAND_NOT_ALLOWED: "Command not allowed in current state",
        StatusWord.INTEGRITY_ERROR: "Data integrity check failed",
        StatusWord.NO_SUCH_KEY: "Specified key does not exist",
    }

    if isinstance(sw, StatusWord):
        desc = descriptions.get(sw, sw.name.replace("_", " ").title())
        return f"{sw.name} (0x{sw1:02X}{sw2:02X}): {desc}"
    else:
        return f"Unknown status (0x{sw1:02X}{sw2:02X})"


# ============================================================================
# Constants
# ============================================================================

# Factory default key (all zeros) for NTAG424 DNA tags
FACTORY_KEY: Final[bytes] = bytes(16)  # 16 bytes of 0x00

# Default base URL for game coin provisioning
GAME_COIN_BASE_URL = "https://script.google.com/a/macros/gutsteins.com/s/AKfycbz2gCQYl_OjEJB26jiUL8253I0bX4czxykkcmt-MnF41lIyX18SLkRgUcJ_VJRJbiwh/exec"


# ============================================================================
# Capability Container (CC) File
# ============================================================================


@dataclass
class CCFileData:
    """Capability Container file data for NFC Type 4 Tag.

    The CC file tells phones/readers where to find NDEF data and
    what access conditions apply.
    """

    cc_length: int  # Total CC length in bytes
    mapping_version: int  # T4T mapping version (0x20 = v2.0)
    max_read_length: int  # MLe - max bytes in single read
    max_write_length: int  # MLc - max bytes in single write
    ndef_file_id: int  # File ID of NDEF file (usually 0xE104)
    ndef_file_size: int  # Size of NDEF file in bytes
    ndef_read_access: int  # Read access condition (0x00 = FREE)
    ndef_write_access: int  # Write access condition (0x00 = FREE)
    proprietary_file_id: int = 0xE105  # Proprietary file ID
    proprietary_file_size: int = 128  # Proprietary file size
    proprietary_read_access: int = 0x82  # Requires Key 2
    proprietary_write_access: int = 0x83  # Requires Key 3

    # Constants
    FACTORY_CC_LENGTH = 0x0017  # 23 bytes
    T4T_VERSION_2_0 = 0x20
    DEFAULT_MLE = 0x0100  # 256 bytes
    DEFAULT_MLC = 0x00FF  # 255 bytes

    # TLV Tags
    TLV_NDEF_FILE_CONTROL = 0x04
    TLV_PROPRIETARY_FILE_CONTROL = 0x05

    # Access condition codes
    ACCESS_FREE = 0x00
    ACCESS_KEY_AUTH = 0x80  # Base code, OR with key number

    @staticmethod
    def from_bytes(data: bytes) -> "CCFileData":
        """Parse CC file data from raw bytes."""
        if len(data) < 15:
            raise ValueError(f"CC file data too short: {len(data)} bytes")

        cc_length = (data[0] << 8) | data[1]
        mapping_version = data[2]
        max_read_length = (data[3] << 8) | data[4]
        max_write_length = (data[5] << 8) | data[6]

        # Parse NDEF File Control TLV (starts at byte 7)
        tlv_tag = data[7]
        tlv_len = data[8]

        if tlv_tag != 0x04 or tlv_len != 0x06:
            raise ValueError(f"Invalid NDEF File Control TLV: T={tlv_tag:02X}, L={tlv_len:02X}")

        ndef_file_id = (data[9] << 8) | data[10]
        ndef_file_size = (data[11] << 8) | data[12]
        ndef_read_access = data[13]
        ndef_write_access = data[14]

        # Parse Proprietary File Control TLV (optional, starts at byte 15)
        prop_fid = 0xE105
        prop_size = 128
        prop_read = 0x82
        prop_write = 0x83

        if len(data) >= 21:
            prop_tlv_tag = data[15]
            prop_tlv_len = data[16]
            if prop_tlv_tag == 0x05 and prop_tlv_len == 0x06:
                prop_fid = (data[17] << 8) | data[18]
                prop_size = (data[19] << 8) | data[20]
                prop_read = data[21] if len(data) > 21 else 0x82
                prop_write = data[22] if len(data) > 22 else 0x83

        return CCFileData(
            cc_length=cc_length,
            mapping_version=mapping_version,
            max_read_length=max_read_length,
            max_write_length=max_write_length,
            ndef_file_id=ndef_file_id,
            ndef_file_size=ndef_file_size,
            ndef_read_access=ndef_read_access,
            ndef_write_access=ndef_write_access,
            proprietary_file_id=prop_fid,
            proprietary_file_size=prop_size,
            proprietary_read_access=prop_read,
            proprietary_write_access=prop_write,
        )

    def to_bytes(self) -> bytes:
        """Convert CC file data to raw bytes."""
        data = bytearray()

        # CC Header
        data.extend(
            [
                (self.cc_length >> 8) & 0xFF,
                self.cc_length & 0xFF,
                self.mapping_version,
                (self.max_read_length >> 8) & 0xFF,
                self.max_read_length & 0xFF,
                (self.max_write_length >> 8) & 0xFF,
                self.max_write_length & 0xFF,
            ]
        )

        # NDEF File Control TLV
        data.extend(
            [
                self.TLV_NDEF_FILE_CONTROL,  # T
                0x06,  # L
                (self.ndef_file_id >> 8) & 0xFF,
                self.ndef_file_id & 0xFF,
                (self.ndef_file_size >> 8) & 0xFF,
                self.ndef_file_size & 0xFF,
                self.ndef_read_access,
                self.ndef_write_access,
            ]
        )

        # Proprietary File Control TLV
        data.extend(
            [
                self.TLV_PROPRIETARY_FILE_CONTROL,  # T
                0x06,  # L
                (self.proprietary_file_id >> 8) & 0xFF,
                self.proprietary_file_id & 0xFF,
                (self.proprietary_file_size >> 8) & 0xFF,
                self.proprietary_file_size & 0xFF,
                self.proprietary_read_access,
                self.proprietary_write_access,
            ]
        )

        # Pad to 32 bytes with zeros
        while len(data) < 32:
            data.append(0x00)

        return bytes(data)
