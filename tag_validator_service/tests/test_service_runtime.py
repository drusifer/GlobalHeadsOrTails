"""Unit tests for standalone tag_validator_service runtime configuration, CLI entrypoint, and container packaging."""

from __future__ import annotations

from pathlib import Path

import pytest

from tag_validator.config import get_config

SERVICE_ROOT = Path(__file__).resolve().parents[1]


def test_get_config_reads_dynamic_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_config() dynamically reads environment variables at call time."""
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9091")
    monkeypatch.setenv("SECRET_STORE_BACKEND", "K3S")
    monkeypatch.setenv("TAG_SECRETS_NAMESPACE", "custom-ns")
    monkeypatch.setenv("KUBECONFIG", "/tmp/test-kubeconfig")
    monkeypatch.setenv("DEBUG", "true")

    cfg = get_config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9091
    assert cfg.secret_store_backend == "k3s"
    assert cfg.tag_secrets_namespace == "custom-ns"
    assert cfg.kubeconfig_path == "/tmp/test-kubeconfig"
    assert cfg.debug is True


def test_app_main_check_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify tag_validator.api.app:main entrypoint supports --check for standalone service verification."""
    from tag_validator.api.app import main

    monkeypatch.setenv("SECRET_STORE_BACKEND", "memory")
    monkeypatch.setenv("PORT", "8085")

    main(["--check"])
    captured = capsys.readouterr()
    assert "tag-validator-service check OK" in captured.out
    assert "backend=memory" in captured.out
    assert "port=8085" in captured.out


def test_container_and_pi_patch_packaging_contracts() -> None:
    """Verify Dockerfile, .dockerignore, and Makefile targets for standalone pi-patch container export."""
    dockerfile = (SERVICE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.txt" not in dockerfile
    assert "COPY pyproject.toml README.md /app/" in dockerfile
    assert 'pip install --no-cache-dir ".[k3s,server]" && pip check' in dockerfile
    assert "--worker-tmp-dir" in dockerfile
    assert "tag_validator.api.app:create_app()" in dockerfile

    dockerignore = (SERVICE_ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "__pycache__/" in dockerignore
    assert "dist/" in dockerignore

    makefile = (SERVICE_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "pkg:" in makefile
    assert "verify-container:" in makefile
    assert "export-image:" in makefile
    assert "dist/tag-validator-service-$(VERSION).tar" in makefile

    k8s_deploy = (SERVICE_ROOT / "k8s" / "deployment.yaml").read_text(encoding="utf-8")
    assert "image: localhost/tag-validator-service:latest" in k8s_deploy
    assert "containerPort: 8080" in k8s_deploy

