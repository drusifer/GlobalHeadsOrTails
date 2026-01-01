"""Service for reading tag hardware and database status."""

import logging
from dataclasses import dataclass

from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.get_key_version import GetKeyVersion
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager, TagKeys
from ntag424_sdm_provisioner.hal import NTag424CardConnection


log = logging.getLogger(__name__)


@dataclass
class TagStatus:
    """Complete tag status from hardware and database."""

    uid: str
    key0_version: int
    key1_version: int
    key3_version: int
    db_keys: TagKeys | None
    hw_major_version: int
    hw_minor_version: int

    @property
    def is_factory_hardware(self) -> bool:
        """True if hardware shows factory key versions (all 0x00)."""
        return (
            self.key0_version == 0x00
            and self.key1_version == 0x00
            and self.key3_version == 0x00
        )


class TagStatusService:
    """Service for reading tag hardware and database status."""

    def __init__(self, card: NTag424CardConnection, key_manager: CsvKeyManager):
        """Initialize the service.

        Args:
            card: Connected card to read from
            key_manager: Key manager for database lookups
        """
        self.card = card
        self.key_manager = key_manager

    def read_tag_status(self) -> TagStatus:
        """Read complete tag status from hardware and database.

        Returns:
            TagStatus with all hardware and database information

        Raises:
            Exception if tag cannot be read
        """
        # Select application and read chip version
        self.card.send(SelectPiccApplication())
        version_info = self.card.send(GetChipVersion())
        uid = version_info.uid.hex().upper()

        # Read key versions from hardware
        key0_resp = self.card.send(GetKeyVersion(key_no=0))
        key1_resp = self.card.send(GetKeyVersion(key_no=1))
        key3_resp = self.card.send(GetKeyVersion(key_no=3))

        # Look up database keys
        try:
            db_keys = self.key_manager.get_tag_keys(uid)
        except Exception:
            db_keys = None

        return TagStatus(
            uid=uid,
            key0_version=key0_resp.version,
            key1_version=key1_resp.version,
            key3_version=key3_resp.version,
            db_keys=db_keys,
            hw_major_version=version_info.hw_major_version,
            hw_minor_version=version_info.hw_minor_version,
        )

    def update_widget(self, tag_status_widget, tag_status: TagStatus) -> None:
        """Update a TagStatusWidget with tag status.

        Args:
            tag_status_widget: Widget to update
            tag_status: Status to display
        """
        tag_status_widget.update_from_hardware(
            uid=tag_status.uid,
            key0_ver=tag_status.key0_version,
            key1_ver=tag_status.key1_version,
            key3_ver=tag_status.key3_version,
        )

        if tag_status.db_keys:
            tag_status_widget.db_keys = tag_status.db_keys
        else:
            tag_status_widget.db_keys = None
