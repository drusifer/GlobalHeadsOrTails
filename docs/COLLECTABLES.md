# Collectable stickers

Sticker packs share a coin-owned collection; anyone holding its signed tap URL can act for that coin, consistent with the existing tap-based model. There are no person accounts. The original Twelve Clans pack has 12 RPG clans and 36 illustrated forms.

The clans are Hearthshield, Mosswhisper, Brassburrow, Redcap, Moonwake, Dawn Oath, Velvetclaw, Ashquill, Stormhorn, Tideglass, Emberwing and Crownless. Each has its own kinship tradition, ancestral ambition and rival. The Sticker Book tab beside Recent Flips and Leaderboard shows the current season description and shared clan story, even without a tap. Artwork appears only for forms currently owned by the tapped coin; without a tap, no stickers appear. Individual sticker quotes reveal their feuds. Display names and lore may change while stable family IDs preserve existing ownership and artwork.

## Rules

- Physically flip your coin before each tap for the best sticker odds, and tap the face that lands. Each genuine validated Heads/Tails tap has a 5%–50% drop chance based on exact coin history across both face UIDs. Developer test Heads/Tails taps use the same drop odds and evolution in the coin’s collection. Repeated test UID/counter pairs do not reroll; increment the hexadecimal `ctr` for each new test tap. Invalid taps do not award.
- Twelve Clans conditional rarity chances: Common 60%, Uncommon 25%, Rare 12%, Legendary 3%. Families within a tier are equally likely. Rangers uses individual player weights described below.
- Drops start at level 1. Three unlocked copies of one family/level combine automatically, up to level 3. Rarity stays fixed.
- Optional Flip Off wagers lock one exact copy per participant. Challenger offers; opponent chooses a copy and accepts. No progress counts before acceptance. Winner keeps both. Draw/decline/cancel/expiry returns originals. Yield after acceptance forfeits the stake; pending-offer yield returns it.
- Accepted matches cannot be unilaterally cancelled. Inventory unlock/transfer triggers evolution and displays resulting forms.

## Weighted drop odds

Chance = `0.5 × max(0.1, (entropy / 8) × p_weight)`. Entropy uses exact Heads/Tails counts, scaled to 0–8. At 100 actual flips, `p_weight` is the monobit p-value `erfc(abs(heads − tails) / sqrt(2 × count))`. Before 100 flips, the p-value is unavailable and its weight is neutral (1); entropy still applies. The 5% floor avoids locking out new coins and streaks. A balanced history reaches the 50% ceiling. No synthetic byte-padding bits contribute.

These balance-based game scores are not proof of physical randomness. Repeated same-side outcomes can reduce the chance; no drop is guaranteed. The Sticker Book shows the current chance and early-history explanation. The next flip changes the history before its award is calculated and can change the chance.

Real awards use genuine history only. Developer test awards use genuine plus test history, explicitly labeled in the UI; they never change real odds. Test retries return the stored result without logging another score observation. Each fresh eligible scan, score snapshot, drop/no-drop and evolution commit together. Existing reward rows remain readable.

## Persistence and API

Existing SQLite DB receives `stickers`, `sticker_awards` and `flip_off_wagers` tables. Award decisions persist for each canonical UID/counter, including no-drop results. Physical scan, award/evolution, battle progress and settlement commit or roll back together. No reset/import is needed for an existing DB.

`GET /api/stickers?coin_name=NAME` returns public catalog, inventory, latest challenge (including returns) battle state and current `odds` (drop_chance, entropy, p_value, flip_count, warmup and includes_test). Add `drew_test_outcome=heads` or `tails` to inspect test-inclusive odds. `/api/flip` includes `sticker_award` with the persisted `odds` used for that decision, and current `stickers`.

Catalog responses always include pack descriptions, totals and rarity policies, but family metadata only for stickers owned by the requested coin. No coin returns no family metadata or sticker images. The Sticker Book defaults to the current season, retains a selected archive through polling and searches only the coin's collected player/family names. Both face UIDs resolve to the same coin-name inventory. Old awards, artwork, wagers and evolutionary family IDs survive season changes.

`POST /challenge/create` optionally takes `sticker_id`; signed `uid`, hexadecimal `ctr`, and `cmac` must match the challenger. `/challenge/accept` takes those credentials plus `challenge_id` and `sticker_id`; `/challenge/cancel` takes credentials plus `challenge_id`. Wagered `/challenge/yield` also requires matching credentials. Posted names cannot authorize another coin.

## Development checks

```sh
make -C ntag424_sdm_provisioner test_collectables
make -C ntag424_sdm_provisioner lint_collectables
make -C ntag424_sdm_provisioner test_sticker_ui
```

Set `CHROMIUM_PATH=/usr/bin/chromium` to use a locally installed browser instead of Playwright’s bundled Chromium.

The browser check uses a temporary database and a deterministic signed-key test seam, launches actual Chromium, and exercises the mobile album and two-coin wager flow. It does not require physical tags.

`make -C ntag424_sdm_provisioner test_rangers_art_ui` additionally checks six actual portraits in all three frames at mobile and desktop widths; review screenshots in `build/rangers-art-ui` under the provisioner project. This is a sample-art check, not full-roster completeness.

## Rangers historical pack — BLOCKED, not released

**Broadway Blueshirts: Rangers Through the Years** (`rangers-history`) covers a frozen official NHL snapshot of 1,162 players, including six playoff-only appearances. Every NHL player ID has one original humorous caricature shared by three card treatments: Rinkside, Spotlight and Garden Glow. Level labels and frame structures distinguish all three; they are not three duplicated portrait files. The Twelve Clans remains active until all 1,162 real WebPs and 3,486 form references validate and final review passes.

Rarity is an editorial fan-favorite ranking supported by official team history, retired numbers and fan-favorite lists, rather than measured popularity. The reviewed roster has 908 Common, 219 Uncommon, 22 Rare and 13 Legendary players. Conditional on a sticker drop, each Common player has weight 8, Uncommon 4, Rare 2 and Legendary 1, normalized over total weight 8,197. Thus an individual Legendary player is eight times harder to pull than an individual Common player. The entropy-based overall drop chance stays 5%–50%; the old pack retains its original tier-first draw policy.

Stats are Rangers-only NHL totals with regular season/playoffs and skater/goalie roles kept separate. Historical unknown metrics display as unavailable. Player facts derive from sourced statistics; humorous cartoon flavor is original writing and never attributed as a player quote. Snapshot, tenure and official sources are available in player details. Appearance references are separately audited:717 downloadable candidates and 445 rejected generic silhouettes. Downloading a candidate does not verify a likeness. Cards disclose unverified cartoon interpretations, explicitly identifying archival interpretations where no usable reference exists.

Source/rarity records: `../../agents/oracle.docs/rangers_roster_sources.md`, `../../agents/oracle.docs/rangers_art_sources.json` and `../../agents/cypher.docs/rangers_rarity.json`. Reproduce metadata with root targets `rangers-roster-audit`, `rangers-roster-seasons` and `rangers-catalog`. Frozen report hashes and request URLs are retained in the compiled catalog.

## Art production

Runtime metadata: each pack's `cards.json`. Smith's creative specification: `../../agents/smith.docs/collectables_catalog.md`.

Sticker art is made with **artai** (sibling repo `../artai`, override with `ARTAI_SRC=`), which `make install-art` pip-installs (editable) into its own `.venv-art/` so the workspace environment is untouched. Each pack's manifest lives in `game_server/src/game_server/sticker_catalog/<pack>/` (`manifest.yaml` + `cards.json`); set `MANIFEST=` to choose one (default Twelve Clans).

```sh
make art-status   [MANIFEST=...]             # items, masters, packed, missing
make art-generate BACKEND=codex [MANIFEST=...]  # paint missing masters (resumable; quota stops with exit 2), then pack
make art-pack     [MANIFEST=...]             # re-pack masters into the manifest's output_dir
make art-review   [MANIFEST=...]             # HTML contact sheet
make art-verify   [MANIFEST=...]             # every sticker present, 512x512, unique, not placeholder art
```

Masters live in ignored `build/artai/<set name>/masters/`; packed WebPs ship from each manifest's `output_dir`. `BACKEND` is required (`codex`, `agy`, `gemini`, `command`, `mock`). Options, providers and exit codes: artai's `docs/USAGE.md`.
