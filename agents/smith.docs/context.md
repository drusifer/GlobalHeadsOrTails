# Smith context

## Recent Decisions
2026-10-06: Collectables Gates 1 and 2 approved with notes in collectables_catalog.md. Design approval only; actual UI gate pending.
Launch pack The Twelve Claims: 12 original fantasy factions, 5 Common/4 Uncommon/2 Rare/1 Legendary, 36 named forms and lore quotes. Art via adjacent recard RTG scripts.
Coin-only ownership; independent 50% drop on every valid flip, including Flip Off. Conditional rarity 60/25/12/3. Level-1 drops, automatic unlocked 3:1 evolution up to level 3, fixed rarity, duplicates allowed.
Optional pre-agreed wagers: winner keeps both, ties/cancel return originals. Locked copies cannot evolve or be reused.

## Key Findings
Architecture approved: individual inventory IDs, atomic transactions, challenge locks, CMAC-bound mutations, once-only settlement. Challenger fixed offer is their consent; opponent sees both exact forms/levels and selects own stake before acceptance. Terms immutable or changes clear acceptance. No challenge flips score before acceptance. Unlock/transfer can trigger evolution with visible explanation.
UI distinguishes rarity from level, shows counts and locks, explains 3-copy consumption and loss risk, and uses labeled mobile controls at least 44px tall. 50% never promises a drop every second flip.

## Important Notes
No running-app usability approval claimed. Prior mobile opponent selector truncation/small targets/input zoom feedback remains relevant. Catalog: agents/smith.docs/collectables_catalog.md.
Last updated: 2026-10-06

## Running-app acceptance 2026-10-06
Actual make -C ntag424_sdm_provisioner test_sticker_ui passed in mobile Chromium (390x844), temporary real Flask/SQLite, deterministic credential validation/RNG seams. Verified 12 families/36 forms, initial drop, signed third-tap 3:1 evolution reveal, exact wager consent, locks, signed yield winner receives both, decline/cancel unlock, repeated offers, cleared stale status, restored start label, no repeated fanfare after dismiss/poll, no horizontal overflow, collectable controls >=44px, no JS errors. Screenshot ntag424_sdm_provisioner/build/collectables-mobile.png inspected; artwork and text legible. Root fixed missing restart control, stale waiting/Close copy and repeated fanfare discovered during testing. Running-feature UX approved; full 36 image availability remains artwork-production check.

## Final artwork QA 2026-10-06
Smith visually inspected refreshed complete build/sticker-art/review.jpg (36/36). All12 families distinct through archetype, palette, emblem and silhouette; each3-form sequence visibly gains equipment, scale or magical ornament. Tideglass is subtler but fins/crown/ornament progress consistently. No glaring anatomy/render artifacts or embedded labels/watermarks visible in full sheet. Catalog preserves original Twelve Claims narrative and lore quotes. Art agent reports make sticker-art-pack sticker-art-verify sticker-art-review exit0,36/36 decoded minimum512px. Final Smith art gate APPROVED.
