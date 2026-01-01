import logging
import os
from contextlib import AbstractContextManager

from ntag424_sdm_provisioner.hal import CardManager, NTag424CardConnection
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger
from ntag424_sdm_provisioner.seritag_simulator import SeritagCardManager


log = logging.getLogger(__name__)


class CardConnectionFactory:
    """Factory for creating card connections.

    Switches between real hardware and simulation based on environment variables.
    """

    @staticmethod
    def create(sequence_logger: SequenceLogger) -> AbstractContextManager[NTag424CardConnection]:
        """Create a context manager that yields a card connection.

        Args:
            sequence_logger: Logger for command sequence tracing (required)

        Returns:
            AbstractContextManager yielding NTag424CardConnection-compatible object
        """
        if os.environ.get("NTAG_SIMULATION") == "1":
            log.info("Using SIMULATED card connection (SeritagSimulator)")
            # SeritagCardManager yields a SeritagCardConnection
            # We need to ensure it's compatible or wrapped if necessary
            # For now, we assume SeritagCardConnection implements the required interface
            return SeritagCardManager(sequence_logger)
        else:
            log.info("Using REAL card connection (PCSC)")
            return CardManager(sequence_logger)
