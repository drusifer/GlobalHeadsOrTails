# Sprint 1 User Stories: Key Custody — keys never leave the key store

*   **Total Points**: 31 (Tier 2)
*   **Branch**: `main` in the new repo (the split happens first; SDLC §3 allows `main` or a feature branch)
*   **Source**: Owner, 2026-11-17, `docs/PROPOSAL_KEY_CUSTODY.md` (parts 1-3), the scoping answers given at sprint kickoff, and the owner's request to move the validator and provisioner to their own repo
*   **Status**: Draft — awaiting Smith Gate 1

## Goal

When this sprint is done, the validator, provisioner and key package live in their own repo, and a validator can run in a mode where no HTTP route returns, writes or generates tag keys, and the provisioner puts the keys it writes onto a tag into the same key store the validator reads from — without sending them over HTTP. The key model and key stores live in one shared package that is published to the owner's PyPI with CSV as the default store and the k3s store included as an option. This lets tap-to-open (tto) run its validator sidecar with no key-returning endpoints (closing its SEC-002), and makes the provisioner and validator one product with one version.

## Assumptions made for the owner

1. The owner said the provisioner's resume behaviour "depends on the key store implementation". Assumed: the provisioner reads keys back through the same store interface it writes to, so resume works wherever that store can be read (CSV file: yes; k3s: with a credential that can read the Secrets). No separate local record.
2. "Publish on my PyPI" is taken to mean the pi-patch Forgejo PyPI registry (`forgejo-publish.sh pypi`). Publishing itself is not part of this sprint's acceptance; the package must build and be publishable.
3. Validate-only mode is selected by `TAG_VALIDATOR_MODE=validate`; the default stays as today. The game's own validator stays on the default mode (owner's choice).
4. The new repo is `git@github.com:drusifer/ntag-tools.git` (cloned at `~/Projects/ntag-tools`, contains only the LICENSE). History is not kept: files are copied in with one initial commit.
5. Part 4 of the proposal (removing `?raw=true`) is backlog, not this sprint.
7. Coins are a game concept and tags are tag-tool concepts (owner's decision). A coin has two tags, a heads tag and a tails tag, and the two are not interchangeable. The tag tools (validator, provisioner, key package) know nothing about coins, coin names or sides; the game keeps its own coin registry that maps each coin to its heads tag UID and its tails tag UID (STORY-KC-5).
6. The existing `shared/` package moves to `ntag-tools` (owner's choice) without `Outcome` (heads/tails), which stays in the game (owner's choice). `UID`, `TagKeys` and `mask_key` move; `TagKeys` loses its `outcome` field. `game_server` already has its own `Outcome` and `TagKeys` in `csv_key_manager.py`, so it keeps those and consumes only `UID` and `mask_key` from the registry. KC-2's key-store package is added alongside it, not merged into it.

---

## STORY-KC-0: Validator and provisioner live in their own repo
**Points:** 5 · **Phase 0**, done before KC-1 to KC-4

**As the** owner,
**I want** `tag_validator_service`, `sdm_provisioner` and `shared` (without `Outcome`) in a repo of their own,
**so that** they are built, tested and released as one product, apart from the game.

### Acceptance Criteria
1. The new repo contains `tag_validator_service`, `sdm_provisioner`, `shared` (`UID`, `TagKeys`, `mask_key`; `Outcome` and `TagKeys.outcome` removed), their tests, `docs/PROPOSAL_KEY_CUSTODY.md`, and a Makefile and `docs/SDLC.md` that work there; `make test-all` passes from a fresh clone.
2. The validator image still builds, boot-checks and exports from the new repo, and publishes to the pi-patch Forgejo with the same image name.
3. `game_server` stays in this repo and builds and passes its tests using the `tag-validator-service` and `shared` packages from the registry (or a pinned wheel), not sibling directories; its Dockerfile and `make export-game-server-image` still work.
4. Nothing in either repo refers to a path that now lives in the other; the moved directories are removed from this repo in a separate commit after the new repo passes.
5. `Outcome`, coin names and sides are not in `ntag-tools`: `game_server` keeps its own `Outcome`, and nothing in the new repo imports, defines or stores them, including the provisioner's re-export and its copy in `csv_key_manager.py`.
6. If any file the moved code needs is missing in the new repo, the move stops and names it rather than leaving a half-working repo.

---

## STORY-KC-1: Validator runs in validate-only mode
**Points:** 5

**As a** tto operator running the validator as a sidecar,
**I want** a mode in which the validator exposes no route that reads, writes or generates keys,
**so that** anyone who can reach its port cannot obtain tag keys.

### Acceptance Criteria
1. With `TAG_VALIDATOR_MODE=validate`, `/healthz`, `/readyz` and `/api/v1/validate` (GET and POST, including `consume:true`) behave exactly as they do today.
2. In that mode every key route answers 404 with no key material in the body: `GET /api/v1/keys`, `GET /api/v1/keys/<uid>` (with and without `raw=true`), `POST /api/v1/keys`, `POST /api/v1/keys/generate`, `POST /keys/import-csv`, `DELETE` and `undelete`.
3. `/healthz` lists `"validate-only"` in `features` in that mode, and still lists `consume`.
4. With the variable unset, or set to the default value, all existing validator tests pass unchanged.
5. An unrecognised value of `TAG_VALIDATOR_MODE` makes the service refuse to start with a message naming the variable and the allowed values, rather than silently running in the default mode.

## STORY-KC-2: One shared package for the key model and key stores
**Points:** 8

**As the** owner maintaining the provisioner, validator and game server,
**I want** the tag key model and the key stores (CSV and k3s) in one shared package,
**so that** the Secret layout and CSV format are defined in one place and every deployable agrees on them.

### Acceptance Criteria
1. A new shared package contains `TagSecret`, key-hex validation, the store interface, the CSV store, the memory store and the k3s store; `tag_validator_service`, `sdm_provisioner` and `game_server` import them from it.
2. Existing tests in all three packages pass with no behaviour change, and `tag_validator`'s old import paths still work (or fail with a clear message) so nothing outside the repo breaks silently.
3. A plain install of the package gives the CSV store as the default store with no Kubernetes dependency; the k3s store is available through an extra (for example `pip install pkg[k3s]`) and importing it without the extra gives a message naming the extra.
4. The package builds a wheel and sdist with `make`, and a clean virtualenv can install and import it.
5. The package carries its own version, which the validator and provisioner declare as a dependency.

## STORY-KC-3: Provisioner stores a tag's keys in the key store
**Points:** 5

**As the** owner provisioning a tag,
**I want** the provisioner to save the tag's new keys into the key store the validator reads (CSV by default, k3s when configured),
**so that** keys never travel over HTTP and the validator can verify the tag's taps immediately.

### Acceptance Criteria
1. The provisioner generates its own keys and saves them through the shared store interface after writing a tag; it no longer calls `?raw=true` or `generate`.
2. The store is chosen by configuration: CSV file path by default; k3s with a namespace setting (for example `tto-tags`) when selected.
3. If saving fails (file not writable, missing k3s credential, namespace absent), the provisioner stops and reports which store and location failed before the tag is left in an unrecoverable state.
4. If provisioning is interrupted partway, running it again for the same tag recovers its keys from the store and finishes (CSV store; and k3s store given a credential that may read the Secrets).
5. Saved keys are never printed to logs or the terminal.
6. The provisioner and the key store record only tag data (UID, keys, status, timestamps, notes). No coin name, side or `outcome` is written to or read from the key store, and the provisioner's coin-assignment steps are removed from it.

## STORY-KC-4: Provisioned tags are proven end to end
**Points:** 3 · **Owner:** Trin

**As the** owner releasing the product,
**I want** one automated test that provisions a simulated tag, publishes its keys, and validates its taps,
**so that** a change to either side that breaks the other fails before release.

### Acceptance Criteria
1. The test provisions a simulated tag, then validates a genuine tap and sees it accepted.
2. The same test shows a replayed counter is rejected when consumption is on, and a tap with a forged CMAC is rejected.
3. The test runs with the CSV store with no cluster, and with the validator in validate-only mode.
4. `make test-all` includes it, and it fails if the provisioner and validator disagree on the key layout.

---

## STORY-KC-5: The game names coins separately from tags
**Points:** 5 · **Owner:** Neo (in this repo, `game_server`)

**As the** owner running the coin game,
**I want** the game to keep its own record of which two tags make up each coin,
**so that** coin names and heads/tails sides live in the game and the tag tools stay about tags only.

### Acceptance Criteria
1. The game has a coin registry that maps each coin name to exactly one heads tag UID and exactly one tails tag UID; the two are distinct tags and are never treated as interchangeable.
2. Existing coin names and sides in the game's current key CSV are carried into the registry without loss, and a tap on an already-provisioned coin gives the same heads or tails result as before.
3. Assigning a tag to a coin that already has a tag on that side is refused with a message naming the coin, the side and the existing UID; a tag cannot be on two coins or on both sides of one coin.
4. A tag that is not in the registry is reported as unassigned, not as heads or tails.
5. The game keeps working against the validator with keys held only in the key store; it needs no coin or side data from it.

---

## Out of Scope
- Removing `?raw=true` and key-returning responses from `generate` (proposal part 4), and the matching changes to `service_key_manager` and `scripts/update_keys_to_active.py`.
- Redesigning how coins are drawn or sold; only the coin-to-tag mapping is in scope.
- Putting the game's own validator into validate-only mode.
- Copying already-provisioned tags' keys to `tto-tags` (one-off migration).
- Pruning `tag-ctr-<uid>` counter Secrets.
- Remote crypto / token-on-routes alternatives (rejected in the proposal).
- Keeping git history for the moved code (fresh start chosen).
- Actually publishing to PyPI; only that the package is buildable and publishable.

## Open Questions
1. Should the validator pin its published image to the shared package version, or keep its own image tag scheme? Assumed: keep the current scheme (tto pins by digest).
2. Pruning counter Secrets when a tag is deleted: backlog item; assumed not needed this sprint.

---

# Sprint 1 Architecture (Morpheus)

*   **Status**: Approved by Smith Gate 2 (see CHAT.md)
*   **Scope**: Sprint 1 Architecture — key custody, `ntag-tools` repo

## 1. Overview

Tag keys are written by the provisioner straight into a key store and read by the validator from the same store; no HTTP route has to return key material. Everything about tags lives in a new repo `ntag-tools`; everything about coins lives in this repo (`game_server`).

## 2. Boundaries

```
ntag-tools (git@github.com:drusifer/ntag-tools.git)         GlobalHeadsOrTails (this repo)
  shared/            UID, TagKeys (no outcome), mask_key       game_server/   coins (heads uid + tails uid),
  ntag_keys/         TagSecret, TagKeyStore (ABC),                            Outcome, flip game
                     MemorySecretStore, CsvSecretStore (default),   depends on wheels: shared,
                     K3sSecretStore (extra "k3s")                             tag-validator-service
  tag_validator_service/  CMAC engine + HTTP API, uses ntag_keys
  sdm_provisioner/   NFC + TUI; StoreKeyManager over ntag_keys
  tests/e2e/         provision -> publish -> validate
```

Trust: the provisioner (admin machine, NFC reader) writes keys; the validator (in cluster) reads them. A k3s credential for the validator can be read-only, and the provisioner's read-write. Validate-only mode additionally removes every key route from the validator's HTTP surface.

## 3. Components and decisions

1. **`ntag_keys` package.** `TagSecret`, `KeyConflictError`, `CounterStoreError`, `TagKeyStore` (the existing ABC incl. `consume_counter`), `MemorySecretStore`, new `CsvSecretStore`, and `K3sSecretStore` (imports `kubernetes` lazily; without the `k3s` extra, selecting it raises an error naming the extra). `create_secret_store(backend, ...)` defaults to `csv`. No dependencies in the base install.
2. **`CsvSecretStore`.** One file `tag_keys.csv` with columns `uid,k0,k1,k3,status,created_at,deleted_at`; same WORM and soft-delete semantics as the memory store; atomic write via temp file and rename; per-process lock; counters in a sibling `tag_counters.csv`. It has no coin, side or outcome column. The game's own CSV is not touched.
3. **`tag_validator`** keeps `tag_validator.models` and `tag_validator.store` as thin re-exports of `ntag_keys`, so existing imports keep working. Config default for `SECRET_STORE_BACKEND` stays `memory` for the service (the container sets `k3s`); `csv` is added as a choice.
4. **Validate-only mode.** `TAG_VALIDATOR_MODE` in `{full (default), validate}`. In `validate`, key routes are not registered (404). Anything else fails at start with a message. `/healthz` `features` adds `validate-only`.
5. **Provisioner.** New `StoreKeyManager(store)` replaces `ServiceKeyManager`; generates keys with `secrets.token_bytes(16)`; saves via the store; resume reads back via the same store. The coin store, coin methods, `CoinNamingScreen` and coin parameters are removed. `CsvKeyManager` (legacy, with coin columns) is removed. Store selection by `NTAG_KEY_STORE` (`csv` default, `k3s`), `NTAG_KEY_CSV` path, `NTAG_K3S_NAMESPACE`.
6. **`shared`** keeps `UID`, `TagKeys` (without `outcome`, `coin_name`) and `mask_key`; `Outcome` is removed. The provisioner/ validator no longer import it.
7. **Game.** `game_server` keeps its own `Outcome`, `TagKeys` copy and `coins` table; it consumes `shared` and `tag-validator-service` as wheels built by `ntag-tools` (`make dist`), found through `NTAG_TOOLS_DIST` (default `../ntag-tools/dist`) or an index URL. KC-5 closes the gaps in the existing coin admin (heads/tails distinctness, one tag per coin side, unassigned reporting) and removes its use of key-store coin data.
8. **One version.** A single `VERSION` file in `ntag-tools`; `make check-versions` fails if any `pyproject.toml` disagrees; one `CHANGELOG.md`. Validator keeps publishing its own image.

## 4. Failure modes

Store not writable/missing credential → provisioner stops before touching the tag and names the store and path. Corrupt CSV row → store raises a clear error naming the line, never silently skips. k3s extra missing → error naming the extra.

## 5. Build-environment note (for Mouse)

New repo needs its own Makefile, venv, `docs/SDLC.md` (Tank, Phase 0). No new third-party dependency mechanism; `kubernetes` becomes an extra.
