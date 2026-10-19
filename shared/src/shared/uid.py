"""Utility classes and functions for working with NTAG424 UIDs."""

from __future__ import annotations


class UID:
    """Represents an NTAG424 7-byte UID and provides formatting and utility methods."""

    def __init__(self, uid: bytes | str) -> None:
        """Initialize UID from bytes or hex string."""
        if isinstance(uid, (bytes, bytearray)):
            self._uid_bytes = bytes(uid)
        elif isinstance(uid, str):
            clean = uid.strip().replace(":", "").replace("-", "").replace(" ", "")
            self._uid_bytes = bytes.fromhex(clean)
        elif isinstance(uid, UID):
            self._uid_bytes = uid.bytes
        else:
            raise TypeError(f"Expected bytes or str for UID, got {type(uid)}")

        self.uid: str = self._uid_bytes.hex().upper()

        if len(self._uid_bytes) < 7:
            raise ValueError(f"UID must be at least 7 bytes, got {len(self._uid_bytes)}: {self.uid}")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UID):
            return self.uid == other.uid
        if isinstance(other, str):
            clean = other.strip().replace(":", "").replace("-", "").replace(" ", "").upper()
            return self.uid == clean
        return False

    def __hash__(self) -> int:
        return hash(self.uid)

    def __repr__(self) -> str:
        return f"UID({self.uid!r})"

    def __str__(self) -> str:
        return f"UID({self.uid}, {self.asset_tag}, {self.short_hex})".upper()

    @property
    def bytes(self) -> bytes:
        """Get UID as raw bytes."""
        return self._uid_bytes

    @property
    def asset_tag(self) -> str:
        """Convert UID to a short asset tag code for labeling.

        Format: XX-YYYY (7 chars with dash)
        Uses bytes 1-4 (skips manufacturer ID byte 0 and batch suffix).
        """
        return f"{self._uid_bytes[1]:02X}-{self._uid_bytes[2]:02X}{self._uid_bytes[3]:02X}".upper()

    @property
    def short_hex(self) -> str:
        """Convert UID to compact hex string (last 3 bytes, 6 chars)."""
        return self._uid_bytes[-3:].hex().upper()

    def matches(self, asset_tag: str) -> bool:
        """Check if an asset tag code matches this UID."""
        return asset_tag.strip().upper() == self.asset_tag
