# Changelog

## Upcoming - Rangers historical pack (BLOCKED, not released)

- Artwork quota block:478 masters/684 missing; all managed lanes stopped. Reset2026-10-08 22:44:02 America/New_York. Twelve Clans remains active; full artwork/package/final review/launch gates remain open.
- Full official 1,162-player catalog with Rangers-only stats, sourced facts and original cartoon humor.
- Multi-pack archive support, owned-only name search, player/source details and three structural evolution frames.
- Editorial fan-favorite rarity with individual 8/4/2/1 weights; old inventory, wagers, entropy odds and stored awards preserved.
- Existing Recard art generator reused; six-portrait/eighteen-card sample approved. Full roster artwork and activation remain pending.
- Current validation:147 server tests, syntax, sample artwork and isolated active-Rangers browser preparation pass.

## 2026-10-07 — Entropy-weighted sticker drops

- Odds vary from 5% to 50% based on exact coin entropy and monobit p-value, shared across both face UIDs.
- Current odds, warm-up policy and real physical-flip instructions appear in the Sticker Book.
- Test awards use the same policy without affecting real odds; retries preserve original score/drop decisions.
- Validation: 126 server tests, syntax checks and actual mobile browser acceptance pass, including mature odds, test labels/history isolation and existing album/evolution/wager flows.

## 2026-10-06 — Collectables: The Twelve Clans

- Coin-owned sticker album with 12 original RPG factions, 36 named/illustrated forms and narrative lore quotes.
- 50% random drops, four rarity tiers, and automatic three-copy evolution through level 3.
- Optional mutually agreed Flip Off wagers, locked copies, winner transfers and returns on ties/cancellation/expiry.
- Atomic scan/reward/battle settlement, authenticated wager ownership checks and migrated SQLite persistence.
- Reusable recard RTG art-generation/packing workflow; all 36 images verified and visually reviewed.
- Sticker Book uses existing bottom-tab styles, shows season lore and only the tapped coin’s owned forms.
- Developer test Heads/Tails taps award stickers with normal odds and automatic evolution.
- Validation: 110 server tests, syntax checks and actual mobile browser acceptance passed.

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

