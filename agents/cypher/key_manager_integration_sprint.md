# Sprint Backlog: SDM Provisioner Key Manager Service Integration

**Sprint Name**: SDM Provisioner Key Manager Service Integration  
**Owner**: Cypher (Product Manager)  
**Date**: 2026-10-20  
**Status**: Stage 1 - Sprint Planning (Gate 1 Review)  

---

## 1. Executive Summary & Objective

Decouple `sdm_provisioner` from monolithic local CSV storage (`tag_keys.csv`) by integrating it directly with the new `tag_validator_service` key vault and SQLite `app.db`.

Per user architectural clarification:
1. **Strict Connection**: `sdm_provisioner` strictly connects to `tag_validator_service` (via `TAG_VALIDATOR_URL`, default `http://localhost:8080`) and fails fast with clear guidance if the service is unreachable.
2. **SQLite `app.db`**: Coin domain identities (`coin_name`, `outcome`, `clan`, `rarity`) are persisted in SQLite `data/app.db` (`coins` table), aligning with `game_server` and Decision 10.
3. **Full Custom Keys**: Key 0 (PICC Master Key), Key 1 (App Read Key), and Key 3 (SDM MAC Key) are all generated and stored in `tag_validator_service` WORM storage, establishing centralized cryptographic authority.

---

## 2. User Stories & Acceptance Criteria

### US-KMS-001: Extend `tag_validator_service` Schema for Full Custom Keys
**As a** security officer and hardware provisioner,  
**I want** `tag_validator_service` to store all three tag keys (Key 0 PICC Master, Key 1 App Read, Key 3 SDM MAC),  
**So that** all tag credentials are held in centralized, secure WORM storage instead of scattered local files.

#### Acceptance Criteria
- [ ] `TagSecret` data model in `tag_validator_service/src/tag_validator/models.py` extended with `k0` (PICC Master) and `k1` (App Read), both 32 hex chars AES-128, alongside existing `k3`.
- [ ] Serialization to/from Kubernetes secret data (`to_k8s_secret_data`, `from_k8s_secret_data`) and dictionary payloads updated with backward-compatible defaults.
- [ ] `POST /api/v1/keys/generate` atomically generates CSPRNG keys for `k0`, `k1`, `k3` and commits the secret to the vault, returning all three keys in the creation response.
- [ ] `POST /api/v1/keys` accepts `k0`, `k1`, `k3`.
- [ ] `GET /api/v1/keys/{uid}` supports returning raw keys when `?raw=true` or when requested by provisioner, defaulting to masked keys for public inspection.
- [ ] `TagValidatorClient` SDK in `tag_validator_service/src/tag_validator/client.py` updated to return and handle `k0`, `k1`, `k3`.
- [ ] Unit tests in `tag_validator_service/tests/` verify full key storage, generation, and retrieval (all tests passing).

---

### US-KMS-002: Implement `ServiceKeyManager` in `sdm_provisioner`
**As a** hardware provisioner operator,  
**I want** a dedicated `ServiceKeyManager` in `sdm_provisioner` that interfaces with `tag_validator_service` and SQLite `app.db`,  
**So that** tag provisioning operations use vaulted keys and persist coin identities without local CSV dependencies.

#### Acceptance Criteria
- [ ] `ServiceKeyManager` created in `sdm_provisioner/src/sdm_provisioner/service_key_manager.py` implementing the `KeyManager` interface.
- [ ] Implements strict connection check: verifies `tag_validator_service` health (`/healthz`) on initialization, raising a clear error if unreachable.
- [ ] Implements two-phase provisioning context manager `provision_tag(uid, url, coin_name, outcome)`:
  - Generates `k0`, `k1`, `k3` via `tag_validator_service` (`/api/v1/keys/generate`).
  - Sets coin name and outcome in `data/app.db`.
  - Yields staged `TagKeys` containing raw key bytes for APDU execution.
  - Commits status to `keys_configured` or `provisioned`.
- [ ] Implements `update_url(uid, url)` context manager for NDEF updates.
- [ ] Implements `validate_sdm_url(uid, counter, cmac)` delegating to `tag_validator_service` (`/api/v1/validate`).
- [ ] Implements `get_tag_keys(uid)`, `list_tags()`, `list_coins()`, `assign_coin_name()`, `delete_key()`, `undelete_key()`.
- [ ] Comprehensive unit tests in `sdm_provisioner/tests/test_service_key_manager.py` passing with 100% test success.

---

### US-KMS-003: Wire TUI, CLI & Provisioning Tools to `ServiceKeyManager`
**As an** operations user running `provision-tui` or `provision-tag`,  
**I want** the TUI and provisioning tools to use `ServiceKeyManager` by default,  
**So that** all interactive provisioning workflows burn vaulted keys directly to chips.

#### Acceptance Criteria
- [ ] `NtagProvisionerApp` in `sdm_provisioner/src/sdm_provisioner/tui/app.py` instantiates `ServiceKeyManager` as `self.key_manager`.
- [ ] If `tag_validator_service` is offline, TUI fails fast on startup with a descriptive, user-friendly error message detailing how to start the service (`make run-tag-validator`).
- [ ] TUI screens (`ProvisionScreen`, `ConfigureKeysScreen`, `TagStatusScreen`, `ReadTagScreen`, `FormatPICCScreen`, `KeyRecoveryScreen`, `CoinNamingScreen`) execute seamlessly against `ServiceKeyManager`.
- [ ] `ProvisioningService` in `sdm_provisioner/src/sdm_provisioner/services/provisioning_service.py` receives and uses `ServiceKeyManager`.
- [ ] `ToolRunner` and individual tools in `sdm_provisioner/src/sdm_provisioner/tools/` support `ServiceKeyManager`.

---

### US-KMS-004: Regression Testing & Sprint Verification
**As a** QA Guardian and DevOps engineer,  
**I want** complete regression test coverage across all workspace components,  
**So that** integrating the new key manager service causes zero regressions.

#### Acceptance Criteria
- [ ] All `tag_validator_service` unit and integration tests pass.
- [ ] All `sdm_provisioner` unit tests pass (including new service key manager tests).
- [ ] All `game_server`, `shared`, and `tools` tests pass.
- [ ] Total passing tests across the workspace is >= 375 tests (100% pass rate).
- [ ] Documentation updated in `docs/DECISIONS.md` (Decision 13) and `docs/SDLC.md`.
