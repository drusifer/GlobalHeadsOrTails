# Technical Architecture: Key Service Segmentation & Internal WORM Engine

## Architecture Metadata
- **Status**: Proposed (Pending Gate 2 Review)
- **Author**: Morpheus (Tech Lead)
- **Document**: `arch_key_segmentation.md`
- **Scope**: `tag_validator_service`, `data/app.db`, `ntag424_sdm_provisioner/server`

---

## 1. System Topology & Component Segmentation

```
                                 [NFC Hardware / Provisioner]
                                              │
                                              │ 1. POST /api/v1/keys/generate
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            tag_validator_service                            │
│                                                                             │
│  ┌───────────────────────┐              ┌────────────────────────────────┐  │
│  │   crypto/cmac_engine  │              │          store/                │  │
│  │  • CSPRNG key gen     │              │  • WORM enforcement            │  │
│  │  • SV2 construction   │              │  • Soft-delete / tombstoning   │  │
│  │  • CMAC AES-128       │              │  • Undelete recovery           │  │
│  │  • Odd-byte truncate  │              │  • K3sSecretStore              │  │
│  │  • Constant-time cmp  │              │  • MemorySecretStore           │  │
│  └───────────────────────┘              └────────────────────────────────┘  │
│                                                         │                   │
│                                ┌────────────────────────┴────────────────┐  │
│                                │   k3s Namespace: tag-secrets             │  │
│                                │   Secret: tag-key-<uid> (immutable)     │  │
│                                └─────────────────────────────────────────┘  │
└──────────────────────────────────────▲──────────────────────────────────────┘
                                       │
                                       │ 2. POST /api/v1/validate
                                       │    (Stateless Cryptographic Check)
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                               Flip Game Server                              │
│                                                                             │
│  ┌──────────────────────────┐             ┌──────────────────────────────┐  │
│  │      server/app.py       │             │         data/app.db          │  │
│  │  • Tap route handling    │             │  • coins table               │  │
│  │  • HTTP validation client│────────────▶│  • scan_logs table           │  │
│  │  • Anti-replay check     │             │  • coin_messages             │  │
│  │  • Outcome calculation   │             │  • sticker progress          │  │
│  └──────────────────────────┘             └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Cryptographic Engine Updates (`tag_validator.crypto`)

All crypto logic from `ntag424_sdm_provisioner` is strictly preserved and augmented:
- **`generate_sdm_key() -> str`**:
  Uses OS-level CSPRNG `secrets.token_hex(16).upper()` generating 128 bits of entropy (32 hex characters).
- **AN12196 CMAC Pipeline (Preserved Exact)**:
  1. `build_system_vector(uid, counter)`: `3CC300010080 || UID(7B) || CTR_LE(3B)` (16 bytes).
  2. `calculate_session_key(sv2, k3)`: `AES-128-CMAC(k3, sv2)` (16 bytes).
  3. `calculate_full_cmac(message, session_key)`: `AES-128-CMAC(session_key, UID&ctr=COUNTER&cmac=)` (16 bytes).
  4. `truncate_cmac(full_cmac)`: Indices `[1, 3, 5, 7, 9, 11, 13, 15]` (8 bytes / 16 hex chars).
  5. `verify_sdm_cmac(...)`: `hmac.compare_digest(calc_mac, received_cmac)`.

---

## 3. Data Model Refinement (`tag_validator.models`)

### Model: `TagSecret`
```python
@dataclass
class TagSecret:
    uid: str
    k3: str
    status: str = "active"          # "active" | "deleted"
    created_at: str = field(...)   # ISO 8601 UTC
    deleted_at: str | None = None  # ISO 8601 UTC or None
```
*Note: `coin_name` is completely deleted from the data model, serialization, and Kubernetes labels/annotations.*

---

## 4. Internal WORM Storage Layer (`tag_validator.store`)

### Protocol: `TagKeyStore`
```python
class TagKeyStore(Protocol):
    def get_key(self, uid: str, include_deleted: bool = False) -> TagSecret | None: ...
    def save_key(self, secret: TagSecret) -> bool: ...
    def delete_key(self, uid: str) -> bool: ...
    def undelete_key(self, uid: str) -> bool: ...
    def list_uids(self, include_deleted: bool = False) -> list[str]: ...
    def is_healthy(self) -> bool: ...
```

### WORM Rules:
1. **Immutability of Key Material**:
   - In `save_key(secret)`: If `uid` exists in store:
     - If existing `k3` != incoming `k3`: **Reject immediately with conflict** (cannot overwrite a burned key).
     - If existing `k3` == incoming `k3`: Update status/metadata (idempotent).
2. **Non-destructive Soft-Delete**:
   - In `delete_key(uid)`:
     - Does **NOT** delete the Kubernetes Secret or dictionary entry.
     - Sets `status = "deleted"` and `deleted_at = datetime.now(timezone.utc).isoformat()`.
     - Updates Kubernetes secret label `app.kubernetes.io/status: deleted` and annotation `app.kubernetes.io/deleted-at`.
3. **Undelete Recovery**:
   - In `undelete_key(uid)`:
     - Sets `status = "active"` and `deleted_at = None`.
     - Restores Kubernetes secret label `app.kubernetes.io/status: active`.

---

## 5. REST API Specifications (`tag_validator.api.app`)

| Method | Path | Request Body / Params | Status | Response | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/keys/generate` | `{"uid": "<14-hex>"}` | `201` | `{"status": "created", "uid": "...", "k3": "..."}` | Plaintext K3 disclosed ONLY here. Commits to WORM store. Returns `409` if UID exists. |
| `POST` | `/api/v1/keys` | `{"uid": "...", "k3": "..."}` | `201`/`200` | `{"status": "created", "secret": {...}}` | Rejects differing `k3` with `409 Conflict`. Redacts secret in response. |
| `GET` | `/api/v1/keys/<uid>` | None | `200` | `{"uid": "...", "k3": "...", "status": "active"}` | Redacted secret (`A1B2...C3D4`). Returns 404 if deleted unless admin. |
| `DELETE`| `/api/v1/keys/<uid>` | None | `200` | `{"status": "deleted", "uid": "..."}` | Soft-deletes secret. |
| `POST` | `/api/v1/keys/<uid>/undelete` | None | `200` | `{"status": "restored", "uid": "..."}` | Restores secret to active. |
| `GET` | `/api/v1/keys` | `?include_deleted=true` | `200` | `{"count": N, "uids": [...]}` | Filters active by default. |
| `POST` | `/api/v1/validate` | `{"uid": "...", "counter": N, "cmac": "..."}` | `200` | `{"valid": true/false, ...}` | Returns `403/404` if key is deleted or missing. |

---

## 6. Game Database Schema (`data/app.db`)

First-class table in SQLite `data/app.db`:
```sql
CREATE TABLE IF NOT EXISTS coins (
    uid TEXT PRIMARY KEY,
    coin_name TEXT NOT NULL,
    clan TEXT DEFAULT '',
    rarity TEXT DEFAULT 'common',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```
Game server validates taps:
1. Calls `POST http://<key-service>:8080/api/v1/validate`
2. If valid, verifies `counter > last_seen_counter` in `scan_logs` (anti-replay).
3. Looks up `coin_name` from `coins` table in `app.db`.
