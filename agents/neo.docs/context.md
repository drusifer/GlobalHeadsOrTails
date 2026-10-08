# Agent Local Context

Release handoff: user authorizes commit and local container rebuild only; user pushes/deploys from pi-patch. Tank owns rebuild. Latest 110 server tests, mobile browser and syntax/art checks pass.

## Test-tap stickers — 2026-10-07

User rejected separate simulator; removed its script and Makefile targets. Existing drew_test_outcome=heads/tails now awards stickers to selected coin using normal 50% odds and auto evolution. Invalid outcomes never award. Test UID/counter ledger is namespaced to avoid consuming real signed-tap awards; repeated test counter does not reroll. Increment hexadecimal ctr for new test drops. 110 server tests and syntax checks pass.

Complete; await feedback.

## Shared tab styling — 2026-10-06

Sticker Book styling now reuses the existing tab-content CSS for its panel. Collection-specific layout is inside the panel; removed custom panel background/border/radius and tab-button override, aligned cards and quote colors with existing page grays. Mobile browser acceptance and git diff --check pass.

Complete; await user feedback.

## Sticker Book feedback — 2026-10-06

Sticker Book now lives in the bottom tab group beside Recent Flips and Leaderboard. Current-season narrative is visible by default inside the tab. Only currently owned forms for the tapped coin render; no tap renders no stickers. Drop notices and wager actions remain outside tabs. Mobile browser acceptance passes, including no-tap description, tab switching, owned forms, evolution and wagers; syntax checks and git diff --check pass. Use CHROMIUM_PATH=/usr/bin/chromium make -C ntag424_sdm_provisioner test_sticker_ui on this machine.


## Recent Decisions

- User will run gallery themselves and requires 0.0.0.0. Added configurable --host/HOST defaulting to 0.0.0.0; stop assistant-started session 58487 and hand over make sticker-art-gallery.

- Local artwork gallery added: tools/sticker_gallery.py, make sticker-art-gallery. Serves 36 images with clan names/quotes/chronicles on 127.0.0.1:8765; artwork links enlarge. Only allowlisted art files are served. Started for user's browsing; gallery and image HTTP checks pass.

- Clan lore updated beyond the pack title: all 12 display names now denote clans, with ancestral/kinship histories, paired rivalries and revised quotes. Added readable clan chronicles in album. Generator consumes explicit stable family-id comments to preserve DB ownership and all 36 existing asset paths. Runtime catalog regenerated and 36/36 assets verified.

- User renamed the sticker pack to **The Twelve Clans**. Updated UI heading, runtime catalog, catalog generator and active documentation; historical chat/summaries retain the original name.

### Collectables complete — 2026-10-06
- Root API/UI and delegated backend/art integrated and reviewed. All36 actual illustrations shipped as512px WebPs; packed total2.1 MiB. Catalog and static assets included in package data.
- Atomic scan/award/evolution/progress/settlement commits together; yield verifies actual current wager authorization under write lock.
- Validation:109 server tests, mobile browser flow, critical syntax checks and36-image decode check pass. Test-only tracked DB change restored. No deployment.

- **Customize form gate**: `coin_name` (which controls the ✏️ button and form) is only set in the index route when CMAC is cryptographically valid AND `ctr_int > last_counter` (replay check). Params table still shows on any valid uid+ctr visit.
- **auth model**: Removed DB-based `validate_tap_auth`. Save endpoint (`/api/coin/messages`) now calls `key_manager.validate_sdm_url(uid, ctr_int, cmac)` directly — same crypto the flip endpoint uses. Counter still required for CMAC math but not checked against DB.
- **mask_key**: Moved to `ntag424_sdm_provisioner/log_utils.py`. Imported by `csv_key_manager.py`, `diagnostics_service.py`, and `server/app.py`.
- **Max message length**: 24 chars (was 50). Enforced in `maxlength` attr on both inputs and server-side in `set_coin_messages`.
- **UI order**: ✏️ button (right-aligned) → form (hidden by default) → params table. Form opens above params.
- **Icons**: ✏️ = open, ❌ = close (unicode emoji, not SVG or letter x).

## Key Findings

- WHAT: `validate_sdm_url` in `csv_key_manager.py` logs all 3 AES keys, session key, and full CMAC in plaintext at INFO level
  - WHY: Was debug-era logging; now all masked via `mask_key()`
- WHAT: `app.py` debug log dumped raw `validation_result` dict including `session_key` and `full_cmac`
  - WHY: Fixed by building `safe` dict with those two fields masked before logging
- WHAT: Replay detection (ctr <= last_counter) only existed in `/api/flip`, not in the index route
  - WHY: Index route now fetches `game_manager.get_state(uid_str).last_counter` and gates `tap_valid` on it

## Important Notes

- `coin_name` template var is the single gate for all customize UI: button, form, JS vars, challenge lookup, messages fetch
- `tap_valid` is a local var in the index route — not passed to template; `coin_name` being set is the signal
- `via: enabled` per PROJECT.md — use `mcp__via__via_query` for symbol lookup

---
*Last updated: 2026-10-06*

## Protocol Initialization — 2026-10-06

- Loaded project protocol, recent chat, Neo instructions/state, and PROJECT.md. Existing Neo discovery links resolve to this project.
- Chat records Trin UAT passing 60/60 and Morpheus approval of polling on 2026-04-22; these are historical results, not rerun this session.
- Chat also records the immediate totals fix and Smith's pending mobile opponent-selection request (radio cards and larger flip-count buttons).
- Initialization only; application code and tests were not changed or executed.
- Shell sandbox fails at startup because read-only `.agents` crosses the writable symlink to `agents`; approved commands were used outside it.

## Collectables backend — 2026-10-06
- StickerService persists individual copies and every drop/no-drop decision keyed by UID/counter. RNG injectable; 50% drop, rarity 60/25/12/3; unlocked automatic 3:1 cascades through level 3.
- FlipOffService stakes use BEGIN IMMEDIATE; challenger lock at create, challenged lock at acceptance, baseline resets on acceptance. Pending wager flips do not count. Cancel/expiry/draw return stakes; accepted yield/win transfers both; settlement and terminal status atomic. Historical stakes retain catalog metadata after evolution consumes copies.
- Explicitly close SQLite connections. Expiry compares julianday to support both legacy ISO timestamps and SQLite CURRENT_TIMESTAMP.
- Last validation: make -C ntag424_sdm_provisioner test_collectables, 81 passed including 19 new backend regression tests.
