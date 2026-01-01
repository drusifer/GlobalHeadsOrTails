"""SelectPiccApplication command for NTAG424 DNA."""

from typing import ClassVar

from ntag424_sdm_provisioner.commands.base import ApduCommand
from ntag424_sdm_provisioner.constants import SuccessResponse
from ntag424_sdm_provisioner.hal import hexb


class SelectPiccApplication(ApduCommand):
    """Selects the main PICC-level application on the NTAG424 DNA tag.

    This must be called before any other NTAG424-specific commands.
    The PICC application has AID: D2760000850101
    """

    PICC_AID: ClassVar[list[int]] = [0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01]

    def __init__(self):
        super().__init__(use_escape=True)

    def __str__(self) -> str:
        return f"SelectPiccApplication(AID={hexb(self.PICC_AID)})"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return "SelectPiccApplication"

    @property
    def sequence_description(self) -> str:
        return "Select NTAG424 DNA PICC application (AID: D2760000850101)"

    def get_sequence_params(self) -> dict[str, str]:
        return {"aid": hexb(self.PICC_AID)}

    # --- ApduCommand Implementation ---
    def build_apdu(self) -> list:
        """Build APDU for new connection.send(command) pattern."""
        return [0x00, 0xA4, 0x04, 0x00, len(self.PICC_AID), *self.PICC_AID, 0x00]

    def parse_response(self, _data: bytes, _sw1: int, _sw2: int) -> SuccessResponse:
        """Parse response for new connection.send(command) pattern."""
        return SuccessResponse("PICC Application selected.")
