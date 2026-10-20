# Sprint: Reorganization Completion & Legacy Cleanup — COMPLETE

Plan: `agents/cypher.docs/reorg_cleanup_sprint.md`. Arch: `agents/morpheus.docs/arch_reorg_cleanup.md`.

- [x] **Phase 1: Component Parity & Test Porting**
  - [x] Task 1.1: Copy `key_manager.py` into `sdm_provisioner/src/sdm_provisioner/` and harmonize imports.
  - [x] Task 1.2: Port 13 missing unit test files and `trace_based_simulator.py` into `sdm_provisioner/tests/`.
  - [x] Task 1.3: Update ported test imports/assertions to match decoupled architecture and verify all pass (155/155 passing).
  - [x] Task 1.4: Move `acceptance_tests/` to `sdm_provisioner/acceptance_tests/`.
- [x] **Phase 2: Asset Migration**
  - [x] Task 2.1: Copy all 473 Rangers history WebP portraits into `game_server/src/game_server/static/stickers/rangers-history/`.
  - [x] Task 2.2: Verify full 479+ portrait count and file integrity in `game_server` (481 total portraits present).
- [x] **Phase 3: Documentation Consolidation**
  - [x] Task 3.1: Move `DECISIONS.md` to `docs/DECISIONS.md`.
  - [x] Task 3.2: Move `LESSONS.md` to `docs/LESSONS.md`.
  - [x] Task 3.3: Merge `ntag424_sdm_provisioner/docs/` into root `docs/` and update `agents/DOCUMENTATION_INDEX.md`.
- [x] **Phase 4: Root Virtual Environment Bootstrap & Legacy Purge**
  - [x] Task 4.1: Create fresh root `.venv` and install all workspace packages in editable mode.
  - [x] Task 4.2: Update root `Makefile` and `docs/SDLC.md` to point to root `.venv`.
  - [x] Task 4.3: Safely delete obsolete `ntag424_sdm_provisioner/` directory.
  - [x] Task 4.4: Run full workspace test suite `make test-all` and execute sprint close gates.

---

# Previous Sprint: Generic YAML-Driven Art Generator Refactor — COMPLETE

Plan: `agents/cypher.docs/art_generator_sprint.md`. Arch: `agents/morpheus.docs/arch_art_generator.md`.

- [x] **Phase 1: YAML Manifest Parsing & Prompt Templating Engine**
  - [x] Task 1.1: Implement YAML schema parser (`ManifestParser`, `ArtworkSetMeta`, `ArtItem`) with strict validation.
  - [x] Task 1.2: Implement `PromptTemplateEngine` with safe metadata and set token interpolation.
- [x] **Phase 2: Pluggable Generator Backend & WebP Image Processor**
  - [x] Task 2.1: Implement `ArtBackend` interface with `MockBackend` (for deterministic offline testing) and `CLICommandBackend`.
  - [x] Task 2.2: Implement `ImageProcessor` (auto-crop, Lanczos scaling, WebP Q92 encoding).
- [x] **Phase 3: Set-Specific Storage & Clean Review Contact Sheet**
  - [x] Task 3.1: Enforce set-specific subdirectories (`<output_dir>/<id>.webp`) and resumable status tracker.
  - [x] Task 3.2: Implement `ContactSheetBuilder` generating clean, responsive HTML review sheet (`contact_sheet.html`) with zero card flair.
- [x] **Phase 4: CLI Orchestration, Unit Tests & Makefile Targets**
  - [x] Task 4.1: Build executable CLI `tools/art_generator.py` with `--manifest`, `--status`, `--generate`, `--force`, `--item`, `--review`, `--export-prompts`.
  - [x] Task 4.2: Create comprehensive pytest suite `tools/tests/test_art_generator.py` (10/10 tests passing).
  - [x] Task 4.3: Add Makefile targets (`test-art-generator`, `art-status`, `art-generate`, `art-review`) and run full regression suite (315/315 passing).
  - [x] Task 4.4: Sprint close gates (Trin UAT, Tank SDLC, Oracle grooming, Smith acceptance, Cypher launch).
- [x] **Phase 5: Sticker Catalog Pack Structure & Data Decoupling**
  - [x] Task 5.1: Relocate manifests to `game_server/src/game_server/sticker_catalog/<set-id>/`.
  - [x] Task 5.2: Separate raw card records into `cards.json` and single item template in `manifest.yaml`.
  - [x] Task 5.3: Update `tools/art_generator.py` to auto-load `data_file` and apply `item_template` (11/11 tests passing).
- [x] **Phase 6: Legacy Sticker Art Cleanup & Doc Grooming**
  - [x] Task 6.1: Purge legacy scripts (`sticker_art.mjs`, `sticker_production.py`, `sticker_references.py`, `crop_stickers.py`, etc.).
  - [x] Task 6.2: Purge old review grids (`build/sticker-art/`, `build/rangers-art/`).
  - [x] Task 6.3: Clean `Makefile.prj` legacy targets and update `RANGERS_STICKER_TARGETS.md`.
  - [x] Task 6.4: Oracle documentation grooming and decision log update (Decision 11).

---

# Previous Sprint: Code Reorganization & Component Consistency — COMPLETE

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
