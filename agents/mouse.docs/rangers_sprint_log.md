# Rangers historical pack — implementation phases

Approved stories: ../cypher.docs/rangers_stickers_sprint.md. Architecture: ../morpheus.docs/rangers_stickers_architecture.md. Smith Gate1/Gate2 passed. Snapshot1162players; one1162portraitset and3486formmetadata/CSSleveldesigns. PackIDrangers-history. No commit/build/deploy in scope.

1. Data/catalog (Neo → Trin → Morpheus): import frozen career+season sources and reviewed rarity; create1162playerfamilies with sourced facts, separate role/competition/null stats and tenure; verify exact coverage/rarity/provenance.
2. Pack service (Neo → Trin → Morpheus): indexed multi-pack registry preserving old IDs/wagers/replays; direct8/4/2/1 player draw and legacy policy; tests for archive awards and safe activation.
3. Sticker Book (Neo → Trin → Morpheus): current/archived pack selector and owned-only search/dynamic counts; readable stats/facts/source details and three CSS treatments; mobile acceptance using existing styles.
4. Art tooling/sample (Neo → Trin → Morpheus, Smith): parameterize existing recard adapter without breaking Clans; generate six representative caricatures and show three level treatments; Smith explicit approval before full generation.
5. Complete artwork (Neo → Trin → Morpheus): resumably generate all1162portraits; pack/validate every expected asset and form reference; inspect across roster and report actual complete counts, no placeholders.
6. Activation/close (Neo → Trin → Morpheus → Oracle → Smith → retro → Cypher): activate only after complete asset/roster gate; full server/browser regression and legacy inventory/wagers; docs/retrospective/workspace launch.

Each phase has three or fewer tasks. Oldpackremainsactive untilphase6; releasecannotclaimcomplete while anycaricaturemissing. Userartsteeringoverridesoneportraitdefaultbeforegeneration. Everypersona savesstateandchat beforehandoff.

## Progress — 2026-10-07 22:54

Phases1–4 approved: catalog1162/3486;145serverchecks; mobilepack/search/stats/source/sharedUID/legacywagers; actual6portraits×3frames at390/1280, Smithexplicitapproval22:53:34. Phase5fullproduction authorized; referenceaudit active. OldClans remainsactive until all1162realportraits pass. No fullproduction completion claimed.


## Quota block and controlled resumption — 2026-10-07

**BLOCKED — not released.** Image generation returned `usage_limit_reached` (HTTP429). At the stop checkpoint, 478 of 1,162 masters existed and 684 player IDs remained missing. All four managed lanes stopped cleanly. Reset: **2026-10-08 22:44:02 America/New_York** (2026-10-09 02:44:02 UTC; epoch1791513842). Exact missing IDs and evidence: `agents/neo.docs/rangers_art_blocker.json`; ignored quota report: `build/rangers-art/quota-report.json`. Packing the 478 existing masters does not satisfy full-art completeness. Twelve Clans remains active.

The 147 server checks, isolated active-Rangers browser flow and Smith flow approval validate preparation only. They do not authorize a partial release, partial-package acceptance or launch.

1. Before reset, make no image-generation calls. Preserve valid masters, logs, reference audit and user database. Root may pack and inspect existing artwork only.
4. Finish all 1,162 unique portraits, pack and validate all 3,486 references and 36 legacy images. Trin/Morpheus review the complete report and Smith reviews completed-roster artwork.
5. Only then run the full `make -C ntag424_sdm_provisioner verify_rangers_package` gate, activate through the guarded production target, and repeat final server/browser/installed-package checks. No partial wheel counts as acceptance.
6. Oracle updates active-feature docs; Smith gives final running-app approval, Mouse closes phases and persona retrospectives, and Cypher checks acceptance and records launch. No commit, container build, push or deployment is authorized by this documentation update.
