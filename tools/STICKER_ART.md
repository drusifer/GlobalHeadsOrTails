# Sticker art production

## Rangers historical pack

Set `STICKER_PACK=rangers-history` on the existing targets to reuse the same Recard parser, resumable runner, validator and WebP packer. The sourced catalog is built by `make rangers-catalog`. Its 1,162 player families share one unique portrait across three CSS card treatments, yielding 3,486 form references. Original Twelve Clans commands remain the default.

```sh
make sticker-art-manifest STICKER_PACK=rangers-history
make MKF_ACTIVE=1 sticker-art-generate STICKER_PACK=rangers-history ART_IDS=nyr-8444933,nyr-8448095,nyr-8445529,nyr-8447400,nyr-8468685,nyr-8478550
make sticker-art-pack STICKER_PACK=rangers-history
make sticker-art-verify STICKER_PACK=rangers-history ART_IDS=nyr-8444933,nyr-8448095,nyr-8445529,nyr-8447400,nyr-8468685,nyr-8478550
make sticker-art-review STICKER_PACK=rangers-history ART_IDS=nyr-8444933,nyr-8448095,nyr-8445529,nyr-8447400,nyr-8468685,nyr-8478550
```

The sample-only verification is explicitly labeled and cannot establish pack completeness. Smith must approve the six portraits and eighteen rendered CSS cards before full generation. Remove `ART_IDS` for the complete run and final verification. Masters/logs/manifest are in `build/rangers-art`; packed assets are in `server/static/stickers/rangers-history`. Contact sheets contain at most 36 portraits each; missing images are visibly marked. Keep the old pack active until all 1,162 real portraits and 3,486 form references validate. No placeholders or duplicate bitmaps are counted as different portraits.

Browse only actually packed Rangers art with `make sticker-art-gallery STICKER_PACK=rangers-history`; the gallery binds to `0.0.0.0:8765`, supports name search and 24-family pages, and loads portraits lazily. Its counter explicitly reports completed artwork against the full roster. It is separate from the coin's owned-only Sticker Book.

`make sticker-art-references ART_IDS=all` caches public identity-reference candidates with four bounded fetch workers. Generic official silhouettes are rejected. `make rangers-reference-index` exports all 1,162 portable source/status records without copying reference photographs into shipped assets. Records with an explicit archival `source_url` act as reproducible source overrides. Use `ART_REFRESH=1` to refresh selected records, then export and rebuild the catalog. Candidate download and an era-shaped URL do not prove identity or photo era; visual review remains authoritative. Cards disclose unverified interpretations, including archival interpretation where a usable official photo is missing.

The safe backend inspects a locally cached reference when available. `make sticker-art-regenerate STICKER_PACK=rangers-history ART_IDS=nyr-ID` archives the rejected selected master/WebP before generating its replacement; active locks prevent replacement of running images. `ART_PARALLEL` accepts 1–8 workers per runner and defaults to two. Keep `MKF_ACTIVE=1` for concurrent long-running commands.

Choose the image provider with `ART_BACKEND=codex` (the default), `ART_BACKEND=nanobanana`, or `ART_BACKEND=agy`. Nano Banana calls Google's Gemini Interactions API directly, uses `GEMINI_API_KEY` from the environment, and defaults to model `gemini-nano-banana-2.1`; set `NANOBANANA_MODEL` to select another Gemini image model. It sends an audited local player portrait as an image reference when available and writes the returned PNG atomically into the same resumable Recard output directory. Never put the key in a command argument or commit it.

`ART_BACKEND=agy` uses the installed Antigravity CLI (`agy`) and does not use an AI Studio key. Headless runs use cached account credentials and account quota. The adapter requests a PNG at the exact per-sticker output path and validates it through Recard. Set `ANTIGRAVITY_MODEL` only to pin a model from `agy models`; otherwise the account default is used. Antigravity headless mode can soft-deny required tools when its permission policy does not allow them. A run without the override saw `read_file` and `command` denied and produced no artwork. If explicitly approved for a single sample, set `ANTIGRAVITY_YOLO=1`; the adapter also enables the CLI sandbox and rejects Yolo on a full-pack generation. Do not use it for production lanes. The normal production path still needs scoped Antigravity tool permissions. A quota response stops the run, and completed images remain resumable.

For long Rangers runs, `make sticker-production-start ART_LANE=forward` starts a detached eight-worker lane with a persistent log and process identity in `build/rangers-art/production-forward.*`. `make sticker-production-status` reports these managed lanes; `make sticker-production-stop ART_LANE=forward` signals only its verified process group. The optional `middle-a` and `middle-b` lanes use two workers each over catalog slices400:700 and700:900. Account for separately running interactive lanes before starting any managed lane: the reviewed production ceiling is sixteen total workers, including `ART_LANE=reverse`, the four-worker lane working from the end of the roster. Do not start a managed and interactive copy of the same lane. Starts serialize per lane, reject duplicates/quota markers, and require at least1.5GiB available RAM. These controls preserve completed images and do not clear stale image locks automatically.

On quota exhaustion, retain the marker and record the actual service reset timestamp plus remaining IDs in `build/rangers-art/quota-report.json`. `make sticker-production-clear-quota` refuses a report older than the marker, a future reset time, or a live managed lane. After expiry it archives the marker without starting generation. Verify stale image locks separately, then resume the same bounded lanes. The current blocked checkpoint and exact remaining IDs are recorded in `agents/neo.docs/rangers_art_blocker.json`; no work is scheduled automatically overnight.

After full validation and final review, `make sticker-art-activate STICKER_PACK=rangers-history` validates every expected image/reference before atomically updating the active pack registry. It rejects `ART_IDS` to prevent sample-only activation. Restart the app to refresh its immutable catalog cache. Never use this target to bypass the final artwork and UX gates.

The Twelve Clans uses 12 original fantasy clans and three evolution forms each. The creative source is `agents/smith.docs/collectables_catalog.md`; the runtime catalog includes all 36 names, lore quotes and individual prompts. Each heading has a stable `family-id` comment so renaming a clan never changes its inventory or artwork identity. Preserve those IDs when editing lore.

Run from the repository root:

Browse all 36 images with clan names and lore using `make sticker-art-gallery`, then open http://localhost:8765/ or http://YOUR-SERVER-IP:8765/ from another device. The default bind address is `0.0.0.0`; override it with `HOST=127.0.0.1` if desired. Set `PORT=8766` to use a different port. Click an image to open its full-size WebP. Only the gallery and known artwork files are exposed.

```sh
make sticker-catalog
make sticker-art-manifest
make sticker-art-generate
make sticker-art-pack
make sticker-art-verify
```

The adapter imports the adjacent recard RTG project's actual manifest parser, resumable generation runner, image validator and WebP packer. Override `RECARD_IMAGEGEN_DIR` if that project moves. It does not modify recard.

Generation uses a local `codex-safe` backend with normal `workspace-write` permissions, never recard's legacy approval/sandbox bypass flags. Requires Node, Codex CLI with an available image-generation tool, and Python 3 with Pillow for image validation/packing. Missing image-generation capability is a production blocker; no procedural or placeholder images are substituted.

Masters and individual backend logs are retained in ignored `build/sticker-art/raw`; rerunning generation skips valid completed files. Set `ART_IDS=family-id-1,family-id-2` to select forms. Quota exhaustion stops the runner; each backend invocation also has a ten-minute timeout. The exact prompt set is `build/sticker-art/manifest.json`, reproducible from the tracked catalog. Final 512px WebPs ship in `ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server/static/stickers`. The packer uses opaque ivory backgrounds; transparent output is not requested.

`sticker-art-verify` fails until all 36 production images exist and decode at the required dimensions. Do not report artwork complete based solely on a successful manifest build or a partial packing run.

For a second production lane pair, `make MKF_ACTIVE=1 sticker-art-generate ART_REVERSE=1` works from the end of the manifest. Per-image exclusive locks prevent both runners from spending generation on the same form. A hard-killed process can leave a `.lock`; `make MKF_ACTIVE=1 sticker-art-unlock ART_IDS=family-id-1` checks active backend processes before clearing the specified stale lock. Normal completion and handled failures release locks automatically.

Bob's build wrapper has one shared `build/build.out`; concurrent wrapped commands can corrupt that log. For concurrent production use `MKF_ACTIVE=1` on both generation and interim pack/review commands. Run ordinary wrapped verification after all generators finish. Per-image generation logs remain separate regardless of wrapper use.
