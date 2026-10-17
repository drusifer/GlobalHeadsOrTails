# Agent Local Context

## Current Rangers product acceptance — supersedes planning notes below
Pack: Broadway Blueshirts: Rangers Through the Years (`rangers-history`). Phases1–4 complete;145serverchecks, actualmobile flow and sixactualportraits×3CSSlevels passed. Smithsampleapproval2026-10-07 22:53:34 authorizes fullgeneration. Root phase5production/referenceaudit running; oldTwelveClans remainsactive. Oneportrait/player+3CSSframes is final art agreement; sourced Rangers-only stats/facts and original bagel/hockey humor are distinct. Reviewed rarity908Common/219Uncommon/22Rare/13Legendary,8/4/2/1 perplayer,total8197. User ownership remains coin name across bothUIDs. Full1162WebPs/3486refs, activation and finalgates remain required. Requirementsprogress updated; rangers_release_checklist.md prepared but NOTlaunch. RootOracle owns active guides; no commit/build/deploy.

## Rangers historical pack planning — 2026-10-07
Rarity curation complete: rangers_rarity.json Smith approved, packIDrangers-history;13Legendary(retired11+Gretzky/Jagr),22Rare(18additionalFanFavorites+Panarin/Fox/Shesterkin/Kreider),219Uncommon>=150RSgames in single role,908Common. Normalized weighttotal8197.35finiteIDoverrides all canonical names checked against1162officialIDunion. Root art architecture1162uniqueWebPs +3486metadataforms/3CSSframes supersedes earlierdistinctbitmapwording.
Final planning update: Oracle source artifact rangers_roster_sources.md confirms1162distinct =1156RS union507playoff,6playoff-only; local snapshot2026-10-07 fetched2026-10-08T02:27:45UTC. LesterPatrickID8448095 included in both roles (1RSskater,1playoffgoalie). Root/Smith revised weights to8/4/2/1 because100-foldrarity is punitive in large roster; latest story policy supersedes earlier100/25/5/1. Ready final Smith Gate1.
Update: root instructed planning default of one generated caricature/player reused across three distinct rendered evolution treatments after optional-question wait; full generation remains gated. Rangers draw is normalized per-player weight Common100/Uncommon25/Rare5/Legendary1, not legacy tier-first percentages. Story draft updated. Final Smith Gate 1 still awaits Oracle coverage reconciliation.
User requests full historical NY Rangers roster, most popular Legendary, stats, fact/quote, gently funny caricatures, reuse art generator. Draft: rangers_stickers_sprint.md. Root owns one pending question: one portrait reused over three card treatments vs three generated caricatures/player. Oracle researches distinct NHL-ID union of NYR regular-season and playoff appearances and NYR-only career stats. Proposed active Rangers pack preserves all Twelve Clans ownership/evolution/wagers and old replay decisions. Critical finding: fixed tier distribution may invert per-player rarity for a large roster; strict per-player odds ordering required. Retired-number honorees plus editorial icons proposed Legendary; no objective popularity claim. Smith Gate 1 cannot finalize until art choice and scope are frozen. No app code changed.

## Entropy awards workspace release — 2026-10-07
User requested weighted sticker odds and real-flip instructions. Delivered5%-50% exact entropy/monobit weighting, current chance and warm-up/test labels, coin-name aggregation and persisted atomic replay decisions. All gates passed:126 server tests, syntax, extended actual mobile browser (mature50%/p1, test isolation, existing album/evolution/wagers). Decision7/PRD16/feature guide/changelog/index and retro current. No build, commit, push or deployment performed.

## 2026-10-07 entropy awards sprint
Current plan: entropy_stickers_sprint.md; user wants lower entropy/p-value to reduce drop odds and real-flip guidance. Proposed5%-50% floor/ceiling, neutral unavailable p-value until100 actual flips, coin-name aggregation across faces; test awards preserved. Oracle context consulted (memory/lessons missing), Mouse context read. Smith Gate1 review requested. Prior flat50% requirements are superseded when this sprint ships.

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
