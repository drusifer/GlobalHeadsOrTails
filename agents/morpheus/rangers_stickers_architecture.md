# Rangers historical sticker pack architecture

Status: Smith story Gate1 approved2026-10-07 22:30:26 and architecture Gate2 approved22:32:28. Mouse six-phase plan reviewed and approved; Neo phase1 authorized. Canonical pack ID rangers-history matches the final checked-in rarity manifest.

## Immutable identity and catalog registry

Keep SQLite ownership, award ledger and wager schemas unchanged. Existing Twelve Clans family IDs remain byte-for-byte stable. Rangers families use globally unique `nyr-<official NHL player ID>` IDs; each has levels1–3. The existing family-based evolution therefore cannot combine unrelated players or packs. Keep persisted award results authoritative on replay, including old pack drops and no-drop results. Keep exact-copy stakes and transaction boundaries unchanged.

Add an explicit pack registry with stable IDs (`twelve-clans`, `rangers-history`), title, narrative, snapshot, selection policy and active-pack ID. Load both immutable catalogs into an indexed family lookup used by decoration and historical wager display. Preserve the flattened `families` field shape while adding `packs`, `active_pack_id` and each family's `pack_id`. The public polling API sends family metadata only for the tapped coin's owned family IDs; no tap sends zero families. Pack headers always include title, narrative, total families/forms and rarity policy. Keep the full union cached server-side for draws, evolution and decoration; historical stakes carry their own decorated family/form metadata even after transfer. This avoids polling megabytes of unowned metadata every three seconds. Older single-pack fixture catalogs remain supported. Single-pack test fixtures without a registry retain their existing behavior. Reject duplicate family IDs, malformed levels and invalid policy weights at load/validation time.

The old pack stays active until the release verifier confirms the entire Rangers roster and all artwork. Change the checked-in active-pack ID only in the final verified phase. Do not silently fall back to another pack on malformed release data. Runtime requests need no NHL network dependency and no per-request image scans; deployment verification owns asset completeness.

## Award probability

Preserve the existing entropy/p-value drop decision and its transaction-aware coin-name history across both face UIDs. Only the conditional family draw changes for Rangers: weights Common8, Uncommon4, Rare2, Legendary1; choose one player directly from the complete eligible population using cumulative normalized weights. With total weight W and current drop chance d, a player's per-flip chance is d*w/W. Publish tier population counts and aggregate conditional probabilities from the frozen classification, rather than reusing legacy60/25/12/3. The Twelve Clans retains its tier-first policy when active. RNG remains injectable; client requests cannot choose pack, player or rarity. Store the chosen result once before committing. Tests use fixed boundary rolls, not statistical flaky trials.

## Reproducible roster and editorial data

Use Oracle's audited official NHL four-report regular-season/playoff union: exactly1,162 unique IDs for the snapshot. Preserve raw response URLs and timestamp in a compact tracked provenance/coverage manifest; ignored build caches retain full fetches. Import career and per-season reports sorted by playerId/seasonId. Validate pagination totals, duplicate rows, career/per-season ID unions and Rangers team filtering. Derive actual first/last Rangers seasons from per-season records. Numeric ID controls joins; canonical API names control display.

Store separate regular-season/playoff and skater/goalie records per player; never flatten Lester Patrick's mixed roles. Historical unavailable values remain null. Use official aggregated goalie rates or correctly calculated total-based rates, never mean percentages. Catalog player metadata contains NHL ID, name, position/roles, Rangers tenure, labeled team-only statistics, snapshot and source URLs. One original sourced summary fact per player may be computed from these totals; quote support is optional and must carry verified attribution. An original playful caption is a separate field and is never attributed to the player.

Freeze a player-ID rarity override manifest with reasons and official supporting links for curated stars. Retired-number honorees plus Gretzky are explicit Legendary candidates; Smith reviews the final fan-favorite editorial assignments. Lower-tier appearance thresholds must be deterministic and documented as seeding, not measured popularity. Verify all curated IDs exist in the coverage union and no named star is assigned by ambiguous spelling.

## Existing art generator, one portrait and three treatments

Parameterize the current `tools/sticker_art.mjs` adapter with explicit pack/catalog/output options while preserving existing defaults and Twelve Clans paths. Continue importing the actual adjacent recard manifest, runner, validator and packer. Retain normal sandbox behavior, resumable generation, per-ID locks, per-image logs, selective IDs and reverse lanes. New Ranger assets live under a pack subdirectory and reference an explicit catalog asset URL, avoiding guessed legacy file paths.

Generate one original caricature master and one packaged WebP per player, referenced by all three form records. Use deterministic CSS card frames/borders/level markings to create three visibly distinct rendered card treatments; do not duplicate portrait bitmaps. This is the root-communicated scope assumption, still subject to user steering before production. Deliver1,162 decoded unique512px-minimum packaged WebPs and3,486 valid form metadata references. Separate CSS card treatments from portrait generation so frame updates are cheap and reproducible. Levels must differ by frame structure, shape/markings and visible level text, not color alone. Every rendering surface uses the same form.image URL helper with the legacy filename fallback, including album, award notices, wager stakes and gallery.

Approve six representative players before full generation: Lundqvist, Gretzky, Messier, Bill Cook, Lester Patrick and one Common short-tenure player. Each prompt includes sourced era/position/appearance features and gentle hockey humor. Use officially sourced player portraits/headshots as generation references where available, recording the reference URL and retrieval date. For historical gaps, research a documented official archival reference; if none exists, honestly record a stylized historical interpretation, avoid claiming a faithful likeness, and ask Smith to assess whether recognizability is sufficient. Do not invent facial specifics as facts. Delivered images remain original cartoons. Full generation waits for Smith's explicit sample approval.

## Sticker Book and gallery

Keep the existing bottom tab and CSS. Display current-pack narrative by default even without a tap; display zero cards without a resolved tapped coin. With a coin, derive the rendered list from owned copies first, then selected pack/search filters. Pack selection supports the retained archive. Search names locally across owned families; render only owned results and lazy-load images. Counts and evolution totals derive from catalog data instead of hard-coded12/36. Keep selected pack across polling, while an active season change uses the default only for a fresh session. Both UIDs resolve the same coin-name inventory.

Cards expose readable name, rarity, level, quantity, lock and team-only stats; source/details affordance exposes tenure, fact, snapshot, sources and any separate postseason/role records without overcrowding mobile. Use textContent/escaping for all imported text. Continue real-coin-flip odds instructions and test-flip support. Adapt the read-only artwork gallery to select packs and search the large roster with pagination/lazy loading, instead of downloading thousands of images immediately.

## Verification and release gate

### Reference coverage decision (2026-10-07)

The complete reference audit found717 downloadable official portrait candidates and445 unavailable/generic silhouettes across1,162 players. A downloaded image is a candidate, not proof of verified identity or correct depicted era. The Smith-approved brief permits disclosed archival interpretation where trustworthy photo coverage is incomplete; requiring445 outside photos before any generation would exceed that approved contract. Continue generating the complete roster, while retaining mandatory visual quality and era checks.

Embed per-player `art_reference` metadata with status, source URL(s), retrieval date and reference scope, backed by the tracked source index. Use precise states that distinguish downloaded candidate, verified reference actually used, and archival interpretation without a verified likeness. In owned-card details show **Archival cartoon interpretation; facial likeness unverified** when no validated identity reference was used. Source unavailability must never be silently converted to verified accuracy. If generation research locates a trustworthy additional reference, record the actual source and review evidence before upgrading its state. Source URLs remain links/details metadata; all imported text is escaped. These disclosures do not waive complete artwork, stats, era or final Smith acceptance gates.

Small phases, each1–3 tasks, with Neo→Trin→Morpheus review:

1. Reproducible data importer, rarity/facts manifest and roster/stat reconciliation.
2. Multi-pack service registry and direct weighted selection, with replay/evolution/wager regression coverage.
3. Owned-only pack/search/details UI and gallery integration using existing styling; mobile/no-tap/shared-UID checks.
4. Parameterized art adapter and three distinct accessible CSS level treatments; Smith six-player visual approval.
5. Full resumable portrait production and1,162-WebP/3,486-form-reference validation. This phase cannot close on a sample or manifest alone.
6. Activate Rangers only after complete coverage/art gate; package assets, docs/provenance, all regressions and actual mobile Smith approval.

Mouse owns final task sizing and tracking. Oracle records the multi-pack/identity/weighted-draw decision and source contract. Mandatory release evidence includes exact roster set equality,1,162 valid unique WebPs,3,486 valid form references, three visibly distinct CSS level treatments with no missing IDs, all old36 images intact, reviewed rarity manifest and computed odds, preserved old inventories/wagers/replays, unchanged entropy policy, relevant server checks, browser acceptance and package-data inclusion. No commit, container build, push or deployment is implied by this sprint.
