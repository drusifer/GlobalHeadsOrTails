from abc import ABC, abstractmethod
from functools import wraps

from ..models import TagSecret


class KeyConflictError(Exception):
    """Raised when an attempt is made to overwrite an immutable key with a different value."""
    pass


class CounterStoreError(Exception):
    """The counter could not be read or written reliably; the caller must not treat the tap as used or fresh."""


class TagKeyStore(ABC):
    """Abstract base class for managing tag key secrets with internal WORM semantics."""

    def __init__(self) -> None:
        """Explicit base initializer for all TagKeyStore implementations."""
        self._base_initialized = True
        super().__init__()

    def __init_subclass__(cls, **kwargs) -> None:
        """Enforce that TagKeyStore.__init__ is always evaluated when instantiating subclasses."""
        super().__init_subclass__(**kwargs)
        subclass_init = cls.__init__

        @wraps(subclass_init)
        def _enforcing_init(self, *args, **kwargs):
            TagKeyStore.__init__(self)
            subclass_init(self, *args, **kwargs)
            if not getattr(self, "_base_initialized", False):
                raise RuntimeError(
                    f"Contract violation: {cls.__name__} failed to evaluate TagKeyStore.__init__()"
                )

        cls.__init__ = _enforcing_init

    @abstractmethod
    def get_key(self, uid: str, include_deleted: bool = False) -> TagSecret | None:
        """Retrieve a tag secret by UID. Defaults to active secrets only."""
        ...

    @abstractmethod
    def save_key(self, secret: TagSecret) -> bool:
        """Create or update a tag secret. Enforces WORM immutability on key data."""
        ...

    @abstractmethod
    def delete_key(self, uid: str) -> bool:
        """Soft-deletes a tag secret by UID (tombstoning). Does NOT physically delete."""
        ...

    @abstractmethod
    def undelete_key(self, uid: str) -> bool:
        """Restores a soft-deleted tag secret back to active status."""
        ...

    @abstractmethod
    def list_uids(self, include_deleted: bool = False) -> list[str]:
        """List managed tag UIDs (defaults to active only)."""
        ...

    @abstractmethod
    def consume_counter(self, uid: str, counter: int) -> bool:
        """Atomically record `counter` as the highest seen for `uid`.

        True if it was strictly greater than anything recorded before (now recorded); False if it
        is a replay. Raises CounterStoreError if the answer cannot be trusted."""
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if backend secret store is reachable/healthy."""
        ...

