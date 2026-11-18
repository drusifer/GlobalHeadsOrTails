# Sprint 1 Task Board: Key Custody — keys never leave the key store

*   **Goal**: Move the tag tools to `ntag-tools`, add validate-only mode and a shared key-store package (CSV default, k3s extra), have the provisioner store keys directly, and keep coins in the game.
*   **Tier**: Tier 2
*   **Total Points**: 31
*   **Branch**: `main` (both repos)
*   **Status**: Approved plan — executing

Stories and architecture: `docs/sprints/USER_STORIES_SPRINT1.md`.

---

## Stage 0: SDLC Gate
- [x] **Task 0.1:** `docs/SDLC.md` exists. (*Owner: Mouse | Verification: `test -f docs/SDLC.md`*)

## Phase 0: New repo and build environment (KC-0 part 1; Owner: Tank)
- [ ] **Task 0.2:** Copy `tag_validator_service`, `sdm_provisioner`, `shared`, the proposal doc into `~/Projects/ntag-tools`; add Makefile, `.gitignore`, `VERSION`, `CHANGELOG.md`, `docs/SDLC.md`. (*Verification: `make -C ~/Projects/ntag-tools test-all` passes*)

## Phase 1: Key package (KC-2; Owner: Neo)
- [ ] **Task 1.1:** Create `ntag_keys` with models, ABC, memory/CSV/k3s stores, factory; tests first. (*Verification: `make test-ntag-keys`*)
- [ ] **Task 1.2:** Re-point `tag_validator` at `ntag_keys` via shims; wheels build. (*Verification: `make test-tag-validator && make dist`*)
- [ ] **Task 1.3:** UAT + review.

## Phase 2: Validate-only mode (KC-1; Owner: Neo)
- [ ] **Task 2.1:** `TAG_VALIDATOR_MODE`, 404 routes, healthz feature, bad-value startup error; reproduction tests. (*Verification: `make test-tag-validator`*)
- [ ] **Task 2.2:** UAT + review.

## Phase 3: Provisioner stores keys; tags only (KC-3 + KC-0 part 2; Owner: Neo)
- [ ] **Task 3.1:** `StoreKeyManager`, remove coin code and `Outcome` from provisioner and `shared`. (*Verification: `make test-sdm-provisioner`*)
- [ ] **Task 3.2:** Wire TUI/runner config; no key logging. (*Verification: `make test-sdm-provisioner`*)
- [ ] **Task 3.3:** UAT + review.

## Phase 4: End-to-end test (KC-4; Owner: Trin)
- [ ] **Task 4.1:** `tests/e2e` provision → publish → validate (genuine, replay, forged), CSV + validate-only. (*Verification: `make test-all`*)

## Phase 5: Game consumes packages; coin rules (KC-0 part 3 + KC-5; Owner: Neo)
- [ ] **Task 5.1:** Game consumes `shared`/`tag-validator-service` wheels; Dockerfile and Make targets updated. (*Verification: `make test-game-server && make export-game-server-image`*)
- [ ] **Task 5.2:** Coin rules and decoupling from key-store coin data. (*Verification: `make test-game-server`*)
- [ ] **Task 5.3:** Remove moved directories from this repo in a separate commit. (*Verification: `make test-all`*)

## Close
- [ ] Tank `*devops sdlc-check`; Oracle groom; Smith acceptance; retro; Cypher launch.
