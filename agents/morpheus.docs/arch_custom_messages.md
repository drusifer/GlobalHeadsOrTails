# Architecture — §14 Custom Coin Messages

**Author:** Morpheus
**Date:** 2026-04-22
**PRD:** `agents/cypher.docs/custom_messages_prd.md`

---

## System Component Map

### Existing (relevant)

```
app.py
├── init_managers(app, key_csv_path, db_path)
│   ├── app.key_manager    = CsvKeyManager
│   ├── app.game_manager   = SqliteGameStateManager  ← data/app.db
│   └── app.flip_off_service = FlipOffService        ← data/app.db (same file)
│
├── GET /              → index() — renders page, passes template context
├── GET /api/flip      → validates CMAC, records flip, returns JSON
├── GET /api/stream/flips → SSE stream
└── POST /api/flipoff/yield
```

### New (§14)

```
NEW: CoinMessageService                              ← data/app.db (same file)
├── get_messages(coin_name) → (heads_msg, tails_msg)
├── set_messages(coin_name, heads_msg, tails_msg)
└── validate_tap_auth(coin_name, cmac_hex, ctr_hex) → bool
    └── SELECT cmac, counter FROM scan_logs
        WHERE coin_name=? ORDER BY counter DESC LIMIT 1
        → stored_cmac == cmac_hex AND stored_counter == int(ctr_hex, 16)

app.py changes:
├── init_managers() → add app.coin_message_service = CoinMessageService(db_path)
├── index()         → read cmac from URL args; fetch messages; pass to template
├── /api/flip       → fetch messages after recording; add to JSON response
└── NEW: POST /api/coin/messages
        → validate_tap_auth → set_messages → return JSON

index.html changes:
├── Edit form (Jinja, hidden when no coin_name)
│   ├── Pre-populated from template context
│   └── Hidden inputs: cmac, ctr
├── showOutcome(outcome, customMessage) — uses customMessage if set
├── [...str] spread fix for emoji in scramble
└── Live feed handler — apply custom msg for own coin, canonical for opponent
```

---

## Data Model

```sql
-- New table in data/app.db
CREATE TABLE IF NOT EXISTS coin_custom_messages (
    coin_name     TEXT PRIMARY KEY,
    heads_message TEXT NOT NULL DEFAULT '',
    tails_message TEXT NOT NULL DEFAULT ''
);
```

SQLite stores TEXT as UTF-8 by default. Emoji are stored correctly with no PRAGMA changes needed (SQLite 3.x uses UTF-8 by default for TEXT columns).

---

## Data Flows

### Setting messages
```
NFC URL: /?uid=X&ctr=Y&cmac=Z
  → index() renders page with cmac+ctr in hidden form inputs

User fills edit form → JS submits:
  POST /api/coin/messages
  Body: {coin_name, heads_message, tails_message, cmac, ctr}
  
  → CoinMessageService.validate_tap_auth(coin_name, cmac, ctr)
      SELECT cmac, counter FROM scan_logs
      WHERE coin_name=? ORDER BY counter DESC LIMIT 1
      → match? → proceed / no match? → 401
  → server-side validation: strip tags, len([...msg]) ≤ 50 each
  → CoinMessageService.set_messages(coin_name, heads_msg, tails_msg)
  → return {heads_message, tails_message} 200
  → JS shows "Saved!" inline / "Tap your coin again to save changes." on 401
```

### Displaying custom message on flip
```
GET /api/flip?uid=X&ctr=Y&cmac=Z
  → validates CMAC (existing)
  → records flip (existing)
  → coin_message_service.get_messages(coin_name)
  → return {outcome, coin_name, ..., heads_message, tails_message}

JS: showOutcome(outcome, outcome === 'HEADS' ? heads_message : tails_message)
  → finalText = customMessage || outcome
```

### Flip Off live feed (own coin)
```
SSE event arrives: {latest_flip: {coin_name, outcome, ...}}
JS already has: my_coin (from template context, set at page render)

if (event.coin_name === my_coin) {
    displayText = outcome === 'HEADS' ? myHeadsMessage : myTailsMessage || outcome
} else {
    displayText = outcome  // canonical HEADS/TAILS for opponent
}
```

`myHeadsMessage` and `myTailsMessage` are JS vars set from template context at page load.

---

## New File: `coin_message_service.py`

Follows `FlipOffService` pattern exactly:

```python
class CoinMessageService:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self): ...
    def _init_db(self): ...  # CREATE TABLE IF NOT EXISTS

    def get_messages(self, coin_name: str) -> tuple[str, str]:
        """Returns (heads_message, tails_message). Empty strings if not set."""

    def set_messages(self, coin_name: str, heads_message: str, tails_message: str) -> None:
        """UPSERT coin_custom_messages. Strips whitespace, validates length."""

    def validate_tap_auth(self, coin_name: str, cmac_hex: str, ctr_hex: str) -> bool:
        """Returns True iff coin_name's last scan_logs entry matches cmac and counter."""
```

---

## app.py Changes

### `init_managers()`
```python
from ntag424_sdm_provisioner.server.coin_message_service import CoinMessageService
app.coin_message_service = CoinMessageService(db_path=db_path)
```

### `index()` — add to existing reads
```python
cmac = request.args.get("cmac", "")
# ... existing coin_name lookup ...
msgs = current_app.coin_message_service.get_messages(coin_name) if coin_name else ("", "")
# pass to render_template: cmac=cmac, ctr=ctr, heads_message=msgs[0], tails_message=msgs[1]
```

### `/api/flip` — extend JSON response
```python
msgs = current_app.coin_message_service.get_messages(coin_name) if coin_name else ("", "")
return {
    "outcome": ..., "coin_name": ...,
    "heads_message": msgs[0], "tails_message": msgs[1],
    ...
}, 200
```

### New route: `POST /api/coin/messages`
```python
@app.route("/api/coin/messages", methods=["POST"])
def set_coin_messages():
    data = request.get_json(silent=True) or {}
    coin_name = data.get("coin_name", "").strip()
    cmac = data.get("cmac", "").strip()
    ctr = data.get("ctr", "").strip()
    heads = data.get("heads_message", "").strip()
    tails = data.get("tails_message", "").strip()

    if not coin_name or not cmac or not ctr:
        return {"error": "Missing required fields"}, 400

    svc = current_app.coin_message_service
    if not svc.validate_tap_auth(coin_name, cmac, ctr):
        return {"error": "auth_failed"}, 401

    # validate lengths (Unicode codepoint count)
    if len([*heads]) > 50 or len([*tails]) > 50:
        return {"error": "Message exceeds 50 characters"}, 400

    svc.set_messages(coin_name, heads, tails)
    return {"heads_message": heads, "tails_message": tails}, 200
```

---

## Template Changes (`index.html`)

### Edit form (Jinja)
```html
{% if coin_name %}
<form id="coin-messages-form" ...>
  <input type="hidden" name="coin_name" value="{{ coin_name }}">
  <input type="hidden" name="cmac" value="{{ cmac }}">
  <input type="hidden" name="ctr" value="{{ ctr }}">
  <input type="text" name="heads_message" maxlength="50" value="{{ heads_message }}">
  <input type="text" name="tails_message" maxlength="50" value="{{ tails_message }}">
  <button type="submit">Save</button>
</form>
<div id="coin-messages-status"></div>
{% endif %}
```

### JS — template vars passed to JS scope
```html
<script>
  const myHeadsMessage = {{ heads_message | tojson }};
  const myTailsMessage = {{ tails_message | tojson }};
  const myCmac = {{ cmac | tojson }};
  const myCtr = {{ ctr | tojson }};
</script>
```

### `showOutcome()` fix
```js
// Before: finalText.split('').map(...)
// After:
const chars = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'];
const finalChars = [...finalText];  // Unicode-safe
const unrevealedIndices = Array.from(Array(finalChars.length).keys());
// ... rest of animation uses finalChars[i] instead of finalText[i]
```

---

## Sprint Phases

### Phase 1 — Backend (Python)
1. New file: `coin_message_service.py` — `CoinMessageService` with `_init_db`, `get_messages`, `set_messages`, `validate_tap_auth`
2. Wire into `init_managers()` in `app.py`
3. Extend `index()` to read `cmac` and fetch messages; pass to template context
4. Extend `/api/flip` JSON response with `heads_message`, `tails_message`
5. New route `POST /api/coin/messages`

### Phase 2 — Frontend (Template + JS)
1. Edit form in `index.html` (Jinja-rendered, shown when `coin_name` set)
2. JS template vars: `myHeadsMessage`, `myTailsMessage`, `myCmac`, `myCtr`
3. JS form submit handler (fetch POST, inline success/401 UX)
4. `showOutcome()` — add `customMessage` param, use it as `finalText`
5. `showOutcome()` — fix `[...str]` spread for emoji-safe scramble
6. Live feed handler — apply own coin's custom message

---

## Binding Decisions

1. **`CoinMessageService` as separate class** — SRP. Does not extend `SqliteGameStateManager`.
2. **Same `data/app.db` file** — no multi-DB complexity; consistent with `FlipOffService`.
3. **CMAC auth via `scan_logs` lookup** — no new columns; reuses already-stored data.
4. **`cmac` captured in `index()`** — passed through template as hidden field; not re-validated at page load (validation only on `POST /api/coin/messages`).
5. **Unicode codepoint length check** — `len([*msg])` in Python (equivalent to `[...str].length` in JS).
6. **UPSERT pattern** — `INSERT OR REPLACE INTO coin_custom_messages` for `set_messages()`.
