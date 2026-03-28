# UAT Report — Flip Off UX Issues
Date: 2026-03-26

## Issue 1: CONFIRMED BUG — Blank page on "Start Flip Off"
- **Root cause:** `/challenge/create` (app.py:211) returns raw JSON `{"challenge_id": ..., "status": "pending"}, 201`
- The HTML form POSTs to that endpoint, browser renders the JSON directly → blank-looking JSON page
- **Fix needed:** Redirect to `request.referrer` or `/` after challenge creation instead of returning JSON

## Issue 2: CONFIRMED MISSING — No Yield mechanism
- `flip_off_service.py` has no yield/forfeit method. Status values: `pending, in_progress, complete, expired` — no `yielded`
- Template has no Yield button anywhere
- `expire_stale_challenges()` exists but is time-based and not user-triggered
- **Fix needed:** Add `yield_challenge(challenge_id, coin_name)` to FlipOffService + a Yield button in the active-progress section visible to both participants

## Issue 3: CONFIRMED BUG — Battle progress only visible to participants
- In app.py:196: `challenge = flip_off_service.get_latest_challenge(coin_name) if coin_name else None`
  - Only runs when a coin has been tapped; spectators get `challenge=None`
- Template condition (line 316): `{% if challenge and ... and params and params.get('Coin Name') %}`
  - Requires params (i.e., a valid coin scan), so spectators see nothing
- No method to fetch ALL active challenges at once
- **Fix needed:** Add `get_all_active_challenges()` to FlipOffService; pass `active_challenges` list to template always; render active battles section outside the `params` guard

## Issue 4: CONFIRMED — Wrong UI order
- Current order: Header → Dad Joke → Totals/Analysis → Recent Flips/Leaderboard → Flip Off sections
- Required order: Header → Dad Joke → Totals/Analysis → **Flip Off sections** → Recent Flips/Leaderboard
- Template lines 286–365 (flip-off sections) appear after lines 223–284 (Recent Flips/Leaderboard)
- **Fix needed:** Move the three Flip Off blocks (result card, active progress, launcher) above the second `tab-container` div

## Summary
| # | Issue | Status |
|---|-------|--------|
| 1 | Blank page on Start | BUG — JSON response, no redirect |
| 2 | Yield by either party | MISSING — no yield feature |
| 3 | All players see battle progress | BUG — gated behind coin scan |
| 4 | Flip Off UI above leaderboard | WRONG ORDER — easy template move |

All 4 issues confirmed. Handoff to Neo for implementation.
