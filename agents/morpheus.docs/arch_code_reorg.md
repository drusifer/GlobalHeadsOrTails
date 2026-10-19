# Technical Architecture: Repository Modularization & Component Consistency

**Author**: Morpheus (Tech Lead)  
**Date**: 2026-10-18  
**Status**: DRAFT (Pending Gate 2 Review)

---

## 1. Architectural Blueprint

The repository is restructured into 4 decoupled, peer packages under the root workspace:

```
GlobalHeadsOrTails/
├── shared/                  # Common domain contracts (UID, Outcome, TagKeys)
├── tag_validator_service/   # Security appliance: k3s WORM vault + client SDK (tag_validator.client)
├── sdm_provisioner/         # Hardware provisioner: APDUs, PCSC HAL, TUI, tool runner
└── game_server/             # Web application: Flask, game engine, stickers, VIP, app.db
```

### Dependency Graph

```
                  ┌────────────────────────┐
                  │        shared/         │
                  │ (UID, Outcome, TagKeys)│
                  └───────────▲────────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
   ┌───────────┴───────────┐     ┌───────────┴───────────┐
   │    sdm_provisioner/   │     │      game_server/     │
   │  (PCSC, APDU, TUI)    │     │(Flask, app.db, engine)│
   └───────────┬───────────┘     └───────────┬───────────┘
               │                             │
               │         (HTTP REST)         │
               └──────────────┬──────────────┘
                              ▼
               ┌─────────────────────────────┐
               │   tag_validator_service/    │
               │  + tag_validator.client     │
               └─────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 `shared/`
- **Location**: `shared/src/shared/`
- **Responsibilities**:
  - `uid.py`: `UID` representation (14 hex chars, normalization, asset tag derivation).
  - `outcome.py`: `Outcome` enum (`HEADS`, `TAILS`, `INVALID`).
  - `models.py`: `TagKeys` dataclass.
- **Dependencies**: Standard library only (no external dependencies).

### 2.2 `tag_validator_service/`
- **Location**: `tag_validator_service/src/tag_validator/`
- **Additions**:
  - `client.py`: `TagValidatorClient` providing `validate_tag(uid, counter, cmac)`, `generate_key(uid)`, `delete_key(uid)`, `undelete_key(uid)`, and `is_healthy()`.
  - Re-export `TagValidatorClient` in `tag_validator.__init__`.
- **Dependencies**: `pycryptodome` (or standard crypto), zero dependency on `game_server` or `sdm_provisioner`.

### 2.3 `sdm_provisioner/`
- **Location**: `sdm_provisioner/src/sdm_provisioner/`
- **Responsibilities**:
  - NFC card connection HAL (`hal.py`).
  - NTAG 424 DNA EV2 command set (`commands/`).
  - Interactive Provisioner Tool system (`tools/runner.py`, `tools/provision_factory_tool.py`, etc.).
  - Textual TUI (`tui/tui_main.py`).
- **Dependencies**: `pyscard`, `textual`, `coolname`, `shared`.

### 2.4 `game_server/`
- **Location**: `game_server/src/game_server/`
- **Responsibilities**:
  - Flask web server & REST API (`app.py`, `register_sticker_routes`).
  - Game state persistence (`game_state_manager.py` with `scan_logs` and `coins` table in `app.db`).
  - Service layers (`flip_off_service.py`, `sticker_service.py`, `vip_service.py`, `coin_message_service.py`).
  - Key custody delegation (`service_key_manager.py` using `tag_validator.client`).
  - Static WebP sticker art & Jinja2 templates (`static/`, `templates/`).
- **Dependencies**: `flask`, `pycryptodome`, `coolname`, `shared`, `tag_validator_service`.

---

## 3. Migration & Refactoring Strategy

1. **Step 1: Extract `shared/` package**:
   Create `shared/src/shared/__init__.py`, `uid.py`, `outcome.py`, `models.py`.
2. **Step 2: Add `tag_validator.client` to `tag_validator_service`**:
   Add `client.py` and unit tests in `tag_validator_service/tests/test_client.py`.
3. **Step 3: Move provisioner into `sdm_provisioner/`**:
   Copy hardware commands, hal, tui, and tools from `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner` to `sdm_provisioner/src/sdm_provisioner`, updating imports to use `shared`.
4. **Step 4: Move server into `game_server/`**:
   Copy server code, static assets, templates, and server tests into `game_server/`, updating imports to use `shared` and `tag_validator.client`.
5. **Step 5: Unified root Makefile & Clean-up**:
   Configure root `Makefile` targets. Remove obsolete `ntag424_sdm_provisioner/`. Run all test suites.
