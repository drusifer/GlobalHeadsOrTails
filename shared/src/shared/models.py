"""Core domain models for NTAG424 tags."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from shared.outcome import Outcome
from shared.uid import UID


def mask_key(key: str | None) -> str:
    """Mask sensitive 32-character hex key string."""
    if not key:
        return "None"
    key_clean = key.strip()
    if len(key_clean) < 16:
        return "***"
    return f"{key_clean[:4]}...{key_clean[-4:]}"


@dataclass
class TagKeys:
    """Keys and metadata for a single NTAG424 DNA tag."""

    uid: UID
    picc_master_key: str
    app_read_key: str
    sdm_mac_key: str
    outcome: Outcome = Outcome.INVALID
    coin_name: str = ""
    provisioned_date: str = ""
    status: str = "factory"
    notes: str = ""
    last_used_date: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.uid, (str, bytes, bytearray)):
            self.uid = UID(self.uid)
        if isinstance(self.outcome, str):
            self.outcome = Outcome(self.outcome)

    def get_picc_master_key_bytes(self) -> bytes:
        return bytes.fromhex(self.picc_master_key)

    def get_app_read_key_bytes(self) -> bytes:
        return bytes.fromhex(self.app_read_key)

    def get_sdm_mac_key_bytes(self) -> bytes:
        return bytes.fromhex(self.sdm_mac_key)

    def get_asset_tag(self) -> str:
        return self.uid.asset_tag

    @staticmethod
    def from_factory_keys(uid: UID | str) -> TagKeys:
        uid_obj = uid if isinstance(uid, UID) else UID(uid)
        factory_key = "0" * 32
        return TagKeys(
            uid=uid_obj,
            picc_master_key=factory_key,
            app_read_key=factory_key,
            sdm_mac_key=factory_key,
            outcome=Outcome.INVALID,
            coin_name="",
            provisioned_date=datetime.now(UTC).isoformat(),
            status="factory",
            notes="Factory default keys",
            last_used_date="",
        )
