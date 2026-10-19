# Sprint: Code Reorganization & Component Consistency — COMPLETE

Plan: `agents/cypher.docs/code_reorg_sprint.md`. Arch: `agents/morpheus.docs/arch_code_reorg.md`.

- [x] **Phase 1: Shared Models & Tag Validator Client SDK**
  - [x] Task 1.1: Create `shared/` package (`UID`, `Outcome`, `TagKeys`) with tests and `pyproject.toml`.
  - [x] Task 1.2: Add `TagValidatorClient` to `tag_validator_service/src/tag_validator/client.py` with tests.
- [x] **Phase 2: Extract `sdm_provisioner/` Component**
  - [x] Task 2.1: Create `sdm_provisioner/` package layout (`pyproject.toml`, `Makefile`, CLI entrypoints).
  - [x] Task 2.2: Move hardware commands, hal, tui, and interactive tools into `sdm_provisioner/`.
  - [x] Task 2.3: Update imports and verify `sdm_provisioner` test suite (104/104 passing).
- [x] **Phase 3: Extract `game_server/` Component**
  - [x] Task 3.1: Create `game_server/` package layout (`pyproject.toml`, `Makefile`).
  - [x] Task 3.2: Move Flask server, game_state_manager, services, static assets, and templates to `game_server/`.
  - [x] Task 3.3: Wire `game_server` to `ServiceKeyManager` + `tag_validator.client` and verify server tests (170/170 passing).
- [x] **Phase 4: Root Workspace Harmonization & Sprint Close**
  - [x] Task 4.1: Update root `Makefile` and `docs/SDLC.md`.
  - [x] Task 4.2: Clean up legacy directory and verify 100% test pass rate across all packages (305/305 passing).
  - [x] Task 4.3: Sprint close gates (Trin UAT, Tank SDLC, Oracle grooming, Smith acceptance, Cypher launch).

---

# Previous Sprint: Key Service Segmentation & Internal WORM Architecture — COMPLETE (commit a7a0935)

---

# Previous Sprint: Tag Keys K3s Secrets & Stateless CMAC Validator Service — COMPLETE (commit 17a3f73)

---

# Rangers historical sticker pack — BLOCKED, NOT RELEASED

**BLOCKED — not released.** Image generation returned `usage_limit_reached` (HTTP429). At the stop checkpoint, 478 of 1,162 masters existed and 684 player IDs remained missing. All four managed lanes stopped cleanly. Reset: **2026-10-08 22:44:02 America/New_York** (2026-10-09 02:44:02 UTC; epoch1791513842). Exact missing IDs and evidence: `agents/neo.docs/rangers_art_blocker.json`; ignored quota report: `build/rangers-art/quota-report.json`. Packing the 478 existing masters does not satisfy full-art completeness. Twelve Clans remains active.

Plan: agents/mouse.docs/rangers_sprint_log.md. Smith story/architecture gates approved; source1162IDs and first/lastseasons reconciled.

- [x] Phase 1: Full sourced catalog
- [x] Phase 2: Multi-pack service and weighted draws
- [x] Phase 3: Owned-only pack/search/player UI
- [x] Phase 4: Reusable art tooling and Smith sample gate
- [ ] Phase 5: All1162 portraits complete and validated
- [ ] Phase 6: Activation, full regression, docs and sprint close

---

# Sprint Log — 2026-10-07

## Entropy-weighted sticker awards — COMPLETE (workspace release)

Plan: `agents/cypher.docs/entropy_stickers_sprint.md`. Existing coin-owned collection, rarity and evolution retained. No commit/deploy requested in this sprint.

- [x] Cypher stories and Morpheus architecture; Smith Gate1+Gate2 approved.
- [x] Phase1 implementation (Neo): exact-count entropy/monobit weighting5%-50%; aggregate faceUIDs by coin_name; test/genuine atomic award snapshots; persisted replayodds.
- [x] Phase1 Trin/Morpheus gate: 126 server tests and syntax checks pass; Morpheus approves after explicit SQLite connection close fix.
- [x] Phase2 (Neo/Smith): real-flip guidance, current odds, warm-up and test labels, active docs, actual mobile browser approval. Extended browser verifies mature 50% with p=1 and genuine history remains at 100 after a test tap; existing album/drop/evolution/wager flows pass.
- [x] Oracle/Mouse: Decision7, feature guide, PRD16, changelog/index, validation evidence and retrospective recorded; Cypher workspace release approved. No commit, build, push or deployment performed.

---

## Previous sprint — 2026-10-06

## Collectables — The Twelve Clans — COMPLETE (local release)

Plan: `agents/cypher.docs/collectables_sprint.md`. Feature guide: `ntag424_sdm_provisioner/docs/COLLECTABLES.md`.

- [x] Cypher requirements and Smith faction design: 12 factions, 36 forms, original lore; story/architecture gates approved.
- [x] Neo persistence/drop/evolution and atomic optional wagers; Trin: 109 server tests passing.
- [x] Morpheus review: yield authorization race fixed and regression-tested.
- [x] Smith: real mobile browser album/drop/evolution/acceptance/locks/yield/decline/repeat-offer checks approved.
- [x] Oracle feature guide, PRD §16, decision §6 and index updated.
- [x] All 36 RTG-script-generated illustrations packed (2.1 MiB), decode/dimension verified and independently visually approved by Smith.
- [x] Final checks: 109 server tests, syntax/name/JavaScript checks, real mobile Chromium acceptance and git diff whitespace check pass. Test-only sample DB delta restored.
- [x] Retrospective recorded in agents/cypher.docs/collectables_retrospective.md; Cypher local release complete.

Deployment was not requested; this sprint delivers validated workspace changes.

---

## Previous sprint — 2026-04-22

## ✅ §14 Custom Coin Messages — COMPLETE
**Arch**: `agents/morpheus.docs/arch_custom_messages.md`
**PRD**: `agents/cypher.docs/custom_messages_prd.md`

All phases shipped and tested (60/60 server tests passing):
- `CoinMessageService` — SQLite-backed message store
- `POST /api/coin/messages` — CMAC-authenticated save with 24-char cap
- `/api/flip` — returns `heads_message` + `tails_message`
- Frontend — ✏️ edit form, hidden by default, expands on icon click
- Tests: `tests/test_server_coin_messages.py` (16 tests)

---

## ✅ SSE → Polling Refactor — COMPLETE
**Decision**: `ntag424_sdm_provisioner/DECISIONS.md` §5

Replaced Server-Sent Events with two-endpoint polling:
- `GET /api/flips/since?ts=<ISO>` — cheap check (`SELECT 1`, 3s poll)
- `GET /api/state?since=<ISO>` — full state snapshot (fetched only when `has_new=true`)
- Removed `gevent` from pyproject.toml server deps
- Removed `_sse_listeners`, `_push_sse`, `/api/stream/flips`, gevent monkey-patch
- Frontend: `EventSource` replaced with `setInterval` polling IIFE
- Tests: `tests/test_server_polling.py` (10 new tests)

---

## Previous Sprint
*Flip Off Challenge — 34 tests passing as of 2026-03-27*
