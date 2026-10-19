# Rangers historical sticker pack — sprint requirements

Status: **BLOCKED — not released.** Image generation returned `usage_limit_reached` (HTTP429). At the stop checkpoint, 478 of 1,162 masters existed and 684 player IDs remained missing. All four managed lanes stopped cleanly. Reset: **2026-10-08 22:44:02 America/New_York** (2026-10-09 02:44:02 UTC; epoch1791513842). Exact missing IDs and evidence: `agents/neo.docs/rangers_art_blocker.json`; ignored quota report: `build/rangers-art/quota-report.json`. Packing the 478 existing masters does not satisfy full-art completeness. Twelve Clans remains active. Phases1–4 and phase6 preparation passed; 147 server checks, isolated active-Rangers browser and Smith preparation flow approved. One portrait per player serves three CSS evolution treatments. Full-art, package, activation and final release gates remain open.

## Scope and product decisions

The new pack celebrates the complete New York Rangers playing history, rather than a selection of famous alumni. Include every distinct player with at least one Rangers NHL regular-season OR playoff appearance through the 2026-10-07 America/New_York retrieval snapshot (2026-10-08T02:27:45UTC), from the franchise's first NHL season onward. Include goalies and playoff-only players. Exclude players who only attended camp, were drafted, or played solely for affiliates. Identify players by official NHL player ID; names are display text. Oracle reconciled **1,162 distinct players**: 1,156 regular-season union 507 playoff, with six playoff-only. Full source plan: `agents/oracle.docs/rangers_roster_sources.md`. Lester Patrick (NHL ID8448095) is already included, with one regular-season appearance as a skater and one playoff appearance as a goalie; preserve both role records without duplicating his family. Treat the audited snapshot as the release coverage contract; future snapshots require a deliberate catalog refresh and reconciliation.

Approved activation contract: Rangers becomes the active pack for new awards **only after complete artwork verification in phase 6**. Until then, Twelve Clans stays active. The Twelve Clans remains in the catalog, collection and wager system after transition. Existing IDs, copies, locks, award decisions and evolution remain valid. The album selects a pack, defaults to the active season pack, and shows only the tapped coin's owned stickers. No tap means season description but no stickers.

Continue four rarity tiers and three evolution levels. Coin name remains ownership identity across both UIDs. Preserve entropy/p-value award weighting, real-flip instructions, test-flip support, replay protection and wager settlement. For Rangers, each successful award draws directly from the entire player population using per-player weights Common=8, Uncommon=4, Rare=2, Legendary=1, normalized by the sum of weights across all eligible players. Legacy Twelve Clans draw policy remains unchanged. If total player weight is W and current drop probability is d, a player with weight w has probability d*w/W on that flip. This guarantees the intended per-player rarity ordering regardless of tier populations. Root and Smith prefer the legible twofold step because a 1,162-player pool already makes individual pulls scarce.

## Stories and acceptance criteria

### R1 — Complete, verifiable player collection

As a Rangers fan, I can collect a sticker for every historical Rangers player, including brief appearances and goalies.

- Catalog contains exactly one family per reconciled eligible NHL player ID and three forms per family.
- Release evidence records source URLs, retrieval/snapshot date, distinct roster count, inclusion rules, and any source disagreement; no silently skipped or duplicate players.
- A validation report reconciles the regular-season and playoff player union with all generated families; duplicate names do not merge distinct players.
- Historical numbers and spelling come from official NHL/Rangers data. The app renders collected players only and remains usable on mobile with a large roster.

### R2 — Famous players are the hardest pulls

As a collector, I recognize the biggest Rangers and hockey icons as Legendary, and can understand the rarity policy.

- Retain Common, Uncommon, Rare and Legendary labels, independently of evolution level.
- Publish a reviewed, deterministic editorial rarity manifest keyed by NHL player ID, with a reason and source for every curated promotion. Describe it as an editorial fan-favorite ranking, not a scientific popularity measurement.
- Smith-approved `rangers_rarity.json` defines 13 Legendary players: the 11 retired-number honorees plus Wayne Gretzky and Jaromir Jagr. All promotions use explicit NHL IDs, canonical names, reasons and official supporting URLs.
- The 22 Rare players comprise 18 additional official centennial fan favorites and modern-era stars Artemi Panarin, Adam Fox, Igor Shesterkin and Chris Kreider. Modern-era is a historical designation, not a claim that every player remains on the current roster. Uncommon uses a declared seed of at least 150 Rangers regular-season appearances in a single recorded role after overrides; other players are Common. Appearance totals do not measure popularity.
- Compute and verify **per-player** drop probability for every tier using normalized weights8/4/2/1. Every Legendary player has one-half a Rare player's probability, one-quarter an Uncommon player's probability, and one-eighth a Common player's probability under the same flip history. Do not apply the legacy60/25/12/3 tier-first draw to Rangers. Publish the resulting aggregate tier probabilities after roster classification, rather than claiming those legacy percentages still apply.
- No client parameter can select a player, tier or favorable roll. Replays retain their original pack/player/no-drop decision after pack changes.

### R3 — Player facts and meaningful stats

As a fan, I can read the player's Rangers accomplishments without confusing them with whole-career NHL totals.

- Cards identify player name, position, Rangers tenure, rarity and level; stats are explicitly labeled Rangers NHL regular-season career totals and dated to the snapshot.
- Skaters show GP, G, A and P. Goalies show GP, W, shutouts and available GAA/save percentage. Distinguish unavailable historical metrics from zero; do not sum or average rate stats incorrectly.
- A playoff-only player's regular-season values are honestly zero/not applicable and the card explains playoff participation; optional playoff totals are distinctly labeled.
- Mixed-role players retain separate skater and goalie records under one NHL ID, with role/competition labels. Specifically verify Lester Patrick's regular-season skater and playoff goalie appearances. Derive first/last Rangers seasons from per-season sources, not absent career aggregate fields.
- Every player has one short sourced fact or verified attributed quote. Prefer original factual summaries for complete coverage; never invent a player quote. A simple appearance/tenure fact derived from the verified stats is acceptable for lesser-documented players.
- Cards expose a source link/details affordance without crowding the mobile face. Factual copy and playful art captions are visually distinguishable.

### R4 — Funny, recognizable artwork using the existing generator

As a collector, I see an original, affectionate cartoon caricature of each player with gentle hockey humor.

- Reuse the project's existing ../recard-backed art adapter and repeatable make targets. Generate original images rather than substituting official photographs.
- Art direction uses recognizable player features, era-appropriate hockey gear and playful hockey situations, including gently exaggerated skates and New York bagel props; avoid invented biographical claims or mean-spirited jokes. Official headshots/archive references support likeness where available. Reject generic silhouette references; document historical interpretation when a trustworthy likeness reference is unavailable.
- Root's stated default after the optional question: one caricature per player reused across three clearly distinct evolving card treatments. Deliver 1,162 unique portrait WebPs and 3,486 metadata forms; code-native card frames provide the three level treatments with visible level labels, without duplicating bitmap assets. User steering can change this before generation; do not generate the full roster until Smith approves the sample and final scope.
- Sample gate **passed**: Steve Andrascik, Lester Patrick, Bill Cook, Wayne Gretzky, Henrik Lundqvist and Artemi Panarin; six real portraits rendered in all three production CSS treatments at 390px and 1280px. Corrected Andrascik used an actual archival reference after rejecting a generic silhouette. Smith explicitly approved the 18 actual card views at 22:53:34; that permits full generation but does not substitute for complete asset validation.
- Generation is resumable by stable player IDs; completed work survives interruption. Full release requires every promised portrait asset to exist and decode, with all three card treatments verified, no hidden placeholders or missing-player omissions.

### R5 — Safe pack transition and familiar Sticker Book

As an existing player, I keep my collection while a new season offers Rangers stickers.

- Existing Twelve Clans copies retain their names, artwork, levels, rarity, ownership and valid wagers. Three same-family/same-level unlocked copies still evolve within their own pack only.
- Both face UIDs share the same coin-name collection. No-tap state contains no owned stickers; tapping either face reveals that coin's collection only.
- Sticker Book remains in the bottom tab area using existing page/tab CSS. Season description identifies the current pack; archive selection shows only owned archive cards.
- Existing locks, completed settlements and replayed old awards remain readable after the catalog expands. New Rangers awards work through normal and supported test flips.
- The odds guidance continues to ask for real coin flips for the best sticker odds; adding popularity rarity does not imply physical fairness detection or a guaranteed drop.

## Verification and release evidence

Neo → Trin → Morpheus gates apply per small phase. Smith must explicitly approve stories and architecture before implementation, the representative artwork before full generation, and the final actual mobile experience before close. Oracle grooms source provenance and pack policy. Mouse tracks short phases. All personas contribute retro; Cypher launches only after complete roster, asset and regression evidence. No automatic commit, rebuild or deployment is part of this sprint request.

## Source and consultation record

- Oracle state, Mouse sprint history and Cypher state consulted. Oracle memory.md/lessons.md absent; read context.md instead.
- Official NHL roster directory: https://records.nhl.com/nyr/overview/roster (Oracle owns complete ingestion/reconciliation).
- Official retired-number entry: https://www.nhl.com/rangers/team/history/retired-numbers (embedded list requires source verification).
- Official franchise history: https://www.nhl.com/rangers/team/history/ (editorial history context; individual player facts need their own supporting source).
- Official player-profile example: https://www.nhl.com/rangers/team/alumni/henrik-lundqvist (retired-number honor; no unsourced popularity percentage implied).

Planning dependencies are resolved: Oracle reconciled full roster and per-season tenure, Smith reviewed the editorial rarity manifest, Morpheus approved multi-pack/weighted-draw architecture, and the sample gate passed. Remaining release work is full reference audit and portrait production, complete asset/reference validation, activation, final regression/browser/Smith acceptance, Oracle groom and required retro. See `rangers_release_checklist.md`; Cypher must not launch while any required item remains open.

## Frozen rarity audit

Conditional percentages apply only after a drop. Overall entropy/p-value odds remain 5%–50%; family weights do not increase that chance. Per-player probability on a flip is current drop chance multiplied by weight/8,197.

| Tier | Players | Weight per player | Conditional tier share |
| --- | ---: | ---: | ---: |
| Common | 908 | 8 | 88.6178% |
| Uncommon | 219 | 4 | 10.6868% |
| Rare | 22 | 2 | 0.5368% |
| Legendary | 13 | 1 | 0.1586% |

These aggregate percentages follow the frozen roster composition, not a ranked popularity poll. The Twelve Clans retains its existing 60%/25%/12%/3% conditional tier distribution.
