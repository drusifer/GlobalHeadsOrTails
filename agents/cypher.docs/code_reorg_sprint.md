# Sprint Backlog: Code Reorganization & Component Consistency

**Sprint Goal**: Reorganize repository into consistent peer top-level components (`tag_validator_service/`, `sdm_provisioner/`, `game_server/`), separating the NFC hardware provisioner and tools from the game server.

---

## User Stories

### US-REORG-001: Extract `sdm_provisioner/` Component
**As a** hardware engineer or tag provisioner,  
**I want** the provisioner and interactive tool system in a dedicated top-level `sdm_provisioner/` package,  
**So that** hardware provisioning, TUI, and APDU commands are clean, self-contained, and consistent with `tag_validator_service/`.

#### Acceptance Criteria
1. Move provisioner source code (`commands/`, `crypto/`, `hal.py`, `card_factory.py`, `tui/`, `tools/`, `sequence_logger.py`, `uid_utils.py`, `seritag_simulator.py`) into top-level `sdm_provisioner/`.
2. Dedicated `sdm_provisioner/pyproject.toml` defining package `sdm-provisioner` with CLI entrypoints `provision-tui` and `provision-tag`.
3. Dedicated `sdm_provisioner/Makefile` supporting `make test`, `make lint`, `make tui`.
4. Provisioner tests moved to `sdm_provisioner/tests/` and pass cleanly.

---

### US-REORG-002: Extract `game_server/` Component
**As a** game operator or developer,  
**I want** the Global Heads or Tails Flask web server in a dedicated top-level `game_server/` package,  
**So that** web routing, stickers, flip-off challenges, and VIP bat signal services are decoupled from NFC hardware provisioning dependencies (`pyscard`).

#### Acceptance Criteria
1. Move server code (`app.py`, `game_state_manager.py`, `flip_off_service.py`, `sticker_service.py`, `vip_service.py`, `coin_message_service.py`, `static/`, `templates/`) into top-level `game_server/`.
2. Dedicated `game_server/pyproject.toml` with `flask`, `pycryptodome`, `coolname` dependencies.
3. Dedicated `game_server/Makefile` supporting `make run` (port 5001/5000), `make test`, `make docker-build`.
4. Server tests moved to `game_server/tests/` and pass cleanly.
5. Server uses `ServiceKeyManager` / remote key validation with graceful offline fallback.

---

### US-REORG-003: Harmonize Root Workspace & Top-Level Makefile
**As a** developer,  
**I want** top-level build targets and consistent tooling across all services,  
**So that** I can build, test, and run any component from root without path confusion.

#### Acceptance Criteria
1. Root `Makefile` exposes unified targets:
   - `make test`: runs tests across all services (`tag_validator_service`, `sdm_provisioner`, `game_server`).
   - `make run-server`: runs the game server.
   - `make run-validator`: runs the key validator service.
   - `make run-tui`: launches the provisioner TUI.
2. Root `docs/SDLC.md` updated with the 3 peer components architecture topology.
3. Obsolete/empty directories cleaned up.

---

### US-REORG-004: Comprehensive Regression Testing
**As a** QA guardian,  
**I want** all unit and integration tests passing in their new component locations,  
**So that** zero regressions occur across cryptographic calculations, WORM key management, or game features.

#### Acceptance Criteria
1. 100% of tests pass across `tag_validator_service`, `sdm_provisioner`, and `game_server`.
2. Ruff checks clean with zero errors.
