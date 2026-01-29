"""Utility functions for working with NTAG424 UIDs."""

class UID:
    """Reperesents a NTAG424 UID and provides utility methods."""
    
    def __init__(self, uid: bytes | str):
        """Initialize UID from bytes or hex string."""
        if isinstance(uid, bytes):
            self._uid_bytes = uid
        else:
            self._uid_bytes = bytes.fromhex(uid)

        self.uid: str = self._uid_bytes.hex().upper()

        if len(self._uid_bytes) < 7:
            raise ValueError(f"UID must be at least 7 bytes, got {len(self._uid_bytes)}: {self.uid}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UID):
            return False
        return self.uid == other.uid 
    
    def __hash__(self) -> int:
        return hash(self.uid)

    @property
    def bytes(self) -> bytes:
        """Get UID as bytes."""
        return self._uid_bytes
    
    def __str__(self):
        return f"UID({self.uid}, {self.asset_tag}, {self.short_hex})".upper()

    @property
    def asset_tag(self) -> str:
        """Convert UID to a short asset tag code for labeling.

        Format: XX-YYYY (7 chars with dash)
        Uses bytes 3-6 of UID (skips manufacturer ID and batch suffix).

        Args:
            uid: 7-byte UID

        Returns:
            7-character asset tag code (e.g., "6E-6B4A")

        Example:
            >>> UID(bytes.fromhex('046E6B4A2F7080')).asset_tag
            '6E-6B4A'
        """
        # Use bytes 1-4 (skip manufacturer byte 0x04, skip batch suffix 2F7080)
        # Format: uid[1] - uid[2]uid[3]uid[4]
        return f"{self._uid_bytes[1]:02X}-{self._uid_bytes[2]:02X}{self._uid_bytes[3]:02X}".upper()


    @property
    def short_hex(self) -> str:
        """Convert UID to compact hex string (last 3 bytes, 6 chars).

        Args:
            uid: 7-byte UID

        Returns:
            6-character hex code (e.g., "2F7080")

        Example:
            >>> uid_to_short_hex(bytes.fromhex('046E6B4A2F7080'))
            >>> UID(bytes.fromhex('046E6B4A2F7080')).short
            '2F7080'
        """
        # Last 3 bytes
        return self._uid_bytes[-3:].hex().upper()


    def matches(self, asset_tag: str) -> bool:
        """Check if an asset tag code matches a UID.

        Args:
            asset_tag: Asset tag code (format: "XX-YYYY" or "XXYYY")
            uid: 7-byte UID to check

        Returns:
            True if asset tag matches the UID's bytes 1-3

        Example:
            >>> UID('046E6B4A2F7080').matches("6E-6B4A")
            True
        """
        return asset_tag == self.asset_tag
