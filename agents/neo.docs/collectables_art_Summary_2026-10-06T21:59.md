# Collectables art production

Delegated Neo art task; parent Neo owns shared persona state consolidation.

Smith approved `agents/smith.docs/collectables_catalog.md`: The Twelve Claims, 12 original RPG factions, 36 evolution forms. Generated runtime catalog preserves names, quotes, family looks and prompt set at nested `server/sticker_catalog.json`.

`tools/sticker_art.mjs` imports the requested adjacent recard RTG modules for manifest parsing, resumable generation, dimension validation and WebP packing. It registers a safe local Codex backend with normal workspace sandbox permissions; neither recard's approval bypass flags nor sibling edits are used. Local adapter logs individual child output, limits generation to two concurrent images and times out each child after ten minutes.

Public root Makefile targets: `sticker-catalog`, `sticker-art-manifest`, `sticker-art-generate`, `sticker-art-pack`, `sticker-art-verify`, `sticker-art-review`. Manifest and normal make wrapper passed. First Hearth Recruit and Lantern Captain production artworks inspected: correct fantasy style, warm ochre/copper palette, kettle crest, clear equipment evolution and no text.

Production COMPLETE at 22:11 UTC: 36 actual painted raster masters and 36 packed 512px WebPs. `make sticker-art-pack sticker-art-verify sticker-art-review` passed; packer reported36/36 and dimension/decode validator36/36. Full contact sheet inspected: all12 factions distinct, all3 evolution forms visibly escalate, no glaring artifacts or embedded labels. Smith has been notified for independent final visual approval.

Production was expanded safely to four concurrent workers using forward and reverse manifests plus per-image exclusive locks. The original supervised process was environmentally terminated after19 completions; all finished masters were preserved. Guarded `sticker-art-unlock` verified absent backend owners before removing only its two stale Velvet locks. The resumed forward runner finished with4 successful/32 skipped/zero failures; reverse runner finished14 successful/22 skipped/zero failures. No quota exhaustion. Completed shared forms are credited successful to waiting runners, without duplicate generation.

Root mkf's shared build log cannot support concurrent wrapped targets: truncation during a running wrapped generator temporarily caused null padding and a chat-post error. Interim tasks used `make MKF_ACTIVE=1`; final ordinary wrapped targets passed after all generators exited. Isolated per-image logs were unaffected. Production instructions document concurrent operation and stale-lock recovery.

Rerun `make sticker-art-generate` to resume safely; valid existing masters are skipped. Then `make sticker-art-pack sticker-art-verify sticker-art-review` and inspect `build/sticker-art/review.jpg`.

Final app-bound assets: `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/static/stickers/<family-id>-<level>.webp`. Masters, logs and manifest remain in ignored `build/sticker-art`. Full production instructions: `tools/STICKER_ART.md`.
