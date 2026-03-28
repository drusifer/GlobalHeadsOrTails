# UAT Report — Flip Off User Stories (PRD §13.2, §13.9)
Date: 2026-03-26
Tester: Trin

---

## US-1: Start a challenge — PASS

- Flip Offs section present for all visitors ✓
- "+ Start Flip-Off" button shown to coin owners not in active battle ✓
- JS fetch (no navigation) ✓
- Opponent list sorted alphabetically, excludes own coin ✓
- Shows flip count + entropy per opponent ✓
- Battle sizes 10/25/50/100 ✓
- Self-challenge blocked server-side ✓
- Duplicate challenge blocked server-side ✓
- New battle appears for all viewers via SSE ✓

---

## US-2: Track progress in real time — PASS

- Progress bars and flip counts in battle items ✓
- `renderBattles` called from SSE handler ✓
- EventSource always connected (not gated on recentFlipsBody) ✓
- Live flip indicator only shown during active battles ✓

---

## US-3: See the result — PARTIAL

- Result card shown on page load for most recent completed battle ✓
- `showResultCard` called from SSE `just_completed` ✓
- Entropy scores, coin names shown ✓
- Card hidden when coin enters new active battle ✓
- **FAIL**: No distinction between yield and entropy win in result card text — both show "X Won". PRD §13.9 blocking item.

---

## US-4: Yield — PARTIAL

- Yield button visible to both challenger and challenged ✓
- `/challenge/yield` endpoint works ✓
- Opponent wins immediately ✓
- Result card shown after yield ✓
- **FAIL**: `showFanfare` does not distinguish yield from entropy loss. Both show `😔 X Won`. PRD §13.9 blocking item.
- **FAIL**: Result card `showResultCard` uses `winner_coin_name` only — no yield-specific text. Same blocking item.

---

## US-5: Expiry countdown — PASS with minor gap

- `tickCountdowns` runs via `setInterval(tickCountdowns, 1000)` ✓
- Countdown formula correct: `created_at + 24h - now` ✓
- Urgent (red) class applied inside final hour ✓
- `data-created-at` on both server-rendered and JS-rendered battle items ✓
- **MINOR**: `tickCountdowns` not called on page load — expiry divs show blank for first second. Fix: call once in DOMContentLoaded.

---

## US-6: Leaderboard record — PASS

- W/L/D columns in leaderboard table ✓
- `get_all_coin_stats()` on FlipOffService ✓
- Passed to template as `flip_off_stats` ✓
- Counts all completed challenges regardless of end condition ✓

---

## US-7: Recent results as spectator — PARTIAL

- Server-rendered `recent_completed` shown to all visitors (no coin required) ✓
- `prependRecentCompleted` called from yield handler and SSE `just_completed` ✓
- **FAIL**: `recent_completed` missing from SSE payloads in `/api/flip`, `/challenge/create`, `/challenge/yield`. Only present in `_check_expired` push. Recent results section goes stale for non-expiry completions on other viewers' screens. PRD §13.9 blocking item.

---

## Exit Criteria — §13.9 Blocking Items

| # | Criterion | Status |
|---|---|---|
| 1 | All unit tests pass | PASS — expiry tests fixed in previous UAT |
| 2 | `end_condition` column added and set correctly | FAIL — not implemented |
| 3 | `recent_completed` in all SSE payloads | FAIL — only in `_check_expired` |
| 4 | Recent results update via SSE on every end condition | FAIL — same as #3 |
| 5 | Expired challenges marked within one request cycle | PASS — `_check_expired` in index + api_flip |
| 6 | Fanfare distinguishes yield from entropy win/loss | FAIL — both show "X Won" |
| 7 | QA sign-off | BLOCKED — items 2, 3, 4, 6 outstanding |

---

## Additional Defects

**DEF-1 (minor)**: `tickCountdowns` not called on DOMContentLoaded — 1-second blank on expiry divs.
```js
// Add to DOMContentLoaded block:
tickCountdowns();
```

**DEF-2 (dead code)**: `const rowClass = isDraw ? 'draw-row' : '';` in `prependRecentCompleted` — declared but never used.

---

## Summary

| Story | Result |
|---|---|
| US-1 Start challenge | PASS |
| US-2 Real-time progress | PASS |
| US-3 See result | PARTIAL — no yield distinction |
| US-4 Yield | PARTIAL — fanfare/card don't distinguish yield |
| US-5 Expiry countdown | PASS (minor gap) |
| US-6 Leaderboard W/L/D | PASS |
| US-7 Recent results spectator | PARTIAL — SSE updates missing |

**Blocking for sign-off**: end_condition column, SSE payload standardization, yield fanfare text.
