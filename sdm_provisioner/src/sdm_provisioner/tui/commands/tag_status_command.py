"""TagStatusCommand - Check tag status (Factory vs Provisioned)."""

import logging
from typing import Any

from sdm_provisioner.card_factory import CardConnectionFactory
from sdm_provisioner.commands.get_chip_version import GetChipVersion
from sdm_provisioner.constants import FACTORY_KEY
from sdm_provisioner.crypto.auth_session import AuthenticateEV2
from sdm_provisioner.csv_key_manager import CsvKeyManager
from sdm_provisioner.sequence_logger import SequenceLogger
from sdm_provisioner.tui.clock import Clock, RealClock
from sdm_provisioner.tui.nfc_command import NFCCommand


class TagStatusCommand(NFCCommand):
    """Check tag status (Factory vs Provisioned)."""

    def __init__(self, clock: Clock | None = None):
        self._clock = clock or RealClock()

    @property
    def timeout_seconds(self) -> int:
        return 15

    @property
    def operation_name(self) -> str:
        return "Check Tag Status"

    def execute(self) -> dict[str, Any]:
        results = {}

        with CardConnectionFactory.create(sequence_logger=SequenceLogger()) as connection:
            log = logging.getLogger(__name__)
            log.info("Connected to tag")

            # 1. Get Version & UID
            version = connection.send(GetChipVersion())
            results["version"] = version
            uid = version.uid
            if hasattr(uid, "uid"):
                results["uid"] = uid.uid
            elif isinstance(uid, (bytes, bytearray)):
                results["uid"] = uid.hex().upper()
            else:
                results["uid"] = str(uid).upper()
            log.info(f"UID: {results['uid']}")

            # 2. Check Factory State (Auth with Key 0 = 00...00)
            try:
                # Use AuthenticateEV2 orchestrator to perform full handshake
                AuthenticateEV2(FACTORY_KEY, 0)(connection)
                results["status"] = "Factory New"
                results["key_state"] = "Default Keys"
                log.info("Tag is in Factory State")
                return results
            except Exception:
                log.info("Factory Auth failed, checking provisioned keys...")

            # 3. Check Provisioned State
            key_mgr = CsvKeyManager()
            try:
                stored_keys = key_mgr.get_tag_keys(uid)
                if stored_keys.status == "factory":
                    # We already tried factory keys and failed, so it's unknown
                    results["status"] = "Unknown"
                    results["key_state"] = "Auth Failed (Expected Factory)"
                else:
                    master_key = stored_keys.get_picc_master_key_bytes()
                    AuthenticateEV2(master_key, 0)(connection)
                    results["status"] = "Provisioned"
                    results["key_state"] = "Registered Keys"
                    log.info("Tag is Provisioned")
            except Exception as e:
                log.warning(f"Provisioned Auth failed: {e}")
                results["status"] = "Unknown / Locked"
                results["key_state"] = "Auth Failed"

        return results
