# Architecture Specification: Tag Validator & K3s Secrets Microservice

**Document**: `agents/morpheus.docs/arch_tag_secrets_service.md`  
**Author**: Morpheus (Tech Lead)  
**Date**: 2026-10-18  
**Status**: COMPLETE — SUBMITTED FOR GATE 2 (SMITH UX/API REVIEW)  

---

## 1. System Overview & Architectural Bounds

The `tag_validator_service` is an independent, lightweight, containerized microservice located at the repository root. It solves two architectural challenges:
1. **Decoupling Secret Storage from File System**: Eliminates local plaintext `tag_keys.csv` dependency by storing tag cryptographic secrets (specifically Key 3 / SDM MAC keys) in native Kubernetes/k3s `Secret` objects.
2. **Stateless SDM CMAC Verification**: Provides high-throughput, horizontally scalable verification of NTAG 424 DNA Secure Dynamic Messaging (SDM) signatures without maintaining local session or database state.

```
                          ┌──────────────────────────────────────┐
                          │     Kubernetes / k3s Cluster         │
                          │                                      │
  Client / Monolith       │    ┌────────────────────────────┐    │
 (Game Server / App)      │    │   k3s Secrets Namespace    │    │
         │                │    │    "tag-secrets"           │    │
         │                │    │  ┌──────────────────────┐  │    │
         │ HTTP POST/GET  │    │  │ Secret: tag-key-04b7 │  │    │
         │ /api/v1/validate    │  │  data:               │  │    │
         ▼                │    │  │    uid: 04B7...      │  │    │
┌──────────────────┐      │    │  │    k3:  825f...      │  │    │
│ Tag Validator    │      │    │  └──────────────────────┘  │    │
│  Microservice    │──────┼───►│  ┌──────────────────────┐  │    │
│ (Stateless Pods) │      │    │  │ Secret: tag-key-04ae │  │    │
│                  │      │    │  └──────────────────────┘  │    │
└──────────────────┘      │    └────────────────────────────┘    │
                          └──────────────────────────────────────┘
```

---

## 2. Component Design

### 2.1 Crypto Engine (`tag_validator.crypto.cmac_engine`)
- **System Vector Construction (`build_system_vector`)**:
  - `SV2 = 3Ch || C3h || 00h || 01h || 00h || 80h || UID(7 bytes) || SDMReadCtr(3 bytes, Little-Endian)` = Exactly 16 bytes per NXP AN12196 §9.3.9.1.
- **Session Key Derivation**:
  - `Session_Key = AES-128-CMAC(SV2, key=K3)` (16 bytes).
- **Message Calculation**:
  - `cmac_message = f"{uid}&ctr={counter:06X}&cmac=".encode('ascii')`.
  - `Full_CMAC = AES-128-CMAC(cmac_message, key=Session_Key)` (16 bytes).
- **Truncation**:
  - Extracts 8 bytes at Python 0-indexed odd positions `[1, 3, 5, 7, 9, 11, 13, 15]` per AN12196.
- **Constant-Time Verification**:
  - Uses `hmac.compare_digest` to prevent timing attacks.

### 2.2 Pluggable Secret Store Adapter (`tag_validator.store`)
Defines the `TagKeyStore` interface:
```python
class TagKeyStore(Protocol):
    def get_key(self, uid: str) -> Optional[TagSecret]: ...
    def save_key(self, secret: TagSecret) -> bool: ...
    def list_keys(self) -> list[str]: ...
```
1. **`K3sSecretStore`**:
   - Uses `kubernetes.client.CoreV1Api` with `load_incluster_config()` or `load_kube_config()`.
   - Reads/writes Kubernetes `Secret` resources in target namespace (default `tag-secrets`).
   - Secret naming convention: `tag-key-<uid_lowercase>` (RFC 1123 compliant).
   - Secret data fields: `uid`, `k3` (base64-encoded hex string), optional `coin_name`, `status`.
2. **`MemorySecretStore`**:
   - Fast, thread-safe in-memory dictionary store for unit testing, offline execution, and fallback scenarios without Kubernetes dependencies.
   - Selected via `SECRET_STORE_BACKEND=memory` (default for local development and test runs).

### 2.3 Stateless REST API (`tag_validator.api.app`)
Endpoints:
- `POST /api/v1/validate`:
  - Request: `{"uid": "04B7664A2F7080", "counter": 5, "cmac": "A1B2C3D4E5F67890"}`
  - Response (200): `{"valid": true, "uid": "04B7664A2F7080", "counter": 5, "cmac_received": "...", "cmac_calculated": "..."}`
  - Response (404): `{"valid": false, "error": "Tag key secret not found"}`
  - Response (400): `{"valid": false, "error": "Invalid UID format or counter"}`
- `GET /api/v1/validate`:
  - Query parameters: `?uid=04B7664A2F7080&ctr=5&cmac=A1B2C3D4E5F67890` (and `counter=` alias).
- `POST /api/v1/keys`:
  - Saves or updates a tag secret in k3s.
- `GET /api/v1/keys/{uid}`:
  - Fetches metadata for tag key (masked key bytes for security).
- `POST /api/v1/keys/import-csv`:
  - Batch uploads and parses CSV rows to seed k3s secrets.
- `GET /healthz`, `GET /readyz`:
  - Kubernetes liveness and readiness probes.

---

## 3. Top-Level Directory Layout

```
GlobalHeadsOrTails/
├── tag_validator_service/              <-- Top-level microservice
│   ├── src/
│   │   └── tag_validator/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── crypto/
│   │       │   ├── __init__.py
│   │       │   └── cmac_engine.py
│   │       ├── store/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── memory_store.py
│   │       │   └── k3s_store.py
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   └── app.py
│   │       └── cli/
│   │           ├── __init__.py
│   │           └── importer.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_cmac_engine.py
│   │   ├── test_secret_store.py
│   │   ├── test_api.py
│   │   └── test_csv_importer.py
│   ├── k8s/
│   │   ├── rbac.yaml
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── Dockerfile
│   ├── Makefile
│   ├── pyproject.toml
│   └── README.md
```

---

## 4. Operational & SDLC Feasibility

- **Dependencies**: Uses standard Python cryptography (`cryptography` or standard `hashlib`/`hmac` with AES CBC/CMAC), `flask` or `fastapi`, and optional `kubernetes` client.
- **Makefile Standard Targets**:
  - `make test`: Executes all pytest suites with memory backend.
  - `make lint`: Validates code style and typing.
  - `make run`: Runs microservice locally on port 8080.
  - `make docker-build`: Builds container image `localhost/tag-validator-service:latest`.
- **Zero Monolith Regression**: Does not alter `ntag424_sdm_provisioner` internals; exists purely as an autonomous service ready to receive requests.

---

## 5. ARCH Rubric Self-Check
- `BOUND=S`: Clear service boundaries; completely stateless compute layer decoupled from secret storage.
- `FLOW=S`: Simple, deterministic request/response flows for both JSON POST and query parameter validation.
- `FAIL=S`: Explicit error codes for missing keys (404), CMAC mismatches (200 with `valid: false`), and invalid inputs (400).
- `USER=S`: Dual GET/POST support allows direct use as an HTTP hook or REST API. Masked keys in info endpoints protect secrets.
- `DECS=S`: Documented decision to use pluggable store adapter (`MemorySecretStore` vs `K3sSecretStore`) ensuring local testability.
- `FEAS=S`: Conforms 100% to `docs/SDLC.md` requirements with self-contained Makefile and Docker packaging.
