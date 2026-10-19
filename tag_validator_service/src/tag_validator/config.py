"""Service configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Microservice runtime configuration."""

    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    secret_store_backend: str = os.getenv("SECRET_STORE_BACKEND", "memory").lower()
    tag_secrets_namespace: str = os.getenv("TAG_SECRETS_NAMESPACE", "tag-secrets")
    kubeconfig_path: str = os.getenv("KUBECONFIG", "")
    debug: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


def get_config() -> Config:
    return Config()
