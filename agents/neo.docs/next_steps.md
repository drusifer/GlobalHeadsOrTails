# Next Steps

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


User owns gallery process now. Run make sticker-art-gallery to bind 0.0.0.0:8765; optional HOST/PORT overrides.

Local artwork gallery running at http://127.0.0.1:8765/ in session 58487. Leave running for user; restart using make sticker-art-gallery if needed.

Clan lore and naming update complete. Edit agents/smith.docs/collectables_catalog.md and use make sticker-catalog for future lore changes; preserve family-id comments. Await next task.

Latest naming decision: The Twelve Clans. Rename complete; await next task.

## Immediate Next Action

Latest status: collectables sprint complete, all36 assets shipped and reviewed,109 server tests/mobile browser/syntax checks pass. Await user's next task; no pending collectables work. Historical handoffs below are superseded.
2026-10-06: User requested collectable-sticker sprint discovery. Handed off to Cypher for discussion and requirements questions. Earlier Smith mobile UX request remains historical pending work.

## Key Files Changed
- `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/game_state_manager.py` — added `has_flip_since`
- `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/flip_off_service.py` — added `get_completed_since`
- `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/app.py` — SSE removed, polling endpoints added
- `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/templates/index.html` — JS polling loop

## Cold Start
1. Read CHAT.md bottom 20 messages
2. Load Neo state and PROJECT.md; consult Mouse's sprint plan and Oracle lessons/memory before implementation.
3. Do not run baseline tests for initialization alone. Use project Makefile targets when implementation or validation is requested.

## Collectables backend resume
Root owns app/catalog/UI; do not overwrite those files. Verify integrated endpoints after root wiring. Run make -C ntag424_sdm_provisioner test_collectables. Awards are separate from scan-log transaction; root must recover/retry a persisted flip whose award failed. No production deploy performed.
