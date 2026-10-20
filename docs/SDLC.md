# Software Development Life Cycle (SDLC) Specification

**Repository**: GlobalHeadsOrTails  
**Owner**: Tank (DevOps Engineer)  
**Last Verified**: 2026-10-20  

---

## 1. Governance & Overview

All development in this repository strictly adheres to Bob Protocol SDLC standards. No work loop or sprint planning proceeds without this document.

### Architecture Topology
1. **Shared Contracts (`shared/`)**: Lightweight domain model definitions (`UID`, `Outcome`, `TagKeys`, `mask_key`) with zero external dependencies, establishing the universal contract across all services.
2. **Tag Validator Microservice (`tag_validator_service/`)**: Standalone stateless security microservice managing tag keys as k3s WORM secrets and performing NTAG 424 DNA SDM CMAC validation. Bundles the official client SDK (`tag_validator.client`).
3. **SDM Hardware Provisioner (`sdm_provisioner/`)**: Specialized PC/SC smartcard provisioning toolchain, hardware abstraction layer (`hal`), Textual TUI, and command orchestrators.
4. **Game Server (`game_server/`)**: Flask gameplay server, coin message service, VIP contact endpoints, Twelve Clans sticker catalog, and real-time polling state manager.
5. **Generic Art Generator (`tools/art_generator.py`)**: Domain-agnostic declarative YAML pipeline generating high-resolution WebP images into set-specific subdirectories with clean visual review contact sheets and zero card flair.

---

## 2. Tooling, Runtime & Environment

- **Primary Runtime**: Python 3.11+
- **Virtual Environment**: Unified workspace root `.venv` (`.venv/`) with all packages installed in editable mode (`make install-all`).
- **Container Runtime**: Docker / Podman / containerd / k3s.
- **Automation Interface**: `make` is mandatory for all builds, tests, lints, and container operations. No manual out-of-band commands that bypass `make`.

### Standard Makefile Targets per Service
- `make test`: Run automated unit and integration tests.
- `make lint`: Run syntax checks, type checks, and linters.
- `make pkg` / `make docker-build`: Build container images (`localhost/tag-validator-service:latest`).
- `make verify-container`: Verify container dependency graph, CLI check (`tag-validator --check`), and Gunicorn WSGI boot inside a read-only container.
- `make export-image` (or root `make export-tag-validator-image`): Build, verify, tag `localhost/tag-validator-service:$(VERSION)`, and export `dist/tag-validator-service-$(VERSION).tar` for `pi-patch` consumption.
- `make run`: Run development service locally.

---

## 3. Change Management & Source Control

- **Branching**: Features and sprints execute on `main` or designated feature branches.
- **TDD (Test-Driven Development)**: Write tests first before implementation.
- **Phase Quality Gates**: Every phase must pass UAT testing by Trin and code review by Morpheus before proceeding.
- **Sprint Close Audit**: Stage 3 requires Tank's `*devops sdlc-check`, Oracle doc grooming, and Smith UX acceptance before release.
- **Commit Rules**: Work is committed only when clean, passing all tests and linters. No committing sensitive files (`.env`, `*.log`, real private keys).

---

## 4. Kubernetes / k3s Secret Governance for Tag Keys

- Tag keys (specifically K3 / SDM MAC keys) are stored as Kubernetes `Secret` resources in the target k3s cluster namespace (default: `tag-secrets` or `default`).
- Secret Naming: `tag-key-<asset_tag>` or `tag-key-<uid_lowercase>`.
- Secret Labels:
  - `app.kubernetes.io/name`: `tag-validator-service`
  - `app.kubernetes.io/component`: `k3-secret`
- Data Fields:
  - `uid`: 14-hex character Tag UID (e.g. `04B7664A2F7080`).
  - `k3`: 32-hex character SDM MAC Key (AES-128).
  - `counter_offset`: Optional offset tracking.
- Stateless Validator Constraint: The validator microservice maintains **zero persistent local state** outside the secret store.
