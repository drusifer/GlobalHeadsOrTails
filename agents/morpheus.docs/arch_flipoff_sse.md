# Flip-Off SSE-First Architecture

**Author:** Morpheus
**Date:** 2026-03-26
**Status:** ~~Proposed~~ **SUPERSEDED — 2026-04-22**

> **This design was replaced.** SSE was removed in favour of two-endpoint polling.
> See `agents/morpheus.docs/context.md` for the current architecture decision.
> New endpoints: `GET /api/flips/since` (cheap check) + `GET /api/state` (full payload).

---

## Problem

Three separate code paths currently update flip-off UI state:

1. **HTTP response from `/api/flip`** — includes `flip` and `challenge` fields, used directly by the flipping coin's page to insert rows and update result card
2. **HTTP response from `/challenge/yield`** — includes `challenge` field, drives `showFanfare`, `showResultCard`, and `prependRecentCompleted` directly from the fetch callback
3. **SSE events** — deliver `active_challenges` and `just_completed`, driving `renderBattles`, fanfare, result card, and `prependRecentCompleted`

This creates:
- **Race conditions** — SSE and HTTP response both process the same completion event; dedup hacks required
- **Dual processing** — yield fires `showResultCard` and `prependRecentCompleted` from both the fetch response and the SSE event
- **Inconsistent SSE payloads** — `recent_completed` is never in SSE; the history section only updates via imperative `prependRecentCompleted` calls
- **Fragile client logic** — JS must know which path delivered each piece of state and handle each differently

---

## Decision: HTTP = ACK, SSE = State

**One rule:** HTTP responses confirm success or error only. All flip-off UI state flows exclusively through SSE.

---

## Server Changes (`app.py`)

### 1. Standardize the SSE payload

Every `_push_sse` call emits the same shape:

```python
{
    "recent_flips":       [...],   # last N flips (existing)
    "totals":             {...},   # heads/tails totals (existing)
    "active_challenges":  [...],   # all pending/in_progress (existing)
    "recent_completed":   [...],   # get_recent_completed(3) — ADD THIS
    "latest_flip":        {...},   # most recent flip or None (existing)
    "just_completed":     [...],   # battles completed by this event (existing)
}
```

`recent_completed` is missing from all current pushes — add it everywhere.

### 2. Slim down HTTP responses

| Endpoint | Keep | Drop |
|---|---|---|
| `/api/flip` | `outcome`, `coin_name`, `joke`, `flip` | `challenge` |
| `/challenge/yield` | `ok: true` | `challenge` (entire field) |
| `/challenge/create` | `challenge_id`, `status` | already minimal |

The `flip` field stays in `/api/flip` — it solves the own-flip SSE race condition (your EventSource may not be registered before your flip's SSE push fires).

---

## Client Changes (`index.html`)

### 1. `renderRecentCompleted(list)` — replaces full section

Replace the imperative `prependRecentCompleted(battle)` (which appends one entry and deduplicates) with a declarative `renderRecentCompleted(list)` that rebuilds the section from the full list — same pattern as `renderBattles`.

```js
function renderRecentCompleted(battles) {
  // full replace, no dedup needed
}
```

### 2. SSE handler is the single driver

```js
evtSource.onmessage = function(event) {
  const data = JSON.parse(event.data);

  if (data.latest_flip)      showLiveFlip(data.latest_flip);
  if (data.active_challenges) renderBattles(data.active_challenges);       // hides result card if coin is now in battle
  if (data.recent_completed)  renderRecentCompleted(data.recent_completed); // full replace
  if (data.just_completed?.length) {
    showFanfare(data.just_completed[0]);
    const myBattle = data.just_completed.find(b => amInBattle(b));
    if (myBattle) showResultCard(myBattle);
  }
  // ... recent flips table, totals
};
```

### 3. Action handlers become fire-and-forget

**Yield:**
```js
async function yieldChallenge() {
  const resp = await fetch('/challenge/yield', { method: 'POST', body: data });
  const json = await resp.json();
  if (!resp.ok) { showError(json.error); return; }
  // done — SSE delivers all state updates
}
```

**Challenge create:**
```js
form.addEventListener('submit', async (e) => {
  const resp = await fetch('/challenge/create', { method: 'POST', body: data });
  const json = await resp.json();
  if (resp.ok) {
    hideForm();
    // done — SSE delivers new active battle
  } else {
    showError(json.error);
  }
});
```

No direct calls to `showFanfare`, `showResultCard`, `prependRecentCompleted`, or `renderBattles` from action handlers.

### 4. Remove

- `prependRecentCompleted` (replaced by `renderRecentCompleted`)
- `data-challenge-id` dedup logic (no longer needed)
- Direct state calls from `yieldChallenge` fetch callback

### 5. Keep

- `flip` field handling in `/api/flip` fetch (own-flip row insertion)
- `outcome`/`joke` handling from `/api/flip` (animation, joke display)
- Server-side initial render of result card and battles (first paint before SSE connects)
- `showResultCard` / `hideResultCard` (driven by SSE only, not action handlers)

---

## End Condition Type

Yield is not special — it is one of four ways a flip-off ends. All end conditions must be handled uniformly.

### The three end conditions

| Condition | Trigger | Winner |
|-----------|---------|--------|
| `win` | Both coins complete all flips, entropy differs | Higher entropy coin |
| `draw` | Both coins complete all flips, entropy equal | None |
| `yield` | One coin surrenders mid-battle | The other coin |

Note: `expired` is a **fourth end condition** — a flip-off that neither completes nor yields within 24 hours expires automatically. It has no winner. The expiry check runs lazily on each request (index + api/flip), and if anything expired, an SSE push updates all clients. The live battle display shows a countdown timer ticking down to the 24h deadline.

### DB change

Add `end_condition` column to `flip_off_challenges`:

```sql
ALTER TABLE flip_off_challenges
ADD COLUMN end_condition TEXT CHECK(end_condition IN ('win', 'draw', 'yield', 'expired'));
```

Set on completion:
- `_calculate_winner()` → `'win'` or `'draw'`
- `yield_challenge()` → `'yield'`
- `expire_stale_challenges()` → `'expired'` (24h deadline, lazy check on each request)

### SSE payload — completed challenge shape

```python
{
    "id": 42,
    "end_condition": "yield",   # "win" | "draw" | "yield" | "expired"
    "winner_coin_name": "MyCoin" | "DRAW" | None,
    "challenger_coin_name": "...",
    "challenged_coin_name": "...",
    "challenger_entropy": 7.9821,
    "challenged_entropy": 7.8104,
    "flip_count": 25,
}
```

### Client rendering — single branch on `end_condition`

All UI components (`showFanfare`, `showResultCard`, `renderRecentCompleted`) branch on `end_condition` — no inference from `winner_coin_name === 'DRAW'` heuristics:

```js
function renderEndCondition(battle) {
  switch (battle.end_condition) {
    case 'win':
      return battle.winner_coin_name === myFlipOffCoin ? 'You Won!' : `${battle.winner_coin_name} Won`;
    case 'draw':
      return '🤝 Draw!';
    case 'yield':
      return battle.winner_coin_name === myFlipOffCoin ? 'Opponent Yielded' : 'You Yielded';
  }
}
```

Fanfare also branches on `end_condition`:

```js
function showFanfare(battle) {
  if (!amInBattle(battle)) return;
  const iWon = battle.winner_coin_name === myFlipOffCoin;
  if (battle.end_condition === 'draw')    { /* draw fanfare */ }
  else if (battle.end_condition === 'yield' && !iWon) { /* you yielded — no fanfare or quiet note */ }
  else if (iWon)  { /* win fanfare */ }
  else            { /* loss fanfare */ }
}
```

### Why a type, not inference

Currently `winner_coin_name === 'DRAW'` is the only way to distinguish draw from win. Yield is identified by nothing — the client has no way to know a yield happened vs. a normal win. With `end_condition`:

- Client logic is explicit and exhaustive
- Adding a new end condition (e.g. `disqualified`) requires one branch, not a hunt through string comparisons
- The history section can show "yielded" vs "won" vs "draw" without guessing

---

## Why This Is Better

| | Before | After |
|---|---|---|
| State source of truth | HTTP response + SSE (both) | SSE only |
| Dedup logic | Required (`data-challenge-id`) | Not needed |
| `recent_completed` updates | Imperative prepend | Declarative full replace |
| Yield handler complexity | 4 direct state calls | 0 direct state calls |
| Race conditions | Present (yield fires twice) | Eliminated |
| Adding a new flip-off event | Update HTTP response + SSE handler | Update SSE handler only |
