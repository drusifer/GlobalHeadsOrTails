# Tag Keys K3s Secrets & Stateless CMAC Validator Service — 2026-10-18

**Status**: SPRINT PLANNING — READY FOR SMITH USER REVIEW  
**Author**: Cypher (Product Manager)  

---

## 1. Executive Summary & Sprint Scope

This sprint delivers a standalone microservice at the project top level (`tag_validator_service/`) responsible for:
1. Managing NTAG 424 DNA tag keys (specifically Key 3 / SDM MAC keys) as Kubernetes / k3s `Secret` objects.
2. Validating NTAG 424 DNA SDM CMAC signatures in a purely stateless manner.

### In Scope
- Standalone service directory at top-level: `tag_validator_service/`.
- Stateless REST API:
  - `POST /api/v1/validate` (JSON body: `uid`, `counter`, `cmac`) and `GET /api/v1/validate` (query params).
  - Secret management: `POST /api/v1/keys` (set/update tag key secret), `GET /api/v1/keys/{uid}` (get tag key status), `POST /api/v1/keys/import-csv` (bulk import from CSV).
  - Operational endpoints: `GET /healthz`, `GET /readyz`.
- Secret Store Adapters:
  - Native Kubernetes/k3s Secret adapter (using official Kubernetes API / in-cluster config / kubeconfig).
  - In-memory / mock secret store adapter for fast local testing, isolated CI, and offline execution without an active cluster.
- Crypto Engine:
  - Precise AN12196 / AN12343 NTAG 424 DNA SDM CMAC verification: SV2 derivation using K3, AES-128-CMAC session key, full CMAC over `UID&ctr=CTR&cmac=`, and AN12196 odd-byte truncation (indices 1, 3, 5, 7, 9, 11, 13, 15).
- Packaging & Operations:
  - `Makefile` with targets: `test`, `lint`, `run`, `docker-build`.
  - `Dockerfile` for lightweight container image.
  - Kubernetes/k3s deployment manifests (`k8s/deployment.yaml`, `k8s/rbac.yaml`, `k8s/service.yaml`).
- 100% unit and integration test coverage.

### Out of Scope
- Direct tag NFC hardware APDU communication (handled by provisioner TUI/hardware tools).
- Modifying game state or database tables in `ntag424_sdm_provisioner` (the validator microservice is completely stateless).
- Custom coin message storage (remains in application layer; validator only verifies CMAC validity).

---

## 2. User Stories & Acceptance Criteria

### Story 1: Stateless SDM CMAC Validation Endpoint
**As an** API client (game server or mobile tap proxy),  
**I want to** submit a tag's `uid`, `counter`, and `cmac` to `POST /api/v1/validate`,  
**So that** I receive a deterministic JSON validation verdict (`valid: true/false`) without the service storing any session state.

**Acceptance Criteria**:
1. When valid `uid`, `counter`, and matching `cmac` are submitted, returns HTTP 200 with `{"valid": true, "uid": "<UID>", "counter": <ctr>, "cmac_received": "...", "cmac_calculated": "..."}`.
2. When CMAC does not match the calculated signature, returns HTTP 200 with `{"valid": false, "error": "CMAC mismatch"}`.
3. When UID is not found in the k3s secret store, returns HTTP 404 with `{"valid": false, "error": "Tag key secret not found"}`.
4. Input validation rejects malformed UIDs (must be 14-character hex) or negative counters with HTTP 400.
5. Also supports query parameter format `GET /api/v1/validate?uid=...&ctr=...&cmac=...` for compatibility with URL redirects.

### Story 2: Tag Keys as k3s Secrets
**As a** cluster administrator / platform operator,  
**I want** each tag's cryptographic keys to be stored as a native Kubernetes/k3s `Secret`,  
**So that** tag keys leverage cluster-native secret management, encryption at rest, and RBAC.

**Acceptance Criteria**:
1. Tag secret is named `tag-key-<asset_tag>` or `tag-key-<uid_lower>` in namespace `default` (or `TAG_SECRETS_NAMESPACE`).
2. Secret contains data field `k3` (or `sdm_mac_key`) with the 32-character hex AES-128 key.
3. Service provides a Secret Adapter interface allowing switching between live k3s API and in-memory mock store via environment variable `SECRET_STORE_BACKEND` (`k3s` vs `memory`).
4. Microservice can be configured with namespace, kubeconfig path, or in-cluster ServiceAccount.

### Story 3: CSV Import Utility & Key Management API
**As an** operator migrating existing production tags,  
**I want to** import tag keys from existing `tag_keys.csv` into k3s Secrets via an API endpoint or CLI,  
**So that** existing provisioned tags are instantly recognized by the new service.

**Acceptance Criteria**:
1. Endpoint `POST /api/v1/keys/import-csv` accepts CSV text or file upload, validates each row, and creates/updates the corresponding k3s Secret.
2. CLI tool or make target (`make seed-secrets CSV=...`) executes the import.
3. Skips or logs malformed rows without failing the entire batch.
4. Single-key endpoint `POST /api/v1/keys` allows programmatic insertion or update of a tag secret.

### Story 4: Standalone Top-Level Service Architecture & Deployment
**As a** DevOps engineer,  
**I want** the service located at the project root `tag_validator_service/` with complete build automation,  
**So that** it can be built, tested, and deployed to k3s independently of `ntag424_sdm_provisioner`.

**Acceptance Criteria**:
1. Located at `tag_validator_service/` at workspace root.
2. Contains self-contained `Makefile` with `make test`, `make lint`, `make docker-build`.
3. Minimal `Dockerfile` producing a secure, unprivileged container image.
4. Includes Kubernetes manifests (`k8s/rbac.yaml`, `k8s/deployment.yaml`, `k8s/service.yaml`) defining Role with `get`, `list`, `create`, `update` permissions on `secrets`.
5. Health endpoints `GET /healthz` and `GET /readyz` return HTTP 200 when ready.

---

## 3. STORIES Rubric Self-Check
- `OUT=S`: Outcomes clearly defined (stateless CMAC microservice + k3s secrets backend).
- `TEST=S`: Detailed, testable acceptance criteria with HTTP status codes and payloads.
- `CLAR=S`: Boundaries explicitly delineated between in-scope and out-of-scope.
- `VALUE=S`: Strong business and architectural value (security hardening, decoupling, stateless scaling).
