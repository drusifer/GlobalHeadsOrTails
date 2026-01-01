"""ProvisionTagCommand - Headless provision operation."""

import logging
from typing import Any

from ntag424_sdm_provisioner.card_factory import CardConnectionFactory
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger
from ntag424_sdm_provisioner.services.provisioning_service import ProvisioningService
from ntag424_sdm_provisioner.tui.clock import Clock, RealClock
from ntag424_sdm_provisioner.tui.nfc_command import NFCCommand


class ProvisionTagCommand(NFCCommand):
    """Provision tag without UI dependency."""

    def __init__(self, base_url: str = "https://example.com/verify", clock: Clock | None = None):
        self._base_url = base_url
        self._clock = clock or RealClock()

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def operation_name(self) -> str:
        return "Provision Tag"

    def execute(self) -> Any:
        """Execute the provision operation.

        Returns:
            Provisioning result from ProvisioningService
        """
        with CardConnectionFactory.create(sequence_logger=SequenceLogger()) as connection:
            key_mgr = CsvKeyManager("tag_keys.csv")
            service = ProvisioningService(connection, key_mgr)

            log = logging.getLogger(__name__)
            log.info("Starting provisioning...")
            result = service.provision()
            log.info("Provisioning complete")

            return result
