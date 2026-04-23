# Agent Local Context

## Recent Decisions

- **Customize form gate**: `coin_name` (which controls the ✏️ button and form) is only set in the index route when CMAC is cryptographically valid AND `ctr_int > last_counter` (replay check). Params table still shows on any valid uid+ctr visit.
- **auth model**: Removed DB-based `validate_tap_auth`. Save endpoint (`/api/coin/messages`) now calls `key_manager.validate_sdm_url(uid, ctr_int, cmac)` directly — same crypto the flip endpoint uses. Counter still required for CMAC math but not checked against DB.
- **mask_key**: Moved to `ntag424_sdm_provisioner/log_utils.py`. Imported by `csv_key_manager.py`, `diagnostics_service.py`, and `server/app.py`.
- **Max message length**: 24 chars (was 50). Enforced in `maxlength` attr on both inputs and server-side in `set_coin_messages`.
- **UI order**: ✏️ button (right-aligned) → form (hidden by default) → params table. Form opens above params.
- **Icons**: ✏️ = open, ❌ = close (unicode emoji, not SVG or letter x).

## Key Findings

- WHAT: `validate_sdm_url` in `csv_key_manager.py` logs all 3 AES keys, session key, and full CMAC in plaintext at INFO level
  - WHY: Was debug-era logging; now all masked via `mask_key()`
- WHAT: `app.py` debug log dumped raw `validation_result` dict including `session_key` and `full_cmac`
  - WHY: Fixed by building `safe` dict with those two fields masked before logging
- WHAT: Replay detection (ctr <= last_counter) only existed in `/api/flip`, not in the index route
  - WHY: Index route now fetches `game_manager.get_state(uid_str).last_counter` and gates `tap_valid` on it

## Important Notes

- `coin_name` template var is the single gate for all customize UI: button, form, JS vars, challenge lookup, messages fetch
- `tap_valid` is a local var in the index route — not passed to template; `coin_name` being set is the signal
- `via: enabled` per PROJECT.md — use `mcp__via__via_query` for symbol lookup

---
*Last updated: 2026-04-22*
