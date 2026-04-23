# Morpheus Context

## Recent Decisions

### SSE → Polling Refactor (2026-04-22)
- **Decision**: Replace SSE with two-endpoint polling (`/api/flips/since` + `/api/state`)
- **Why**: SSE requires gevent (monkey-patching), has long-lived connection fragility, in-memory listener list can't survive restarts, race condition in client sequencing
- **Poll interval**: 3s — cheap check endpoint (`SELECT 1 ... LIMIT 1`), full state only on has_new=true
- **gevent removed**: No long-lived connections → standard WSGI workers; remove from pyproject.toml server deps

## Key Findings
- **SSE implementation spans**: app.py lines 19-40 (server), 234-273 (route), 382-385 (gevent patch), index.html lines 930-998 (client)
- **Existing render functions** in index.html are reusable as-is: `renderBattles`, `showLiveFlip`, `renderRecentCompleted`, `showFanfare`, `renderRecentFlips`
- **Timestamp format**: SQLite CURRENT_TIMESTAMP → "YYYY-MM-DD HH:MM:SS"; string comparison works for `WHERE timestamp > ?`
- **_check_expired()**: Must be called periodically — move into `/api/flips/since` handler to keep expiry firing

## Important Notes
- `just_completed` is event-based in SSE; with polling, implement `get_completed_since(ts)` on FlipOffService
- `api_flip` response shape unchanged — tap page seeded directly from flip response
- Spectator pages (no uid/ctr/cmac) seed `lastTs` from initial `GET /api/state` then poll

---
*Last updated: 2026-04-22*
