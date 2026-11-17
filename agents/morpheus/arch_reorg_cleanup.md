# Technical Architecture: Reorganization Completion & Legacy Cleanup

**Architect**: Morpheus (Tech Lead)  
**Date**: 2026-10-19  
**Status**: Stage 1 - Sprint Planning (Gate 2 Review)  

---

## 1. Architectural Scope & Invariants

This sprint completes the physical separation and cleanup of the workspace following the 4-peer component architecture established in Decision 9:

```
GlobalHeadsOrTails/
├── .venv/                      # Unified workspace virtual environment
├── docs/                       # Project-wide documentation & decisions
│   ├── DECISIONS.md
│   ├── LESSONS.md
│   ├── SDLC.md
│   └── ... (migrated feature docs)
├── shared/                     # Domain contracts (UID, Outcome, TagKeys)
├── tag_validator_service/      # CMAC validation & K3s secrets vault
├── sdm_provisioner/            # Smartcard APDU engine, TUI & HAL
│   ├── src/sdm_provisioner/
│   │   └── key_manager.py     # Ported key manager implementation
│   ├── tests/                 # Ported test suite (150+ tests)
│   └── acceptance_tests/      # Hardware APDU acceptance tests
├── game_server/                # Flask gameplay server & sticker book
│   └── src/game_server/static/stickers/rangers-history/  # 479 portraits
└── tools/                      # CLI tools & generic art generator
```

---

## 2. Component Migration Plan

### 2.1 Provisioner Parity (`sdm_provisioner/`)
1. **Source parity**:
   - Copy `key_manager.py` from `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/` to `sdm_provisioner/src/sdm_provisioner/key_manager.py`.
   - Update imports in `key_manager.py` to point to `shared` and `sdm_provisioner`.
2. **Test parity**:
   - Port 13 test suites and helpers into `sdm_provisioner/tests/`:
     - `test_an12343_getkeyversion.py`
     - `test_clock.py`
     - `test_compare_with_arduino.py`
     - `test_integration.py` (update assertions to match decoupled domain models where `coin_name` is in `game_server`)
     - `test_key_manager.py`
     - `test_provision_sequence.py`
     - `test_session_with_arduino_keys.py`
     - `test_setup_url_simulation.py`
     - `test_trace_example.py`
     - `test_tui_flow.py`
     - `test_tui_read_tag.py` (adjust pilot click / headless bounds or skip on headless environments)
     - `test_two_session_flow_logic.py`
     - `test_write_data_auth.py`
     - `trace_based_simulator.py`
3. **Hardware acceptance tests**:
   - Move `ntag424_sdm_provisioner/acceptance_tests/` to `sdm_provisioner/acceptance_tests/`.

### 2.2 Asset Migration (`game_server/`)
- Copy all 473 Rangers history WebP portraits from `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/static/stickers/rangers-history/` into `game_server/src/game_server/static/stickers/rangers-history/`.
- Validate that destination contains 479 WebP images matching the catalog manifest.

### 2.3 Documentation Migration (`docs/`)
- Relocate `ntag424_sdm_provisioner/DECISIONS.md` to `docs/DECISIONS.md`.
- Relocate `ntag424_sdm_provisioner/LESSONS.md` to `docs/LESSONS.md`.
- Merge `ntag424_sdm_provisioner/docs/` markdown files into root `docs/`.
- Update `agents/DOCUMENTATION_INDEX.md` and any outdated links.

### 2.4 Environment & Deletion
- Initialize new root `.venv`:
  `python -m venv .venv`
- Install workspace packages in editable mode:
  `.venv/Scripts/pip install -e shared -e tag_validator_service -e sdm_provisioner -e game_server`
- Install test & development dependencies.
- Verify full test regression suite: `make test-all`.
- Delete `ntag424_sdm_provisioner/`.

---

## 3. ARCH Rubric Self-Check
- **Purity / Coupling**: Zero back-references to old folder. All services are self-contained peer packages.
- **Data Integrity**: All 479 portrait assets, 11 architectural decisions, and all hardware tests preserved.
- **Reproducibility**: Clear root `.venv` and single `make install-all` command.
