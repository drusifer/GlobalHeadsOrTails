import logging
import os
from contextlib import AbstractContextManager

from sdm_provisioner.hal import CardManager, NTag424CardConnection
from sdm_provisioner.sequence_logger import SequenceLogger
from sdm_provisioner.seritag_simulator import SeritagCardManager


log = logging.getLogger(__name__)


class CardConnectionFactory:
    """Factory for creating card connections.

    Switches between real hardware and simulation based on environment variables.
    """

    @staticmethod
    def create(
        sequence_logger: SequenceLogger,
        key_store: object | None = None,
    ) -> AbstractContextManager[NTag424CardConnection]:
        """Create a context manager that yields a card connection.

        Args:
            sequence_logger: Logger for command sequence tracing (required)
            key_store: Optional key store. For real hardware, defaults to real ServiceKeyManager.

        Returns:
            AbstractContextManager yielding NTag424CardConnection-compatible object
        """
        if os.environ.get("NTAG_SIMULATION") == "1":
            log.info("Using SIMULATED card connection (SeritagSimulator)")
            return SeritagCardManager(sequence_logger, key_store=key_store)
        else:
            log.info("Using REAL card connection (PCSC)")
            return CardManager(sequence_logger, key_store=key_store)
