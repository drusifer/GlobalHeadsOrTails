# Agent Local Context

## Recent Decisions

- **2026-03-26**: Dad Jokes feature added to PRD (section 12). Static in-code catalog, server-side random.choice(), passed to Jinja2 template. No external API dependency.
- **2026-03-26**: Flip Off Challenge feature added to PRD (section 13). Validated NFC tap initiates challenge, opponent selected from leaderboard (not own coin), 10/25/50/100 flip battle sizes, Shannon entropy determines winner. New `flip_off_challenges` DB table. Passive flip collection via existing validated tap flow.

## Key Findings
- **App stack**: Flask + Jinja2 templates. Main route in `server/app.py`, template at `server/templates/index.html`.
- **All render paths** in `app.py` call `render_template("index.html", ...)` — all paths must pass the `joke` variable.
- **Styling**: Page uses inline CSS with a blue gradient header; joke section should fit this aesthetic.

## Important Notes
- PRD is at `ntag424_sdm_provisioner/docs/PRD.md` (not `agents/` — it's in the app's own docs).
- The web page is the *game results* page (shows Heads/Tails flip outcome + stats). Dad Joke adds a fun element.
- Jokes must show even on error states (invalid CMAC, missing params, etc.).

---
*Last updated: 2026-03-26*
