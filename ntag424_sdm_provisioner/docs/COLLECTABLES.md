# Collectable stickers

The Twelve Clans is a pack of 12 original RPG clans and 36 illustrated forms. A coin owns its collection; anyone holding its signed tap URL can act for that coin, consistent with the existing tap-based model. There are no person accounts.

The clans are Hearthshield, Mosswhisper, Brassburrow, Redcap, Moonwake, Dawn Oath, Velvetclaw, Ashquill, Stormhorn, Tideglass, Emberwing and Crownless. Each has its own kinship tradition, ancestral ambition and rival. The Sticker Book tab beside Recent Flips and Leaderboard shows the current season description and shared clan story, even without a tap. Artwork appears only for forms currently owned by the tapped coin; without a tap, no stickers appear. Individual sticker quotes reveal their feuds. Display names and lore may change while stable family IDs preserve existing ownership and artwork.

## Rules

- Each genuine validated Heads/Tails tap independently has a 50% drop chance. Developer test Heads/Tails taps use the same drop odds and evolution in the coin’s collection. Repeated test UID/counter pairs do not reroll; increment the hexadecimal `ctr` for each new test tap. Invalid taps do not award.
- Conditional rarity chances: Common 60%, Uncommon 25%, Rare 12%, Legendary 3%. Families within a tier are equally likely.
- Drops start at level 1. Three unlocked copies of one family/level combine automatically, up to level 3. Rarity stays fixed.
- Optional Flip Off wagers lock one exact copy per participant. Challenger offers; opponent chooses a copy and accepts. No progress counts before acceptance. Winner keeps both. Draw/decline/cancel/expiry returns originals. Yield after acceptance forfeits the stake; pending-offer yield returns it.
- Accepted matches cannot be unilaterally cancelled. Inventory unlock/transfer triggers evolution and displays resulting forms.

## Persistence and API

Existing SQLite DB receives `stickers`, `sticker_awards` and `flip_off_wagers` tables. Award decisions persist for each canonical UID/counter, including no-drop results. Physical scan, award/evolution, battle progress and settlement commit or roll back together. No reset/import is needed for an existing DB.

`GET /api/stickers?coin_name=NAME` returns public catalog, inventory, latest challenge (including returns) and battle state. `/api/flip` includes `sticker_award` and current `stickers`.

`POST /challenge/create` optionally takes `sticker_id`; signed `uid`, hexadecimal `ctr`, and `cmac` must match the challenger. `/challenge/accept` takes those credentials plus `challenge_id` and `sticker_id`; `/challenge/cancel` takes credentials plus `challenge_id`. Wagered `/challenge/yield` also requires matching credentials. Posted names cannot authorize another coin.

## Development checks

```sh
make -C ntag424_sdm_provisioner test_collectables
make -C ntag424_sdm_provisioner lint_collectables
make -C ntag424_sdm_provisioner test_sticker_ui
```

Set `CHROMIUM_PATH=/usr/bin/chromium` to use a locally installed browser instead of Playwright’s bundled Chromium.

The browser check uses a temporary database and a deterministic signed-key test seam, launches actual Chromium, and exercises the mobile album and two-coin wager flow. It does not require physical tags.

## Art production

Runtime metadata: `src/ntag424_sdm_provisioner/server/sticker_catalog.json`. Smith's creative specification: `../../agents/smith.docs/collectables_catalog.md`.

From the repository root, use `make sticker-art-manifest`, `make sticker-art-generate`, `make sticker-art-pack`, and `make sticker-art-review`. The local adapter reuses the generic generator/packer in `../recard/tools/imagegen` with an approval-respecting backend. The sibling repository is needed to regenerate images, not to run the shipped app. Raw masters and generation logs stay under ignored `build/sticker-art`; packed WebPs ship in `server/static/stickers`. Generation is resumable and stops on quota exhaustion. See `../../tools/STICKER_ART.md` for tooling details.
