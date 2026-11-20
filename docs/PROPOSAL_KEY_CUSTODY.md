# Proposal: keys never leave the validator's store (and provisioner + validator as one product)

Status: **all four parts implemented: parts 1-3 in Sprint 1 (2026-11-17), part 4 (remove `?raw=true` and `generate`) in Sprint 2 (2026-11-20, ntag-tools 0.4.0, decision 16).** Written 2026-11-17 from a session in the `tto` repo (tap-to-open), to be picked up in a separate session here. If accepted, it becomes ADR 15 and amends ADR 13.

## Why this came up

`tto` (a web app that opens gated content when an NFC tag is tapped) runs the `tag_validator_service` as a loopback sidecar in its pod. A security review (finding SEC-002 in the tto repo) found that the validator's HTTP API hands out tag secrets to anyone who can reach it, with no authentication:

| Route | What leaves | Callers |
|---|---|---|
| `GET /api/v1/keys/<uid>?raw=true` | K0, K1, K3 for one tag | `sdm_provisioner/service_key_manager.py` (lines ~196, 231, 323) |
| `GET /api/v1/keys?raw=true` | K0, K1, K3 for every tag | `service_key_manager.py` (~411), `scripts/update_keys_to_active.py` |
| `POST /api/v1/keys/generate` | the new K0, K1, K3 in the response | `sdm_provisioner`, `game_server/service_key_manager.py:208` |

These routes exist on purpose (ADR 13, decision 2: raw retrieval "for authorized hardware provisioners"), but nothing authorizes the caller. The validator only needs a key to compute a CMAC; it never needs to return one. The provisioner needs keys because it does the NTAG 424 crypto locally when it writes a tag.

The tto owner accepted the risk for now (an attacker who reaches the loopback port reads every key) and asked for the validator to have no key-returning endpoints at all.

## Goals

1. No HTTP route of the validator returns key material, in the mode tto uses.
2. The provisioner keeps its APDU and crypto code as is (no remote-crypto redesign).
3. The provisioner and validator are developed, tested and released as one product, but remain two deployables.

## Proposal

### 1. Validate-only mode (small, do first)

A setting, `TAG_VALIDATOR_MODE=validate` (default unchanged), that turns off every route that reads, writes or generates keys. Only `/healthz`, `/readyz` and `/api/v1/validate` (GET and POST, including `consume`) remain; everything else answers 404.

- Reproduction test: in validate mode, request each route in the table above plus `POST /api/v1/keys`, `/keys/import-csv`, `DELETE`, `undelete`; expect 404 and no key material in any body. In default mode all existing tests still pass.
- tto's sidecar runs in this mode. `/healthz` still lists `features` including `consume`; consider adding `"validate-only"` to `features` so a caller can see the mode.

### 2. Provisioner pushes keys into the k3s Secrets (small)

After the provisioner writes a tag, it stores that tag's keys in the validator's k3s Secret store, using the same code the validator reads with (`K3sSecretStore.save_key`), not an HTTP call and not a second copy of the Secret layout.

- Needs a configurable target namespace (tto reads `tto-tags`; the game's validator reads its own) and a Kubernetes credential allowed to create and update Secrets there.
- The provisioner stops calling `?raw=true` and `generate`. It generates keys itself (CSPRNG, as `generate_sdm_key` does today) and keeps what it needs to resume a half-written tag: either its own local record, or a credential that may also read the Secrets. Decide which. The provisioner machine is an admin machine, so reading Secrets with its own credential is acceptable.
- One-off: tags already provisioned in the game's namespace need their keys copied to `tto-tags` if any should open tto gates.

### 3. One product, two deployables (structure)

Provisioner and validator are already in this repo. Make the coupling deliberate:

- **Shared package** for the key model and the k3s store (`TagSecret`, `K3sSecretStore`, key hex validation), imported by `tag_validator_service`, `sdm_provisioner` and `game_server`. The Secret layout then lives in one place. Keep it additive and versioned. If extraction is too much at first, import it from `tag_validator` and extract later.
- **Joint end-to-end test** in this repo: provision a simulated tag, publish its keys, then validate its taps (including replay and forged CMAC).
- **One version and changelog** for the provisioner and validator; the validator still publishes its own image, which tto pins by digest, so tto's release does not wait on provisioner changes.
- **Not merged at runtime.** The provisioner runs on an admin machine with an NFC reader and holds keys; the validator runs in the cluster and only checks taps. Keeping them separate lets the validator's credential be read-only and the provisioner's write-only on tag Secrets. Putting key-writing code in the validator's process would remove that.

### 4. Remove the key egress (after 1 to 3 are in use)

Delete `?raw=true` and return only the UID and status from `generate` (or retire `generate` in favour of provisioner-side generation). Update `service_key_manager` in `sdm_provisioner` and `game_server` and `scripts/update_keys_to_active.py`. `GET /keys` then returns metadata only (status, timestamps).

## Rejected alternatives

- **Token on the three routes.** Smallest change, but keys still leave on request for anyone holding the token. Fails goal 1.
- **Remote crypto service** (provisioner relays APDUs; validator builds the MACs, encrypts `ChangeKey` payloads and keeps the session keys). Meets "no keys leave", but rewrites the provisioner's APDU layer, needs the validator reachable for every command of a tag session, and adds session state and an authenticated oracle to the validator. Owner chose not to change that much.

## Things to decide when picking this up

- Provisioner resume: local record or read credential on the Secrets?
- Shared package: extract now, or import from `tag_validator` first?
- Does the game's validator also go validate-only once its provisioning path uses Secrets, or does it keep the default mode?
- Counter Secrets: the validator writes one `tag-ctr-<uid>` Secret per tapped tag (tto's backlog has "prune old counter Secrets"); decide whether pruning belongs with key deletion in the provisioner.

## What tto needs from this

Only that, in validate mode, `/healthz` still advertises `consume`, `/api/v1/validate` behaves exactly as `tto/docs/VALIDATOR_CONTRACT.md` describes, and keys can reach `tto-tags` as Secrets by some route other than HTTP. tto's deployment hand-off (`docs/PIPATCH_HANDOFF.md` in the tto repo) will then say "keys arrive from the provisioner as Secrets; no `import-csv`", and SEC-002 can be closed.
