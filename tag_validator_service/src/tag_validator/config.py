"""Service configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Microservice runtime configuration."""

    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))
    secret_store_backend: str = field(
        default_factory=lambda: os.getenv("SECRET_STORE_BACKEND", "memory").lower()
    )
    tag_secrets_namespace: str = field(
        default_factory=lambda: os.getenv("TAG_SECRETS_NAMESPACE", "tag-secrets")
    )
    kubeconfig_path: str = field(default_factory=lambda: os.getenv("KUBECONFIG", ""))
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    )


def get_config() -> Config:
    return Config()
