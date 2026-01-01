from ntag424_sdm_provisioner.constants import (
    FileOption,
    FileSettingsResponse,
    KeyVersionResponse,
    SDMConfiguration,
    SDMOffsets,
    SDMUrlTemplate,
)

# Re-export build_ndef_uri_record for backward compatibility
from ntag424_sdm_provisioner.commands.sun_commands import build_ndef_uri_record

__all__ = [
    "calculate_sdm_offsets",
    "build_sdm_settings_payload",
    "parse_file_settings",
    "parse_key_version",
    "build_ndef_uri_record",
]


def calculate_sdm_offsets(template: SDMUrlTemplate) -> SDMOffsets:
    """Calculate byte offsets for SDM mirrors in NDEF message.

    This is a convenience wrapper around SDMUrlTemplate.calculate_offsets().
    All offset calculation logic is now encapsulated in the template object itself.

    Args:
        template: SDM URL template with placeholder configuration

    Returns:
        SDMOffsets with calculated byte positions for SDM parameters
    """
    return template.calculate_offsets()


def build_sdm_settings_payload(config: SDMConfiguration) -> bytes:
    """Build the file settings data payload for ChangeFileSettings command.

    DEPRECATED: Use config.build_settings_payload() instead.
    This function is kept for backward compatibility.

    Args:
        config: SDM configuration

    Returns:
        Byte array ready to send to card
    """
    return config.build_settings_payload()




def parse_file_settings(file_no: int, data: bytes) -> FileSettingsResponse:
    """Parse GetFileSettings response data into structured format.

    Args:
        file_no: File number that was queried
        data: Raw response data from GetFileSettings command

    Returns:
        FileSettingsResponse dataclass with parsed fields
    """
    if len(data) < 7:
        raise ValueError(f"File settings data too short: {len(data)} bytes (minimum 7)")

    # Required fields (always present)
    file_type = data[0]
    file_option = data[1]
    access_rights = data[2:4]
    file_size = int.from_bytes(data[4:7], "little")

    # Optional SDM fields (present if SDM is enabled)
    sdm_options = None
    sdm_access_rights = None
    uid_offset = None
    read_ctr_offset = None
    picc_data_offset = None
    mac_input_offset = None
    enc_offset = None
    enc_length = None
    mac_offset = None
    read_ctr_limit = None

    if len(data) > 7 and (file_option & FileOption.SDM_ENABLED):
        offset = 7

        # SDM options byte
        if offset < len(data):
            sdm_options = data[offset]
            offset += 1

        # SDM access rights (2 bytes)
        if offset + 2 <= len(data):
            sdm_access_rights = data[offset : offset + 2]
            offset += 2

        # UID offset (3 bytes, little-endian)
        if offset + 3 <= len(data):
            uid_offset = int.from_bytes(data[offset : offset + 3], "little")
            offset += 3

        # SDM Read Counter offset (3 bytes)
        if offset + 3 <= len(data):
            read_ctr_offset = int.from_bytes(data[offset : offset + 3], "little")
            offset += 3

        # PICC Data offset (3 bytes)
        if offset + 3 <= len(data):
            picc_data_offset = int.from_bytes(data[offset : offset + 3], "little")
            offset += 3

        # MAC Input offset (3 bytes)
        if offset + 3 <= len(data):
            mac_input_offset = int.from_bytes(data[offset : offset + 3], "little")
            offset += 3

        # Encrypted data offset (3 bytes) - optional
        if offset + 3 <= len(data):
            enc_offset = int.from_bytes(data[offset : offset + 3], "little")
            offset += 3

            # Encryption length (3 bytes) - present if enc_offset is present
            if offset + 3 <= len(data):
                enc_length = int.from_bytes(data[offset : offset + 3], "little")
                offset += 3

        # MAC offset (3 bytes)
        if offset + 3 <= len(data):
            mac_offset = int.from_bytes(data[offset : offset + 3], "little")
            offset += 3

        # Read Counter Limit (3 bytes) - optional
        if offset + 3 <= len(data):
            read_ctr_limit = int.from_bytes(data[offset : offset + 3], "little")

    return FileSettingsResponse(
        file_no=file_no,
        file_type=file_type,
        file_option=file_option,
        access_rights=access_rights,
        file_size=file_size,
        sdm_options=sdm_options,
        sdm_access_rights=sdm_access_rights,
        uid_offset=uid_offset,
        read_ctr_offset=read_ctr_offset,
        picc_data_offset=picc_data_offset,
        mac_input_offset=mac_input_offset,
        enc_offset=enc_offset,
        enc_length=enc_length,
        mac_offset=mac_offset,
        read_ctr_limit=read_ctr_limit,
    )


def parse_key_version(key_no: int, data: bytes) -> KeyVersionResponse:
    """Parse GetKeyVersion response data into structured format.

    Args:
        key_no: Key number that was queried
        data: Raw response data from GetKeyVersion command

    Returns:
        KeyVersionResponse dataclass with parsed fields
    """
    if not data or len(data) < 1:
        raise ValueError(f"Key version data too short: {len(data)} bytes (minimum 1)")

    version = data[0]

    return KeyVersionResponse(key_no=key_no, version=version)
