"""Base interface for secret storage backends."""

from typing import Protocol

from ..models import TagSecret


class KeyConflictError(Exception):
    """Raised when an attempt is made to overwrite an immutable key with a different value."""
    pass


class TagKeyStore(Protocol):
    """Protocol for managing tag key secrets with internal WORM semantics."""

    def get_key(self, uid: str, include_deleted: bool = False) -> TagSecret | None:
        """Retrieve a tag secret by UID. Defaults to active secrets only."""
        ...

    def save_key(self, secret: TagSecret) -> bool:
        """Create or update a tag secret. Enforces WORM immutability on key data."""
        ...

    def delete_key(self, uid: str) -> bool:
        """Soft-deletes a tag secret by UID (tombstoning). Does NOT physically delete."""
        ...

    def undelete_key(self, uid: str) -> bool:
        """Restores a soft-deleted tag secret back to active status."""
        ...

    def list_uids(self, include_deleted: bool = False) -> list[str]:
        """List managed tag UIDs (defaults to active only)."""
        ...

    def is_healthy(self) -> bool:
        """Check if backend secret store is reachable/healthy."""
        ...

