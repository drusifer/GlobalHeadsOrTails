"""Tool Helpers - Common functionality shared across tools.

Provides reusable utilities that follow DRY principle:
- NDEF file reading
- URL extraction and parsing
- Common validation logic
"""

import logging

from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettingsAuth
from ntag424_sdm_provisioner.commands.iso_commands import ISOFileID, ISOReadBinary, ISOSelectFile
from ntag424_sdm_provisioner.commands.sdm_helpers import calculate_sdm_offsets
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.constants import (
    AccessRight,
    AccessRights,
    CommMode,
    FileOption,
    SDMConfiguration,
    SDMUrlTemplate,
)
from ntag424_sdm_provisioner.hal import NTag424CardConnection


log = logging.getLogger(__name__)


def read_ndef_file(card: NTag424CardConnection) -> bytes:
    """Read entire NDEF file from tag.

    Single source of truth for NDEF reading. HAL automatically handles
    multi-frame responses (0x91AF) by sending GET_ADDITIONAL_FRAME.

    Args:
        card: Open connection to tag

    Returns:
        Complete NDEF file contents (up to 256 bytes)

    Note:
        Automatically re-selects PICC application after reading.
    """
    card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
    ndef_data = card.send(ISOReadBinary(0, 256))
    assert isinstance(ndef_data, bytes)
    card.send(SelectPiccApplication())  # Re-select for next commands

    log.debug(f"Read {len(ndef_data)} bytes from NDEF file")
    return ndef_data


def has_ndef_content(ndef_data: bytes) -> bool:
    """Check if NDEF data contains meaningful content.

    Args:
        ndef_data: Raw NDEF file contents

    Returns:
        True if NDEF has provisioned content
    """
    # Check for SDM parameters
    if b"uid=" in ndef_data or b"ctr=" in ndef_data:
        return True

    # Check for URL content
    if b"://" in ndef_data and len(ndef_data) > 20:
        return True

    return False


def extract_url_from_ndef(ndef_data: bytes) -> str | None:
    """Extract URL from NDEF data.

    Single source of truth for URL parsing.

    NDEF URI record format:
    - TLV headers
    - 0x55 (URI record type)
    - 0x04 (https:// protocol byte)
    - URL text
    - 0xFE (terminator)

    Args:
        ndef_data: Raw NDEF file contents

    Returns:
        Complete URL string, or None if not found
    """
    try:
        # Look for URI record (0x55) with https:// prefix (0x04)
        for i in range(len(ndef_data) - 2):
            if ndef_data[i] == 0x55 and ndef_data[i + 1] == 0x04:
                # Found URI record
                url_start = i + 2

                # Find terminator (0xFE) or end of data
                url_end = ndef_data.find(0xFE, url_start)
                if url_end == -1:
                    url_end = len(ndef_data)

                # Extract URL bytes
                url_bytes = ndef_data[url_start:url_end]

                # Decode to string
                url_text = url_bytes.decode("ascii", errors="ignore")

                # Add https:// prefix (0x04 means https://)
                return "https://" + url_text

        return None

    except Exception as e:
        log.warning(f"Error extracting URL from NDEF: {e}")
        return None


def format_url_for_display(url: str, max_length: int = 80) -> str:
    """Format URL for display with truncation if needed.

    Args:
        url: Complete URL
        max_length: Max characters before truncation

    Returns:
        Formatted URL (truncated with ... if too long)
    """
    if len(url) <= max_length:
        return url

    # Truncate in middle to preserve start and end
    keep_start = (max_length - 3) // 2
    keep_end = max_length - 3 - keep_start

    return url[:keep_start] + "..." + url[-keep_end:]


def build_sdm_url_template(base_url: str):
    """Build SDM URL template with standard placeholders.

    Args:
        base_url: Base URL (e.g., "https://example.com/tag?")

    Returns:
        SDMUrlTemplate with standard placeholder lengths
    """
    return SDMUrlTemplate(
        base_url=base_url,
        uid_placeholder="00000000000000",
        read_ctr_placeholder="000000",
        cmac_placeholder="0000000000000000",
    )


def configure_sdm_with_offsets(auth_conn, template):
    """Configure SDM file settings using authenticated ChangeFileSettings.

    Per NXP spec Section 10.7.1:
    "The communication mode can be either CommMode.Plain or CommMode.Full
    based on current access right of the file."

    When Change access = KEY_0, MUST use authenticated (CommMode.Full) mode.

    **FIXED:** Now uses correct ISO 7816-4 padding (0x80 + zeros) instead of PKCS7.
    This resolves the 0x911E (INTEGRITY_ERROR) that occurred with wrong padding.

    Args:
        auth_conn: Authenticated connection (AuthenticatedConnection context)
        template: SDM URL template

    Returns:
        SDMConfiguration that was applied

    Reference:
        NT4H2421Gx Section 9.1.4 (padding)
        NT4H2421Gx Section 10.7.1 (ChangeFileSettings)
    """
    offsets = calculate_sdm_offsets(template)

    sdm_config = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,  # File's future access mode for NFC phones
        access_rights=AccessRights(
            read=AccessRight.FREE,
            write=AccessRight.KEY_0,  # Write requires authenticated session
            read_write=AccessRight.FREE,
            change=AccessRight.KEY_0,  # Keep secured
        ),
        enable_sdm=True,
        sdm_options=FileOption.UID_MIRROR | FileOption.READ_COUNTER,
        offsets=offsets,
    )

    # Send authenticated ChangeFileSettings (CommMode.Full with correct padding!)
    auth_conn.send(ChangeFileSettingsAuth(sdm_config))

    return sdm_config
