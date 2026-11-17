# Sprint: Key Service Segmentation & Internal WORM Architecture

## Sprint Metadata
- **Sprint Name**: `key service segmentation`
- **Goal**: Decouple the coin game domain from the tag key service, consolidate cryptographic key creation and custody into `tag_validator_service`, implement internal WORM storage with soft-delete/undelete, and establish `app.db` ownership of game metadata.
- **Product Owner**: Cypher
- **Tech Lead**: Morpheus
- **QA Guardian**: Trin
- **UX & Governance**: Smith

---

## 1. Context & Business Drivers
The initial implementation of `tag_validator_service` bundled `coin_name` into tag secret models and Kubernetes secret annotations. Furthermore, key generation remained scattered in provisioning scripts, and keys were physically mutable.

To achieve enterprise-grade security and clean microservice boundaries:
1. **Stateless Security Appliance**: `tag_validator_service` must be purely a hardware key vault and stateless CMAC validator. It has zero knowledge of gameplay, coin names, or streaks.
2. **Consolidated Crypto Authority**: Key generation (CSPRNG), SV2 derivation, CMAC calculation, and truncation must reside in the crypto service.
3. **Internal WORM Storage**: Secrets must be write-once, read-many. Keys can never be overwritten with different values. Deletion is implemented via non-destructive soft-delete (tombstones) allowing full audit trails and an `undelete` recovery action.
4. **Domain Ownership in Game DB**: All coin names, metadata, and anti-replay counters belong exclusively to the flip game's `app.db`.

---

## 2. User Stories & Acceptance Criteria

### Story 1: Domain Decoupling & Game Data Cleansing (US-KEY-001)
*As a security engineer, I want the key service to manage only cryptographic credentials so that game business logic is completely isolated from security secrets.*
- **AC 1.1**: Remove `coin_name` from `TagSecret` dataclass and JSON serialization.
- **AC 1.2**: Remove `coin-name` annotations from Kubernetes Secret generator in `k3s_store.py`.
- **AC 1.3**: `POST /api/v1/keys` accepts only `uid`, `k3` (or `sdm_mac_key`), and optional `status`.
- **AC 1.4**: CSV importer ignores extraneous columns (coin name, outcome, master keys) and ingests only `(uid, k3)`.

### Story 2: Cryptographic Key Creation & Atomic Custody (US-KEY-002)
*As a hardware provisioner, I want to request a freshly generated AES-128 key from the key service for a tag UID so that keys are atomically stored in the WORM vault before being burned to physical silicon.*
- **AC 2.1**: Implement `generate_key()` in crypto engine producing a cryptographically secure 16-byte (32-hex) AES-128 key using CSPRNG (`secrets.token_hex(16)`).
- **AC 2.2**: Expose `POST /api/v1/keys/generate` taking `{"uid": "<14-hex>"}`.
- **AC 2.3**: If UID already exists, return `409 Conflict` (WORM enforcement).
- **AC 2.4**: Returns `201 Created` with `{"status": "created", "uid": "...", "k3": "<32-hex>"}` disclosing plaintext key *only once* at creation time.
- **AC 2.5**: Subsequent `GET /api/v1/keys/<uid>` continues to redact the secret.

### Story 3: Internal WORM Storage with Soft-Delete & Undelete (US-KEY-003)
*As a system administrator, I want WORM storage guarantees where secrets cannot be overwritten or permanently deleted, but support soft-deletion and undelete restoration.*
- **AC 3.1**: `save_key()` checks if a key already exists for the UID. If the existing `k3` differs from incoming `k3`, it is rejected with `409 Conflict`. If identical, it is idempotent.
- **AC 3.2**: `delete_key(uid)` performs a soft-delete: sets `status = "deleted"` and records `deleted_at` timestamp. It NEVER drops the Kubernetes Secret or dictionary entry.
- **AC 3.3**: Expose `POST /api/v1/keys/<uid>/undelete` restoring `status = "active"`.
- **AC 3.4**: `POST /api/v1/validate` and `GET /api/v1/validate` strictly verify `status == "active"`. Tags in `deleted` state are rejected with `403 Forbidden` / `404 Not Found`.
- **AC 3.5**: `GET /api/v1/keys` by default returns active UIDs; supports `?include_deleted=true` to view soft-deleted keys.

### Story 4: Game Database Schema & Validation Client Adapter (US-KEY-004)
*As a game developer, I want the flip game to store coin names in `app.db` and query the key service over HTTP for validation, so that the game server is completely decoupled from local key CSVs.*
- **AC 4.1**: Create `coins` table in `app.db`: `(uid TEXT PRIMARY KEY, coin_name TEXT, clan TEXT, rarity TEXT, created_at DATETIME)`.
- **AC 4.2**: Game server anti-replay logic continues to enforce strictly increasing counters in `scan_logs`.
- **AC 4.3**: Provide a clean HTTP client adapter function in the game server to query `tag_validator_service` `/api/v1/validate`.

---

## 3. Definition of Done (DoD)
- [ ] All 4 user stories implemented with 100% acceptance criteria satisfied.
- [ ] Zero `coin_name` references in `tag_validator_service`.
- [ ] Comprehensive automated tests for key generation, soft-delete, undelete, and WORM conflict rejection.
- [ ] All tests passing cleanly via `make test` / pytest.
- [ ] Code formatted and linted cleanly with Ruff.
- [ ] Decision §10 recorded in `DECISIONS.md`.
