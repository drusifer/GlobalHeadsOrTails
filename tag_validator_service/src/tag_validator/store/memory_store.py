"""In-memory thread-safe secret store for testing and standalone/stateless operation."""

from __future__ import annotations

import threading

from ..models import TagSecret


class MemorySecretStore:
    """Thread-safe in-memory key-value secret store."""

    def __init__(self, initial_keys: dict[str, TagSecret] | None = None) -> None:
        self._lock = threading.RLock()
        self._store: dict[str, TagSecret] = {}
        if initial_keys:
            for k, v in initial_keys.items():
                self._store[k.strip().upper()] = v

    def get_key(self, uid: str) -> TagSecret | None:
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._lock:
            return self._store.get(clean_uid)

    def save_key(self, secret: TagSecret) -> bool:
        with self._lock:
            self._store[secret.uid] = secret
            return True

    def delete_key(self, uid: str) -> bool:
        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        with self._lock:
            if clean_uid in self._store:
                del self._store[clean_uid]
                return True
            return False

    def list_uids(self) -> list[str]:
        with self._lock:
            return sorted(list(self._store.keys()))

    def is_healthy(self) -> bool:
        return True

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
