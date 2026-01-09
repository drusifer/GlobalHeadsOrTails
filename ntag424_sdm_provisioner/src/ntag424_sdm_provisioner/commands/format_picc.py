"""FormatPICC command - Factory reset NTAG424 DNA tag.

WARNING: This command ERASES all data and resets all keys to factory defaults!
"""

from ntag424_sdm_provisioner.commands.base import AuthApduCommand
from ntag424_sdm_provisioner.constants import SuccessResponse


class FormatPICC(AuthApduCommand):
    """Format PICC - Factory reset the tag.

    WARNING: This command:
    - Resets ALL keys to factory defaults (0x00 * 16)
    - Erases ALL files and data
    - Disables SDM
    - Cannot be undone!

    KEY REQUIREMENTS:
    ✓ Requires: PICC Master Key (Key 0) for authentication
    ✗ Does NOT require: Keys 1 or 3 (App Read, SDM MAC)

    Keys 1 and 3 can be:
    - Factory defaults (0x00*16)
    - Custom keys
    - Completely unknown
    → FormatPICC will work regardless!

    This is the "nuclear option" when you have Key 0 but lost Keys 1/3.

    Per NXP spec: CommMode.Full is required (CMAC protection).
    """

    def __init__(self):
        super().__init__(use_escape=True)  # Use Control mode for ACR122U

    def __str__(self) -> str:
        return "FormatPICC"

    def get_command_byte(self) -> int:
        """Get FormatPICC command byte (0xFC)."""
        return 0xFC

    def get_unencrypted_header(self) -> bytes:
        """No header data for FormatPICC."""
        return b""

    def build_command_data(self) -> bytes:
        """No command data for FormatPICC - only CMAC is sent."""
        return b""

    def parse_response(self, _data: bytes) -> SuccessResponse:
        """Parse FormatPICC response.

        Returns:
            SuccessResponse indicating tag has been reset to factory
        """
        return SuccessResponse(
            "Tag formatted successfully - all keys reset to factory defaults"
        )
