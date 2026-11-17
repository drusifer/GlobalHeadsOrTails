# Sprint Backlog: Reorganization Completion & Legacy Cleanup

**Sprint Name**: Reorganization Completion & Legacy Cleanup  
**Owner**: Cypher (Product Manager)  
**Date**: 2026-10-19  
**Status**: Stage 1 - Sprint Planning (Gate 1 Review)  

---

## 1. Objective & Vision

Complete the architectural decomposition initiated in previous sprints by:
1. Ensuring newly extracted components (`sdm_provisioner`, `game_server`, `shared`, `tag_validator_service`) have complete file and test parity with the original monolithic package.
2. Preserving all valuable assets (473 generated Rangers history portraits) and historical knowledge (`DECISIONS.md`, `LESSONS.md`, feature docs).
3. Establishing a centralized workspace Python virtual environment at the repository root (`.venv`).
4. Purging the obsolete `ntag424_sdm_provisioner/` directory once all tests and assets are validated.

---

## 2. User Stories & Acceptance Criteria

### US-REORG-005: Port Missing Tests & Provisioner Module Parity
**As a** hardware provisioner engineer,  
**I want** all 13 missing unit test suites, test helpers, and hardware acceptance tests ported into `sdm_provisioner/`,  
**So that** the extracted component maintains 100% test coverage and regression protection matching the original monolithic codebase.

#### Acceptance Criteria
- [ ] `key_manager.py` is present in `sdm_provisioner/src/sdm_provisioner/`.
- [ ] 13 missing test files (`test_an12343_getkeyversion.py`, `test_clock.py`, `test_compare_with_arduino.py`, `test_integration.py`, `test_key_manager.py`, `test_provision_sequence.py`, `test_session_with_arduino_keys.py`, `test_setup_url_simulation.py`, `test_trace_example.py`, `test_tui_flow.py`, `test_tui_read_tag.py`, `test_two_session_flow_logic.py`, `test_write_data_auth.py`) and supporting helpers (`trace_based_simulator.py`) ported to `sdm_provisioner/tests/`.
- [ ] Imports updated from `ntag424_sdm_provisioner` to `sdm_provisioner` and `shared`.
- [ ] Test assertions updated to match decoupled domain models.
- [ ] Hardware `acceptance_tests/` relocated to `sdm_provisioner/acceptance_tests/`.
- [ ] `pytest sdm_provisioner/tests/` passes with expanded test suite (~150+ tests).

---

### US-REORG-006: Asset Preservation & Rangers Portrait Migration
**As a** game server operator and player,  
**I want** all 473 previously generated Rangers history WebP portraits migrated into `game_server/`,  
**So that** existing sticker collection artwork is preserved and zero AI-generated assets are lost.

#### Acceptance Criteria
- [ ] All 473 WebP portraits migrated from `ntag424_sdm_provisioner/.../rangers-history/` into `game_server/src/game_server/static/stickers/rangers-history/`.
- [ ] Target directory contains all 479 total portraits (473 migrated + 6 existing).
- [ ] Portrait file integrity and dimensions verified.

---

### US-REORG-007: Documentation Consolidation at Repository Root
**As a** team member and protocol agent,  
**I want** project-wide architectural decisions, lessons, and feature guides consolidated at the repository root `docs/`,  
**So that** documentation is universally accessible without relying on legacy folder paths.

#### Acceptance Criteria
- [ ] `DECISIONS.md` (Decisions 1 through 11) moved to `docs/DECISIONS.md`.
- [ ] `LESSONS.md` moved to `docs/LESSONS.md`.
- [ ] Feature guides from `ntag424_sdm_provisioner/docs/` merged into root `docs/`.
- [ ] `agents/DOCUMENTATION_INDEX.md` and persona state files updated to reflect new documentation paths.

---

### US-REORG-008: Workspace Root Virtual Environment & Legacy Purge
**As a** DevOps engineer and developer,  
**I want** a unified virtual environment at workspace root (`.venv`) and complete deletion of `ntag424_sdm_provisioner/`,  
**So that** the project workspace is clean, modern, and has zero legacy debris.

#### Acceptance Criteria
- [ ] Python virtual environment created at root `.venv`.
- [ ] All workspace packages installed in editable mode (`pip install -e shared -e tag_validator_service -e sdm_provisioner -e game_server`).
- [ ] Dev and test dependencies installed (`pytest`, `pytest-cov`, `pytest-asyncio`, `ruff`, `pycryptodome`, `pyscard`, `textual`, `coolname`, `pillow`, `flask`, `requests`, `pyyaml`).
- [ ] `ntag424_sdm_provisioner/` directory completely removed.
- [ ] `docs/SDLC.md` and Makefiles updated to reference root `.venv`.
- [ ] `make test-all` passes 100% across all packages.

---

## 3. STORIES Rubric Self-Check
- **OUT (Outcome-Focused)**: Yes, defines concrete component completeness, asset preservation, and clean workspace state.
- **TEST (Testability)**: Every story has binary test criteria (e.g. 479 portraits, 0 legacy files, pytest passing).
- **CLAR (Clarity & Boundary)**: Distinct responsibilities across provisioner, server, docs, and environment.
- **VALUE (User Value)**: Fulfills user intent to complete reorg, maintain all tests, keep all valuable assets, and toss obsolete folder.
