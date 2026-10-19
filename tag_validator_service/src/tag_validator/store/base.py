"""Base interface for secret storage backends."""

from typing import Protocol

from ..models import TagSecret


class TagKeyStore(Protocol):
    """Protocol for managing tag key secrets."""

    def get_key(self, uid: str) -> TagSecret | None:
        """Retrieve a tag secret by UID."""
        ...

    def save_key(self, secret: TagSecret) -> bool:
        """Create or update a tag secret."""
        ...

    def delete_key(self, uid: str) -> bool:
        """Delete a tag secret by UID."""
        ...

    def list_uids(self) -> list[str]:
        """List all managed tag UIDs."""
        ...

    def is_healthy(self) -> bool:
        """Check if backend secret store is reachable/healthy."""
        ...
