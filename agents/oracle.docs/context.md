# Oracle Working Context

## Current Status: ACTIVE
Generic YAML-driven art generator refactor, pack catalog reorganization, and legacy cleanup are fully complete and documented.

### Key Architecture State
2. **Pack Directory Structure**: `game_server/src/game_server/sticker_catalog/<pack-id>/`:
   - `twelve-clans/` (`cards.json`, `manifest.yaml`)
   - `rangers-history/` (`cards.json`, `manifest.yaml`, `champions_cards.json`, `champions.yaml`)
   - `fantasy-heroes/` (`cards.json`, `manifest.yaml`)
3. **Data vs. Prompt Decoupling**: Card records live in `cards.json` with all domain fields filled out; `manifest.yaml` provides set metadata, quality, resolution, and **1 per-item prompt template**.
4. **Clean Review**: Image inspection contact sheets (`contact_sheet.html`) render only raw artwork and prompts in clean HTML with zero card flair.
5. **Decisions Log**: Decision 11 & Decision 12 recorded in `docs/DECISIONS.md`.
6. **Workspace Reorg & Legacy Cleanup Complete**: `ntag424_sdm_provisioner` purged; `sdm_provisioner` has full parity (155 tests); 481 Rangers portraits preserved in `game_server`; root `.venv` active.
7. **All Tests Passing**: 367/367 tests pass across all workspace components.
