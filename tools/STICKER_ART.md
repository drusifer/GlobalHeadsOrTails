# Sticker art production

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
