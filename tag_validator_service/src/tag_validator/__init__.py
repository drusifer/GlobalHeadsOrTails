"""Tag Validator & K3s Secrets Microservice."""

from .api.app import TagValidatorApp, create_app
from .crypto.cmac_engine import calculate_sdm_cmac, verify_sdm_cmac
from .models import TagSecret, ValidationResult
from .store import K3sSecretStore, MemorySecretStore, TagKeyStore, create_secret_store

__version__ = "0.1.0"

__all__ = [
    "K3sSecretStore",
    "MemorySecretStore",
    "TagKeyStore",
    "TagSecret",
    "TagValidatorApp",
    "ValidationResult",
    "calculate_sdm_cmac",
    "create_app",
    "create_secret_store",
    "verify_sdm_cmac",
]
