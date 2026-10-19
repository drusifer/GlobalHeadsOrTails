# UAT Report — Flip Off v2 (SSE + Expiry)
Date: 2026-03-26
Tester: Trin

---

## BROKEN: expire_stale_challenges signature mismatch (3 tests fail)

`expire_stale_challenges` was changed from `days=7 → int` to `hours=24 → list[dict]`.
Existing tests use the old signature and will fail:

| Test | Failure |
|---|---|
| `test_expire_stale_challenges_marks_old_as_expired` | calls `days=7`, asserts `== 1` (list != int) |
| `test_expire_stale_challenges_leaves_recent_intact` | calls `days=7`, asserts `== 0` ([] != 0) |
| `test_expire_does_not_affect_complete_challenges` | calls `days=0`, would get wrong kwarg |

**Fix needed:** Update all 3 tests to use `hours=` kwarg and `len(result)` assertions.
Also: backdating test uses `timedelta(days=10)` — should use `timedelta(hours=25)` to match new 24h window.

---

## MISSING: `recent_completed` absent from most SSE pushes

Arch doc requires every `_push_sse` call to include `recent_completed`.
Currently only `_check_expired` includes it. Missing from:
- `/api/flip` → `_push_sse`
- `/challenge/create` → `_push_sse`
- `/challenge/yield` → `_push_sse`

Client `renderRecentCompleted` will only fire on expiry events.

---

## MISSING: `renderRecentCompleted` not implemented in template

Arch doc replaces `prependRecentCompleted` with declarative `renderRecentCompleted(list)`.
Template still uses `prependRecentCompleted` with dedup logic. Not yet migrated.

---

## MISSING: `end_condition` column not in DB or service

Arch doc specifies `end_condition TEXT CHECK(end_condition IN ('win','draw','yield','expired'))`.
Neither the DB schema nor `_row_to_dict` / `_calculate_winner` / `yield_challenge` / `expire_stale_challenges` set this field yet.

---

## CONFIRMED OK: Countdown timer

- `FLIPOFF_EXPIRY_MS = 24 * 60 * 60 * 1000` correct
- `setInterval(tickCountdowns, 1000)` wired correctly
- `data-created-at` on both server-rendered and JS-rendered battle items
- `urgent` class triggers below 1 hour — correct
- Reads from `created_at` field which is present in challenge dicts

---

## CONFIRMED OK: Lazy expiry triggering

- `_check_expired` called at top of `index` and `api_flip` routes
- Returns expired list, pushes SSE only when non-empty
- `just_completed` in SSE payload will trigger fanfare for expired battles

---

## CONFIRMED OK: Yield both parties

- Server-rendered yield button: `{% if my_coin and (battle.challenger_coin_name == my_coin or battle.challenged_coin_name == my_coin) %}`
- JS-rendered: same `isMyBattle` check on both roles
- Both challenger and challenged see Yield button ✓

---

## CONFIRMED OK: UI order

- Line 268: flip-off section
- Line 406: Recent Flips / Leaderboard tab container
- Flip Offs above leaderboard ✓

---

## CONFIRMED OK: EventSource always connected

- EventSource moved outside `if (recentFlipsBody)` guard
- All clients receive SSE regardless of table presence ✓

---

## Summary

| # | Issue | Status | Owner |
|---|---|---|---|
| 1 | expire_stale_challenges tests broken | BUG | Neo (fix tests) |
| 2 | recent_completed missing from SSE pushes | MISSING | Neo |
| 3 | renderRecentCompleted not implemented | MISSING | Neo |
| 4 | end_condition not in DB/service | MISSING | Neo |
| 5 | Countdown timer | PASS | — |
| 6 | Lazy expiry | PASS | — |
| 7 | Yield both parties | PASS | — |
| 8 | UI order | PASS | — |
| 9 | EventSource always connected | PASS | — |
