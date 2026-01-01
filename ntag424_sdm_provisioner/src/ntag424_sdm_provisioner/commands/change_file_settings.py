from logging import getLogger

from ntag424_sdm_provisioner.commands.base import ApduCommand, AuthApduCommand
from ntag424_sdm_provisioner.commands.sdm_helpers import build_sdm_settings_payload
from ntag424_sdm_provisioner.constants import SDMConfiguration, SuccessResponse
from ntag424_sdm_provisioner.hal import hexb


log = getLogger(__name__)


class ChangeFileSettings(ApduCommand):
    """Change file settings - Unauthenticated command (no CMAC).

    Use this for:
    - Changing settings when Change access right = FREE
    - Files in PLAIN mode with no auth required

    For authenticated changes (when Change access requires a key), use ChangeFileSettingsAuth.
    """

    def __init__(self, config: SDMConfiguration):
        super().__init__(use_escape=True)  # Try with escape (Control vs Transmit)
        self.config = config

    def __str__(self) -> str:
        return f"ChangeFileSettings(file=0x{self.config.file_no:02X})"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return f"ChangeFileSettings (File {self.config.file_no:02X})"

    @property
    def sequence_description(self) -> str:
        return f"Change settings for file {self.config.file_no:02X} (unauthenticated)"

    def get_sequence_params(self) -> dict[str, str]:
        return {
            "file_no": f"{self.config.file_no:02X}",
            "comm_mode": str(self.config.comm_mode),
            "sdm_enabled": str(self.config.enable_sdm),
        }

    # --- ApduCommand Implementation ---
    def build_apdu(self) -> list:
        """Build APDU for connection.send(command) pattern."""
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)

        # Build APDU (plain mode - no encryption/CMAC)
        cmd_header_apdu = bytes([0x90, 0x5F, 0x00, 0x00])
        file_no_byte = bytes([self.config.file_no])
        cmd_data = file_no_byte + settings_payload

        apdu = list(cmd_header_apdu) + [len(cmd_data)] + list(cmd_data) + [0x00]

        log.debug(f"ChangeFileSettings (PLAIN) APDU: {hexb(apdu)}")
        return apdu

    def parse_response(self, _data: bytes, _sw1: int, _sw2: int) -> SuccessResponse:
        """Parse response for connection.send(command) pattern."""
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")


class ChangeFileSettingsAuth(AuthApduCommand):
    """Change file settings - Authenticated command (with CMAC).

    Use this when Change access right requires authentication.
    Type-safe: Requires AuthenticatedConnection via connection.send(command).

    Note: config.comm_mode sets the FILE's future access mode (PLAIN/MAC/FULL),
    not the command transmission mode. This command is always authenticated.
    """

    def __init__(self, config: SDMConfiguration):
        super().__init__(use_escape=False)
        self.config = config

        # NOTE: config.comm_mode is the FILE's access mode (how it will be read),
        # NOT the command transmission mode. ChangeFileSettingsAuth means the
        # COMMAND is sent authenticated, regardless of file's future CommMode.
        # Files with SDM typically use CommMode.PLAIN for free NFC phone access.

    def __str__(self) -> str:
        return f"ChangeFileSettingsAuth(file=0x{self.config.file_no:02X}, mode={self.config.comm_mode})"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return f"ChangeFileSettingsAuth (File {self.config.file_no:02X})"

    @property
    def sequence_description(self) -> str:
        return f"Change settings for file {self.config.file_no:02X} (authenticated, SDM={self.config.enable_sdm})"

    def get_sequence_params(self) -> dict[str, str]:
        return {
            "file_no": f"{self.config.file_no:02X}",
            "comm_mode": str(self.config.comm_mode),
            "sdm_enabled": str(self.config.enable_sdm),
        }

    # --- AuthApduCommand Implementation ---
    def get_command_byte(self) -> int:
        """Command byte for ChangeFileSettings."""
        return 0x5F

    def get_unencrypted_header(self) -> bytes:
        """FileNo is the unencrypted header in ChangeFileSettings.

        It is included in the CMAC but NOT encrypted.
        """
        return bytes([self.config.file_no])

    def needs_encryption(self) -> bool:
        """ChangeFileSettings is ALWAYS sent encrypted (FULL mode).

        The config.comm_mode refers to the file's FUTURE access mode (for NFC phones),
        not the command transmission mode. Per Arduino MFRC522 library and NXP spec,
        ChangeFileSettings commands are always sent encrypted regardless of file CommMode.
        """
        return True  # Always encrypt ChangeFileSettings!

    def build_command_data(self) -> bytes:
        """Build plaintext settings payload.

        Note: config.comm_mode is for FUTURE FILE ACCESS, not command transmission!
        - CommMode.PLAIN = File accessible without auth, but command needs MAC
        - This command is ALWAYS sent with authentication (ChangeFileSettingsAuth)

        Returns:
            Settings payload (Encrypted: FileNo + Settings)
        """
        # Use helper to build payload
        settings_payload = build_sdm_settings_payload(self.config)

        # FileNo is now in get_unencrypted_header(), so just return the settings
        return settings_payload

    def parse_response(self, _data: bytes) -> SuccessResponse:
        """Parse response - no data expected on success."""
        return SuccessResponse(f"File {self.config.file_no:02X} settings changed")
