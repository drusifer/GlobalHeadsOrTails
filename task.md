# Sprint Log — 2026-04-22

## ✅ §14 Custom Coin Messages — COMPLETE
**Arch**: `agents/morpheus.docs/arch_custom_messages.md`
**PRD**: `agents/cypher.docs/custom_messages_prd.md`

All phases shipped and tested (60/60 server tests passing):
- `CoinMessageService` — SQLite-backed message store
- `POST /api/coin/messages` — CMAC-authenticated save with 24-char cap
- `/api/flip` — returns `heads_message` + `tails_message`
- Frontend — ✏️ edit form, hidden by default, expands on icon click
- Tests: `tests/test_server_coin_messages.py` (16 tests)

---

## ✅ SSE → Polling Refactor — COMPLETE
**Decision**: `ntag424_sdm_provisioner/DECISIONS.md` §5

Replaced Server-Sent Events with two-endpoint polling:
- `GET /api/flips/since?ts=<ISO>` — cheap check (`SELECT 1`, 3s poll)
- `GET /api/state?since=<ISO>` — full state snapshot (fetched only when `has_new=true`)
- Removed `gevent` from pyproject.toml server deps
- Removed `_sse_listeners`, `_push_sse`, `/api/stream/flips`, gevent monkey-patch
- Frontend: `EventSource` replaced with `setInterval` polling IIFE
- Tests: `tests/test_server_polling.py` (10 new tests)

---

## Previous Sprint
*Flip Off Challenge — 34 tests passing as of 2026-03-27*
