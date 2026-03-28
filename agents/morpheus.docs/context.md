# Agent Local Context

## Recent Decisions

- **2026-03-26**: Flip Off Challenge architecture complete. See `arch_flipoff.md`.
  - New `FlipOffService` class in `server/flip_off_service.py`
  - Challenge initiation on result page (post-tap), not leaderboard (Smith's fix)
  - Passive flip counting in existing validated-tap flow
  - `flip_off_challenges` DB table (new, migration safe)
  - Reuse `calculate_entropy()` with H=1/T=0 encoding

## Key Findings

- **Existing code**: `SqliteGameStateManager`, `CsvKeyManager`, `calculate_entropy()` all reused — no modification needed
- **App stack**: Flask + Jinja2. Single index route handles all validated taps. Service injection via `current_app`.
- **DB**: SQLite. Migration pattern established in `fix_db()`.

## Important Notes

- 2-phase sprint: Phase 1 = service + DB + tests. Phase 2 = routes + template + integration tests.

---
*Last updated: 2026-03-26*
