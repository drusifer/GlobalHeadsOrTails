# Current Task

Release handoff: user authorizes commit and local container rebuild only; user pushes/deploys from pi-patch. Tank owns rebuild. Latest 110 server tests, mobile browser and syntax/art checks pass.

## Test-tap stickers — 2026-10-07

User rejected separate simulator; removed its script and Makefile targets. Existing drew_test_outcome=heads/tails now awards stickers to selected coin using normal 50% odds and auto evolution. Invalid outcomes never award. Test UID/counter ledger is namespaced to avoid consuming real signed-tap awards; repeated test counter does not reroll. Increment hexadecimal ctr for new test drops. 110 server tests and syntax checks pass.

Complete; await feedback.

## Shared tab styling — 2026-10-06

Sticker Book styling now reuses the existing tab-content CSS for its panel. Collection-specific layout is inside the panel; removed custom panel background/border/radius and tab-button override, aligned cards and quote colors with existing page grays. Mobile browser acceptance and git diff --check pass.

Complete; await user feedback.

## Sticker Book feedback — 2026-10-06

Sticker Book now lives in the bottom tab group beside Recent Flips and Leaderboard. Current-season narrative is visible by default inside the tab. Only currently owned forms for the tapped coin render; no tap renders no stickers. Drop notices and wager actions remain outside tabs. Mobile browser acceptance passes, including no-tap description, tab switching, owned forms, evolution and wagers; syntax checks and git diff --check pass. Use CHROMIUM_PATH=/usr/bin/chromium make -C ntag424_sdm_provisioner test_sticker_ui on this machine.

Status: complete; await user feedback.


Latest action: gallery default bind changed to 0.0.0.0 with HOST override; user will run it. Assistant-started instance is being stopped.

Latest completed action: started local artwork gallery at http://127.0.0.1:8765/ (exec session 58487). Gallery and image return HTTP 200. All 36 forms are browsable with clan names and lore.

Latest completed action: updated all twelve clan names and lore, revised rivalry/quote text, exposed clan chronicles in album and regenerated runtime catalog. Stable family IDs preserve owned stickers and artwork; 36/36 asset validation passes.

Latest completed action: renamed the sticker pack to The Twelve Clans throughout runtime, generation tooling and active docs. Existing artwork IDs remain valid.

**Status:** Complete
**Assigned to:** Neo
**Started:** 2026-04-22

## Task Description
SSE → Polling refactor (5 tasks)

## Completed
- [x] Task 1: `has_flip_since(ts)` in `game_state_manager.py`
- [x] Task 2: `get_completed_since(ts)` in `flip_off_service.py`
- [x] Task 3: `GET /api/flips/since` + `GET /api/state` routes in `app.py`
- [x] Task 4: Removed `_sse_listeners`, `_push_sse`, `/api/stream/flips`, gevent monkey-patch, `stream_with_context`
- [x] Task 5: Replaced EventSource JS with `setInterval` poll loop + immediate tap firing

## Result
Historical completion: Trin reported 60/60 tests passing and Morpheus approved the refactor on 2026-04-22.

## Initialization — 2026-10-06

## Collectables implementation — 2026-10-06

Collectables complete: authenticated optional wagers, mobile album/reveal, atomic scan+award+progress/settlement and all36 verified illustrations. 109 server tests pass; Smith actual Chromium and full art approved; Morpheus code approved. Sprint locally released. See task.md.

100% complete: protocol and saved state loaded; chat reconciled; existing Neo discovery links verified. No baseline tests run.

Pending historical handoff: Smith requested mobile opponent-selection radio cards and larger flip-count buttons. Implementation status has not been inspected during initialization.

## Collectables backend handoff — 2026-10-06
Backend scope complete: sticker_service.py, flip_off_service.py, test_server_stickers.py, test_server_wagers.py. 81 server tests pass. Root integration, artwork and Smith final review in progress separately.
