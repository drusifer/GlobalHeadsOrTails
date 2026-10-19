"""In-memory thread-safe secret store for testing and standalone/stateless operation."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from ..models import TagSecret
from .base import KeyConflictError


class MemorySecretStore:
    """Thread-safe in-memory key-value secret store with WORM and soft-delete semantics."""

    def __init__(self, initial_keys: dict[str, TagSecret] | None = None) -> None:
        self._lock = threading.RLock()
        self._store: dict[str, TagSecret] = {}
        if initial_keys:
            for k, v in initial_keys.items():
                self._store[k.strip().upper()] = v

    def get_key(self, uid: str, include_deleted: bool = False) -> TagSecret | None:
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._lock:
            secret = self._store.get(clean_uid)
            if not secret:
                return None
            if not include_deleted and secret.status == "deleted":
                return None
            return secret

    def save_key(self, secret: TagSecret) -> bool:
        with self._lock:
            existing = self._store.get(secret.uid)
            if existing is not None:
                # WORM check: immutable key material
                if existing.k3 != secret.k3:
                    raise KeyConflictError(
                        f"Tag key for UID '{secret.uid}' is immutable and cannot be overwritten with a different key."
                    )
                # Idempotent or status update
                existing.status = secret.status
                existing.deleted_at = secret.deleted_at
                return True

            self._store[secret.uid] = secret
            return True

    def delete_key(self, uid: str) -> bool:
        """Soft-deletes a tag secret (tombstoning). Retains secret in memory."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._lock:
            secret = self._store.get(clean_uid)
            if not secret:
                return False
            secret.status = "deleted"
            secret.deleted_at = datetime.now(timezone.utc).isoformat()
            return True

    def undelete_key(self, uid: str) -> bool:
        """Restores a soft-deleted tag secret back to active."""
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._lock:
            secret = self._store.get(clean_uid)
            if not secret:
                return False
            secret.status = "active"
            secret.deleted_at = None
            return True

    def list_uids(self, include_deleted: bool = False) -> list[str]:
        with self._lock:
            if include_deleted:
                return sorted(list(self._store.keys()))
            return sorted([k for k, v in self._store.items() if v.status == "active"])

    def is_healthy(self) -> bool:
        return True

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

