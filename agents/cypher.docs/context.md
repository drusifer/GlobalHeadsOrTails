# Agent Local Context

## Recent Decisions

- Added §14 Custom Coin Messages to PRD — covers form UX, CMAC auth model, 24-char limit, persistence
- Added §15 Secret Masking — documents mask_key utility and what is/isn't masked
- PRD lives at: `ntag424_sdm_provisioner/docs/PRD.md`

## Key Findings

- WHAT: PRD was last updated 2026-03-26 (through §13 Flip Off)
  - WHY: Neo implemented Custom Messages and secret masking in 2026-04-22 session; PRD needed catching up
- WHAT: Custom message auth model changed from DB-based validate_tap_auth to direct CMAC crypto
  - WHY: "Tap again" was unworkable UX — new tap opens a new page, the old cmac+ctr would be stale

## Important Notes

- §14 Definition of Done has two open items: unit tests for set_coin_messages and Trin QA sign-off
- §13 (Flip Off) still has open items: end_condition column, SSE payload standardization, yield fanfare

---
*Last updated: 2026-10-06*

## Collectables discovery

### Final delivery

Collectables sprint complete: 109 server tests, actual mobile browser acceptance, syntax checks and 36/36 asset verification passed. Smith approved all artwork and UI; Morpheus approved code including yield race fix. The Twelve Claims ships36 WebPs (2.1 MiB), catalog/lore, album/drop/evolution and optional atomic wagers. Runtime DB delta from test imports restored. Retro and changelog recorded. Workspace release only; no deployment.

### Confirmed by user during discovery

- Additional confirmed: all drops level 1; rarity unchanged on evolution; distinct artwork per level; launch 12 families (5/4/2/1 tiers), distinct looks, one faction each, original D&D-inspired classic RPG theme and lore quotes framing 12 competing factions. User delegated remaining design to Smith and authorized autonomous Bob Protocol sprint.

- Coin is the only identity; persist collection ownership against the coin in the database.
- Every valid flip qualifies, including Flip Off flips. Initial sticker drop probability: 50%.
- Four rarity tiers; conditional on a drop: Common 60%, Uncommon 25%, Rare 12%, Legendary 3%.
- Duplicate stickers allowed. Automatically combine three level-1 copies into one level-2, and three level-2 copies into one level-3. Maximum evolution level: 3; rarity is separate from evolution.
- Flip Off sticker wagers are optional. Both coins agree before starting and each chooses one sticker. Winner receives both; ties/cancellations return each sticker to its original coin.
- Wagered stickers are locked until the Flip Off ends, preventing reuse in another wager or consumption by evolution.
- Use art creation scripts from the user's `../recard RTG` project; exact directory and scripts still require inspection.
- Ask the user one question at a time. Current discussion: decide whether drops are always level 1 or may arrive evolved.

The initial open-question paragraph below is historical; the confirmed rules above supersede it.

User requested a new sprint for collectable stickers awarded randomly to coinflips, explicitly asking for discussion and questions. Ownership, eligible flips, drop frequency, duplicates, and display remain undecided. No implementation authorized in this discussion stage. Oracle memory/lessons and Mouse sprint_log paths were absent when checked.
