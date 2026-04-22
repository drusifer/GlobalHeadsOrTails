# Neo — Context

## Sprint §14 — Custom Coin Messages (Phase 1 Complete, 2026-04-22)

### What was built
- `coin_message_service.py`: `CoinMessageService` class with `get_messages`, `set_messages`, `validate_tap_auth`; DB table `coin_custom_messages`
- `app.py` wired: import + `init_managers()` + `index()` (reads cmac, fetches msgs, passes to template) + `/api/flip` (adds `heads_message`/`tails_message` to JSON) + new `POST /api/coin/messages` route
- `tests/test_server_coin_messages.py` — 18 tests, 52/52 total pass

### Key decisions
- Followed `FlipOffService` pattern exactly for the service file
- `validate_tap_auth` queries `scan_logs` WHERE `coin_name = ?` ORDER BY counter DESC — matches CMAC and integer counter
- Length check uses `len([*msg])` (Unicode codepoint count, emoji-safe)
- Route returns 401 `{"error": "auth_failed"}` on bad auth per PRD spec

## Previous Sprint (flipoff-not-updating fix, 2026-03-27)
- active_challenges added to /api/flip JSON response (flipoff fetch-callback fix)
- renderBattles called from fetch callback AND onmessage handler
- end_condition type: win/draw/yield/expired

## Phase 2 — NOT YET STARTED
See arch doc `agents/morpheus.docs/arch_custom_messages.md` Phase 2 section.
- Edit form in `index.html` (Jinja, shown when coin_name set)
- JS template vars + form submit handler
- `showOutcome(outcome, customMessage)` — use custom message as finalText
- Emoji-safe scramble (`[...str]` spread)
- Live feed custom message for own coin only
