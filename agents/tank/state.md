# Agent State — Tank (DevOps Engineer)

## Context
> ## Recent Decisions
> - Resolved Windows cross-platform virtual environment detection across all Makefiles (`Makefile`, `sdm_provisioner/Makefile`, `tag_validator_service/Makefile`, `game_server/Makefile`) supporting `.venv\Scripts\python.exe`.
> - Fixed Makefile `help` and environment variable exports for Windows `cmd.exe` compatibility.
> - Added Windows launcher scripts (`scripts/run-tui.ps1` and `run-tui.bat`) that auto-check/auto-start `tag_validator_service` on port 8080 before launching `provision-tui`.
>
> ## Key Findings
> - All 381 unit and integration tests across the workspace pass cleanly on Windows (`make test-all`).
> - Physical NFC hardware `ACS ACR122 0` is detected via PC/SC (`pyscard`).
> - Simulated card mode is supported via `-Simulated` switch or `NTAG_SIMULATION=1`.

## Current Task
**Status:** Complete
**Assigned to:** Tank
**Started:** 2026-10-23T12:08:00-04:00

### Task Description
Support building, testing, and running `sdm_provisioner` TUI on Windows.

### Progress
- [x] Fixed `.venv\Scripts\python.exe` path detection and GNU Make targets for Windows
- [x] Verified PC/SC smartcard connectivity (`ACS ACR122 0` reader recognized)
- [x] Created `scripts/run-tui.ps1` and `run-tui.bat` with auto-startup of `tag_validator_service`
- [x] Ran full workspace regression (381/381 tests pass)

### Blockers
None

## Next Steps
### Immediate Next Action
User can run `.\run-tui.bat` or `make run-tui` from terminal.

---
*Last updated: 2026-10-23T12:20:00-04:00*
