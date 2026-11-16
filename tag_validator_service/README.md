# Tag Validator & K3s Secrets Microservice

Standalone microservice for managing NTAG 424 DNA tag keys as Kubernetes / k3s `Secret` objects and verifying SDM CMAC signatures statelessly.

---

## Features

- **Stateless Verification**: High-throughput CMAC calculation and constant-time signature validation per NXP AN12196.
- **k3s Secrets Backend**: Replaces plaintext local `tag_keys.csv` with cluster-managed, RBAC-protected Kubernetes Secrets (`tag-key-<uid>`).
- **Pluggable Store**: Run with native k3s backend (`SECRET_STORE_BACKEND=k3s`) or lightweight in-memory backend (`SECRET_STORE_BACKEND=memory`).
- **Zero-Dependency WSGI Server**: Pure Python standard library WSGI app, compatible with Gunicorn, uWSGI, or builtin `wsgiref`.
- **CSV Migration Tool**: CLI and API endpoint to import existing `tag_keys.csv` into k3s Secrets.
- **Health & Readiness**: Integrated `/healthz` and `/readyz` probes for Kubernetes pod lifecycle management.

---

## API Specification

### 1. Validate CMAC (POST)
`POST /api/v1/validate`

Request:
```json
{
  "uid": "043F13E2151990",
  "counter": 5,
  "cmac": "8841D6A4D9B0A352"
}
```

Response (200 OK):
```json
{
  "valid": true,
  "uid": "043F13E2151990",
  "counter": 5,
  "cmac_received": "8841D6A4D9B0A352",
  "cmac_calculated": "8841D6A4D9B0A352"
}
```

Response (404 Not Found):
```json
{
  "valid": false,
  "uid": "043F13E2151990",
  "counter": 5,
  "cmac_received": "8841D6A4D9B0A352",
  "error": "Tag key secret not found in k3s store"
}
```

### 2. Validate CMAC (GET)
`GET /api/v1/validate?uid=043F13E2151990&ctr=5&cmac=8841D6A4D9B0A352`

GET is stateless and never records anything.

### 2a. Validate and consume the counter (POST with `"consume": true`)
Opt-in, for callers that must accept each tap once (for example tto). Send `"consume": true` (a JSON boolean; any other value is ignored and the request behaves as in section 1). The CMAC is checked first; only if it is valid is the counter recorded, so a forged tap cannot burn a real one. A counter is accepted only if it is strictly greater than every counter previously consumed for that tag.

Fresh counter (200): the usual body plus `"consumed": true`.

Replay (200): `{"valid": false, "reason": "replayed", "consumed": false, "error": "Counter already used", ...}`.

Counter store failure (503): `{"valid": false, "error": "Counter store unavailable; nothing was recorded"}`. The counter is not recorded; retrying is safe.

A caller must treat a `valid: true` without `"consumed": true` as not consumed (an older validator ignores the flag). Counters are kept in a separate Secret per tag (`tag-counter` component, `tag-ctr-<uid>`), never in the key Secret, and updated with Kubernetes compare-and-set, so any number of replicas agree. The in-memory backend keeps them in process memory (lost on restart; for tests only).

### 3. Key Management & Internal WORM Engine
- `POST /api/v1/keys/generate`: Atomically generates a fresh CSPRNG AES-128 key and commits it directly to the WORM vault. Plaintext key is disclosed exactly once for burning to physical chip Key 3.
  ```json
  // Request
  { "uid": "043F13E2151990" }

  // Response (201 Created)
  {
    "status": "created",
    "uid": "043F13E2151990",
    "k3": "99E88808ADC7885BC7065D739A25E1D0",
    "message": "Key created and persisted to WORM vault. Burn this key to chip Key 3."
  }
  ```
- `POST /api/v1/keys`: Save a pre-existing tag key secret. Enforces WORM: attempting to overwrite a UID with a different key is rejected with `409 Conflict`.
  ```json
  {
    "uid": "043F13E2151990",
    "k3": "99E88808ADC7885BC7065D739A25E1D0"
  }
  ```
- `GET /api/v1/keys`: List all managed tag UIDs (active only by default; pass `?include_deleted=true` for all).
- `GET /api/v1/keys/<uid>`: Retrieve tag metadata (masked key `99E8...E1D0`).
- `DELETE /api/v1/keys/<uid>`: Soft-delete (tombstoning). Retains secret in vault for auditability, but disables validation.
- `POST /api/v1/keys/<uid>/undelete`: Restores a soft-deleted key back to `active` status.
- `POST /api/v1/keys/import-csv`: Bulk import tag keys from CSV payload (ingests `UID` and `SDM_MAC_KEY`).

---

## Running Locally

```bash
# Run tests
make test

# Start local service on port 8080
make run

# Import keys from tag_keys.csv
make seed-secrets CSV=../tag_keys.csv
```

---

## Kubernetes / k3s & `pi-patch` Deployment

```bash
# Build, verify container boot, and export image tarball for pi-patch
make export-image
# (or from workspace root: make export-tag-validator-image)
# Artifact produced: dist/tag-validator-service-latest.tar
# Local image tag:   localhost/tag-validator-service:latest

# Apply RBAC, Deployment, and Service directly
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```
