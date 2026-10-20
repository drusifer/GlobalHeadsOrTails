# Broadway Blueshirts release acceptance

Status: **BLOCKED — not released.** Image generation returned `usage_limit_reached` (HTTP429). At the stop checkpoint, 478 of 1,162 masters existed and 684 player IDs remained missing. All four managed lanes stopped cleanly. Reset: **2026-10-08 22:44:02 America/New_York** (2026-10-09 02:44:02 UTC; epoch1791513842). Exact missing IDs and evidence: `agents/neo.docs/rangers_art_blocker.json`; ignored quota report: `build/rangers-art/quota-report.json`. Packing the 478 existing masters does not satisfy full-art completeness. Twelve Clans remains active.

## Approved evidence already available

- [x] Smith story and architecture gates recorded; Morpheus phase 1–3 reviews approved.
- [x] Official NHL snapshot reconciled: 1,162 distinct IDs, 1,156 regular-season union 507 playoff; six playoff-only players preserved. All first/last Rangers seasons reconciled from per-season sources.
- [x] Stats are Rangers-only, with role and competition separated, unavailable historical values preserved, and Lester Patrick's skater/goalie appearances retained under one family.
- [x] Deterministic reviewed rarity: 908 Common, 219 Uncommon, 22 Rare, 13 Legendary; per-player weights8/4/2/1, total weight8,197. Source-backed 35 explicit player-ID promotions; remaining Uncommon seed150 regular-season appearances in a single role is editorial, not measured popularity.
- [x] 147 server checks pass, including registry validation, weighted boundaries, replay/no-drop preservation, legacy evolution/consumed stakes, and owned-only small polling responses.
- [x] Actual mobile browser checks pass for pack/search, no-tap descriptions/no cards, 3,486 dynamic form denominator, both face UIDs sharing coin-name ownership, regular-season-first/mixed-role/null stats, sources, entropy/test labels and existing wagers/evolution.
- [x] Actual six-portrait/18-card sample checked at390px/1280px: real512px images loaded, three structurally distinct frames and visible labels, official-source/fact/flavor details, no overflow or JS errors. Smith explicit approval2026-10-07 22:53:34. Evidence: nested `build/rangers-art-ui/`.

## Complete-art gate — all required before activation

- [x] Root's full reference audit has finished and published its report, including retrieved source URLs/date, invalid/generic silhouette rejection, and any honestly documented historical interpretation.
- [ ] Exactly1,162 unique expected player WebPs exist, decode at minimum512×512, and match the frozen player-ID set. No placeholder, missing ID, duplicate-family substitute or partial sample is counted as complete.
- [ ] All3,486 form references resolve to the correct player's portrait; three forms share one original bitmap per player and differ through production CSS treatment/visible level text.
- [ ] All36 original Twelve Clans images remain valid and its family IDs/names/lore remain intact.
- [ ] Trin verifies the full catalog/asset/reference report and representative full-roster checks; Morpheus approves phase5. Smith reviews completed-roster samples across eras/roles/rarities and reference gaps before release UX approval.

## Activation and final user acceptance

- [ ] Phase6 explicitly changes registry active ID to `rangers-history` after the complete-art gate, with no request-time network dependency or fallback to incomplete/malformed data.
- [ ] Fresh eligible normal and supported test flips draw Rangers using the existing entropy/p-value drop chance and normalized player weights. Replayed old awards and no-drops remain unchanged after activation.
- [ ] Existing Twelve Clans owned copies, locked stakes, settled historical wagers and family-specific evolution survive activation; both UIDs still resolve one coin-name collection.
- [ ] A fresh no-tap page defaults to Broadway Blueshirts season description with zero stickers; tapped coin shows only its own collected cards. Archive selection/search survives polling and never exposes unowned cards as collected.
- [ ] Actual final mobile/desktop UI loads the real activated artwork, preserves existing tab styling, shows readable sourced stats/facts plus separate original humor, and continues requesting physical flips for the best sticker odds.
- [ ] Installed package includes both catalogs, registry, current frontend assets, all1,162 Rangers portraits and all36 legacy images. Verify packaged contents through the existing repeatable packaging surface; no container rebuild is requested.
- [ ] Final relevant server/browser/syntax/asset checks pass after activation. Smith explicit final running-app approval and Morpheus review recorded; temporary test servers stopped and user database activity preserved by root.

## Close requirements

- [ ] Oracle active guide/PRD/decision/provenance/changelog/index grooming matches the final behavior and acknowledges the frozen snapshot rather than promising a permanently fixed roster.
- [ ] Mouse marks all six phases complete with evidence; every Bob persona posts required domain retrospective and backlog items.
- [ ] Cypher reviews the completed checklist, records workspace release and posts `*pm launch`. Until complete-art and final acceptance pass, status remains blocked and not released.

Nonblocking Smith polish backlog: expanded-detail grid whitespace, human-readable snapshot dates and clearer source-link labels. These may be addressed independently; they do not replace required completeness/activation evidence.


## Quota block and controlled resumption — 2026-10-07

**BLOCKED — not released.** Image generation returned `usage_limit_reached` (HTTP429). At the stop checkpoint, 478 of 1,162 masters existed and 684 player IDs remained missing. All four managed lanes stopped cleanly. Reset: **2026-10-08 22:44:02 America/New_York** (2026-10-09 02:44:02 UTC; epoch1791513842). Exact missing IDs and evidence: `agents/neo.docs/rangers_art_blocker.json`; ignored quota report: `build/rangers-art/quota-report.json`. Packing the 478 existing masters does not satisfy full-art completeness. Twelve Clans remains active.

The 147 server checks, isolated active-Rangers browser flow and Smith flow approval validate preparation only. They do not authorize a partial release, partial-package acceptance or launch.

1. Before reset, make no image-generation calls. Preserve valid masters, logs, reference audit and user database. Root may pack and inspect existing artwork only.
4. Finish all 1,162 unique portraits, pack and validate all 3,486 references and 36 legacy images. Trin/Morpheus review the complete report and Smith reviews completed-roster artwork.
5. Only then run the full `make -C ntag424_sdm_provisioner verify_rangers_package` gate, activate through the guarded production target, and repeat final server/browser/installed-package checks. No partial wheel counts as acceptance.
6. Oracle updates active-feature docs; Smith gives final running-app approval, Mouse closes phases and persona retrospectives, and Cypher checks acceptance and records launch. No commit, container build, push or deployment is authorized by this documentation update.
