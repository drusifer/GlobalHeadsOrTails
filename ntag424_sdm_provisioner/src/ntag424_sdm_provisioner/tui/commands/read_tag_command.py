"""ReadTagCommand - Headless read tag operation."""

import logging
from typing import Any

from ntag424_sdm_provisioner.card_factory import CardConnectionFactory
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_file_settings import GetFileSettings
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger
from ntag424_sdm_provisioner.tui.clock import Clock, RealClock
from ntag424_sdm_provisioner.tui.nfc_command import NFCCommand


class ReadTagCommand(NFCCommand):
    """Read tag info without UI dependency."""

    def __init__(self, clock: Clock | None = None):
        self._clock = clock or RealClock()

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def operation_name(self) -> str:
        return "Read Tag"

    def execute(self) -> dict[str, Any]:
        """Execute the read tag operation.

        Returns:
            Dictionary with tag info (version, file settings, etc.)
        """
        results = {}

        with CardConnectionFactory.create(sequence_logger=SequenceLogger()) as connection:
            log = logging.getLogger(__name__)
            log.info("Connected to tag")

            # Get Version
            version = connection.send(GetChipVersion())
            results["version"] = version
            log.info(f"Version: {version}")

            # Get File Settings (File 2 - NDEF) - optional, may fail in simulation
            try:
                file_settings = connection.send(GetFileSettings(2))
                results["file_2_settings"] = file_settings
                log.info(f"File 2 Settings: {file_settings}")
            except Exception as e:
                log.warning(f"Could not read file settings: {e}")
                results["file_2_settings"] = None

        return results
