# Sprint: §14 Custom Coin Messages
**Started**: 2026-04-22
**Status**: In Progress
**Arch**: `agents/morpheus.docs/arch_custom_messages.md`
**PRD**: `agents/cypher.docs/custom_messages_prd.md`

---

## Phase 1 — Backend (Python)
> Goal: `CoinMessageService` fully tested, routes wired, before any UI work.

- [ ] **P1-T1**: Create `coin_message_service.py`
  - `CoinMessageService` class following `FlipOffService` pattern
  - `_init_db()` → `CREATE TABLE IF NOT EXISTS coin_custom_messages (coin_name PK, heads_message, tails_message)`
  - `get_messages(coin_name) → (str, str)` — returns `("", "")` if not set
  - `set_messages(coin_name, heads, tails)` — `INSERT OR REPLACE`, validates `len([*msg]) ≤ 50`
  - `validate_tap_auth(coin_name, cmac_hex, ctr_hex) → bool` — queries `scan_logs` last entry for coin_name, checks cmac + counter match
  - Unit tests: `tests/test_coin_message_service.py` — all methods + auth edge cases

- [ ] **P1-T2**: Wire `CoinMessageService` into `app.py`
  - `init_managers()` → `app.coin_message_service = CoinMessageService(db_path=db_path)`
  - `index()` → read `cmac = request.args.get("cmac", "")`, fetch messages, pass `cmac`, `ctr`, `heads_message`, `tails_message` to `render_template`
  - `/api/flip` → fetch messages after recording, add `heads_message` + `tails_message` to JSON response

- [ ] **P1-T3**: `POST /api/coin/messages` route + integration tests
  - Route: parse JSON body, `validate_tap_auth`, validate codepoint lengths, `set_messages`, return 200/400/401
  - `tests/test_coin_messages_server.py`:
    - Happy path: save + retrieve messages
    - Auth failure (wrong cmac/ctr) → 401
    - Length >50 codepoints → 400
    - Missing fields → 400
    - Emoji round-trip (store + retrieve correctly)

---

## Phase 2 — Frontend (Template + JS)
> Goal: Edit form + custom outcome display + live feed, all tested.

- [ ] **P2-T1**: Edit form + `showOutcome()` refactor
  - `index.html`: `{% if coin_name %}` edit form — two text inputs pre-populated from `{{ heads_message }}`/`{{ tails_message }}`, hidden inputs for `coin_name`/`cmac`/`ctr`, `#coin-messages-status` div
  - JS block: expose `myHeadsMessage`, `myTailsMessage`, `myCmac`, `myCtr` from template via `| tojson`
  - `showOutcome(outcome, customMessage)`: use `customMessage` as `finalText` if non-empty; **emoji fix** — replace `finalText.split('')` with `[...finalText]` spread; replace `Array(finalText.length)` with `Array([...finalText].length)`
  - Update all `showOutcome()` call sites: pass `outcome === 'HEADS' ? myHeadsMessage : myTailsMessage`

- [ ] **P2-T2**: Form submit handler + live feed custom messages
  - `coin-messages-form` submit: `fetch POST /api/coin/messages`, on 200 show "Saved!" + update in-memory vars, on 401 show "Tap your coin again to save changes.", on error show "Could not save. Try again."
  - Live feed (`#live-flip-outcome`) SSE handler: if `event.coin_name === my_coin` use `myHeadsMessage`/`myTailsMessage`, else use canonical outcome

- [ ] **P2-T3**: Integration tests + regression
  - `/api/flip` response includes `heads_message` + `tails_message`
  - `index()` template context includes `cmac`, `ctr`, `heads_message`, `tails_message`
  - Emoji round-trip through API
  - All existing tests still pass: `make test_server`

---

## Done
*(previous sprint: Flip Off Challenge — 34 tests passing as of 2026-03-27)*
