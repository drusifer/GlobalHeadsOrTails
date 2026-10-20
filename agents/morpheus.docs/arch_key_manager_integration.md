# Technical Architecture: SDM Provisioner Key Manager Service Integration

**Owner**: Morpheus (Tech Lead)  
**Date**: 2026-10-20  
**Status**: Stage 1 - Sprint Planning (Gate 2 Review)  
**Related**: `docs/DECISIONS.md` (Decisions 9, 10), `agents/cypher.docs/key_manager_integration_sprint.md`  

---

## 1. Overview & Architectural Motivation

In Decision 10, the repository established `tag_validator_service` as a standalone security microservice managing NTAG 424 DNA tag credentials as Kubernetes/k3s WORM secrets. While `game_server` was integrated with `tag_validator_service` via `ServiceKeyManager`, the hardware provisioning toolchain `sdm_provisioner` remained coupled to local plaintext CSV files (`tag_keys.csv`).

This architecture integrates `sdm_provisioner` directly with `tag_validator_service` and SQLite `app.db`, delivering:
1. **Centralized Key Custody**: Key 0 (PICC Master Key), Key 1 (App Read Key), and Key 3 (SDM MAC Key) are generated and vaulted directly in `tag_validator_service`.
2. **Domain Decoupling**: Cryptographic keys stay inside `tag_validator_service`; coin game identities (`coin_name`, `outcome`, `rarity`) stay inside SQLite `data/app.db`.
3. **Strict Validation**: Fail-fast validation ensures no tags are provisioned unless the authoritative key service is healthy.

```
+─────────────────────────────────────────────────────────────+
|                     sdm_provisioner                         |
|                                                             |
|   +-----------------------+     +-----------------------+   |
|   |  Textual TUI / CLI    |     |  ProvisioningService  |   |
|   +-----------+-----------+     +-----------+-----------+   |
|               |                             |               |
|               +--------------+--------------+               |
|                              v                              |
|                    ServiceKeyManager                        |
|                     (Strict Mode)                           |
+──────────────────────+──────────────+───────────────────────+
                       |              |
         HTTP REST API |              | SQLite (Direct)
       (TAG_VALIDATOR) |              |
                       v              v
    +───────────────────────+    +────────────────────────+
    | tag_validator_service |    |      data/app.db       |
    |                       |    |                        |
    |  - Key 0 (PICC Master)|    |  - coins (coin_name,   |
    |  - Key 1 (App Read)   |    |           outcome,     |
    |  - Key 3 (SDM MAC)    |    |           rarity)      |
    |  - SDM CMAC Validator |    |  - game_state          |
    |  - WORM Secret Store  |    +────────────────────────+
    +───────────────────────+
```

---

## 2. Key Service Schema & API Expansion

### 2.1 `TagSecret` Model Extension
In `tag_validator_service/src/tag_validator/models.py`, `TagSecret` is expanded to store all three tag keys:
- `k0`: 32 hex chars (16 bytes AES-128) - PICC Master Key
- `k1`: 32 hex chars (16 bytes AES-128) - App Read Key
- `k3`: 32 hex chars (16 bytes AES-128) - SDM MAC Key

```python
@dataclass
class TagSecret:
    uid: str
    k3: str
    k0: str = "00000000000000000000000000000000"
    k1: str = "00000000000000000000000000000000"
    status: str = "active"
    created_at: str = ...
    deleted_at: str | None = None
```

### 2.2 REST API Endpoints
1. `POST /api/v1/keys/generate`:
   - Request: `{"uid": "04B7664A2F7080"}`
   - Behavior: Generates 3 independent CSPRNG AES-128 keys (`k0`, `k1`, `k3`), writes them to WORM storage, and returns:
     ```json
     {
       "status": "created",
       "uid": "04B7664A2F7080",
       "k0": "...",
       "k1": "...",
       "k3": "...",
       "message": "Keys generated and committed to WORM vault."
     }
     ```
2. `POST /api/v1/keys`:
   - Accepts `uid`, `k3`, optional `k0`, optional `k1`, `status`.
3. `GET /api/v1/keys/{uid}`:
   - Query param `?raw=true`: returns raw `k0`, `k1`, `k3` for authorized provisioner operations. Without `raw=true`, returns masked keys (`k0_masked`, `k1_masked`, `k3_masked`).

---

## 3. `sdm_provisioner.service_key_manager.ServiceKeyManager`

### 3.1 Contract & Capabilities
`ServiceKeyManager` implements the `KeyManager` interface used across `sdm_provisioner`:
- `__init__(service_url: str | None = None, db_path: str = "data/app.db", timeout_sec: float = 3.0)`:
  - Verifies service connectivity on startup. In strict mode, if `/healthz` fails, raises `ConnectionError("Cannot connect to tag_validator_service at ...")`.
- `provision_tag(uid, url=None, coin_name="", outcome=Outcome.INVALID)`:
  - Context manager implementing two-phase commit:
    - Calls `client.generate_key(uid)` to obtain and vault `k0`, `k1`, `k3`.
    - Yields `TagKeys` with raw bytes for APDU transmission (`get_picc_master_key_bytes()`, etc.).
    - If APDUs succeed, commits coin name/outcome in `app.db` and updates status to `keys_configured` or `provisioned`.
    - If APDUs fail, rolls back / logs error.
- `validate_sdm_url(uid, counter, cmac)`:
  - Delegates to `client.validate_tag(uid, counter, cmac)`.

---

## 4. TUI Integration & Fail-Fast UX

In `sdm_provisioner/src/sdm_provisioner/tui/app.py`:
- `NtagProvisionerApp.__init__` instantiates `ServiceKeyManager`.
- If `tag_validator_service` is offline, the TUI detects this during startup and halts with a clear error prompt:
  ```
  [FATAL ERROR]
  tag_validator_service is unreachable at http://localhost:8080.
  
  sdm_provisioner operates in strict key-vault mode.
  Please start the key service:
      make run-tag-validator
  ```

---

## 5. Security & Verification Strategy

- **Zero Plaintext Key Files**: Eliminates creation of `tag_keys.csv`.
- **Masked Logging**: All key material formatted with `mask_key()`.
- **Test Matrix**:
  - `tag_validator_service/tests/`: 26+ tests covering 3-key storage and retrieval.
  - `sdm_provisioner/tests/`: New `test_service_key_manager.py` with mock WSGI client and SQLite fixture.
  - Full regression: 367+ tests passing.
