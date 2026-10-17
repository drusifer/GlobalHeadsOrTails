# Optional Nano Banana artwork provider

User asked to add Nano Banana as an alternative to Codex image generation after the 478/1,162 Rangers artwork Codex quota block.

- `ART_BACKEND=codex` remains the default; `ART_BACKEND=nanobanana` calls Google's Gemini Interactions API directly from the Recard-compatible per-image backend.
- Default model: `gemini-nano-banana-2.1`; optional `NANOBANANA_MODEL`. API key is read only from `GEMINI_API_KEY`; no key file, added dependency, or generation was used. Output PNG is atomically written into existing raw/resumable path; cached identity portrait is sent as image input when available; existing packer still handles WebP.
- Detached `sticker-production-start` carries `ART_BACKEND` and permits using the other independent provider despite its quota report. Same-provider quota markers retain reset guards; Codex default behavior is preserved.
- Usage: export `GEMINI_API_KEY`, then `make ART_BACKEND=nanobanana sticker-art-generate STICKER_PACK=rangers-history`; for detached lane `make ART_BACKEND=nanobanana sticker-production-start ART_LANE=forward`.
- Per user request, no external Gemini API request or tests were run. Only inspect code / official Google documentation. Google current docs report no free tier for Nano Banana 2.1 standard, $0.0336 per 1K output image; remaining684 portraits would cost about$22.98 output alone plus input/reference charges.
- Original Rangers sprint remains quota-blocked at478/1162; Twelve Clans active. Resume checkpoint and exact missing IDs in `rangers_art_blocker.json`. Codex reset Oct8 22:44ET. No worker running.
