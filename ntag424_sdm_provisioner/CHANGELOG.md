# Changelog

## 2026-03-26 - Flip Off Challenge Feature

### ✅ Added
- **FlipOffService**: `server/flip_off_service.py` — challenge lifecycle management (create, passive flip counting, entropy winner, expiry)
- **DB Table**: `flip_off_challenges` — stores challenge records with `baseline_scan_id` for reliable post-challenge flip filtering
- **Routes**: `POST /challenge/create` — JSON API to initiate a Flip Off challenge
- **Passive Counting**: Validated NFC taps automatically increment challenge progress via `record_flip()`
- **Template**: `index.html` — three new conditional sections: challenge launcher (post-tap), active progress bars, completed result card with entropy scores
- **PRD §13**: Full product requirements for Flip Off Challenge added to `docs/PRD.md`
- **Tests**: 15 unit tests (`test_server_flip_off.py`) + 7 integration tests (`test_server_flip_off_integration.py`)

### Technical Notes
- Challenge initiation on result page (not leaderboard) — avoids NFC tap navigation conflict
- Shannon entropy uses same H=1/T=0 bit encoding as the existing leaderboard analysis
- `baseline_scan_id` (max scan_logs.id at challenge creation) replaces timestamp filtering to avoid sub-second collision issues

---

## 2026-03-26 - Dad Jokes Feature

### ✅ Added
- **Dad Jokes Catalog**: `server/jokes.py` — static catalog of 25 jokes with `get_random_joke()` helper
- **Web Page**: `index.html` now displays one randomly chosen Dad Joke per page load ("Dad Joke of the Flip" section)
- **Tests**: 3 new tests in `test_server_logic.py` covering catalog size, return type, and page rendering

---


## 2025-10-30 - Authentication Fixed & API Refactored

### ✅ Fixed
- **Authentication**: Fixed CBC mode encryption (was using ECB mode) - Authentication now working ✅
- **Status Word Handling**: Accept `SW_OK_ALTERNATIVE` (0x9100) as success status

### ✅ Added
- **Full Chip Diagnostic**: `examples/19_full_chip_diagnostic.py` - Canonical API usage example
- **Command Classes**: `GetFileIds`, `GetFileSettings`, `GetKeyVersion` moved to `sdm_commands.py`
- **Dataclasses**: `FileSettingsResponse`, `KeyVersionResponse` with `__str__` methods
- **Helpers**: `parse_file_settings()`, `parse_key_version()` in `sdm_helpers.py`

### ✅ Improved
- **API Organization**: Parsing/formatting moved to helpers and dataclasses
- **Fresh Tag Handling**: Graceful handling of missing files on fresh tags
- **Documentation**: Updated to reflect authentication success

### 🗂️ Archived
- Investigation scripts moved to `examples/seritag/investigation/`
- Historical investigation docs marked appropriately

---

## Previous Work
- Registry key fix (EscapeCommandEnable)
- Static URL NDEF provisioning (works without authentication)
- Comprehensive Phase 2 protocol investigation
- See `SERITAG_INVESTIGATION_COMPLETE.md` for full history

