from .base import TagKeyStore
from .k3s_store import K3sSecretStore
from .memory_store import MemorySecretStore


def create_secret_store(
    backend: str = "memory",
    namespace: str = "tag-secrets",
    kubeconfig_path: str | None = None,
) -> TagKeyStore:
    """Factory creating the appropriate TagKeyStore backend."""
    b = backend.lower()
    if b in ("k3s", "k8s", "kubernetes"):
        return K3sSecretStore(namespace=namespace, kubeconfig_path=kubeconfig_path)
    return MemorySecretStore()


__all__ = [
    "K3sSecretStore",
    "MemorySecretStore",
    "TagKeyStore",
    "create_secret_store",
]
