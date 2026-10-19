# Smith UX Review — §14 Custom Coin Messages

**Status:** Approved with required fixes
**Date:** 2026-04-22

Overall the PRD is solid. The CMAC-as-auth model is elegant and the Flip Off live feed rule (yours shows custom, opponent shows HEADS/TAILS) is clean. Four issues to address before handing to Morpheus.

---

## Issues

### 1. BLOCKER — Emoji will break the scramble animation

**Found in**: `showOutcome()` in `index.html:845`

```js
el.innerText = finalText.split('').map((c, i) => ...)
```

`String.prototype.split('')` splits on UTF-16 code units. Emoji are surrogate pairs — `"🎉".split('')` gives two garbage characters, not one emoji. The entire scramble animation will corrupt any message containing emoji.

Also affected: `Array.from(Array(finalText.length).keys())` — `.length` returns the surrogate-pair count, so each emoji is counted as 2 unrevealed positions.

**Fix required**: Use spread operator for Unicode-safe iteration:
- `[...finalText].map(...)` instead of `finalText.split('').map(...)`
- `Array.from(Array([...finalText].length).keys())` for the index array

This must be fixed in Neo's implementation, not left as a follow-up.

---

### 2. REQUIRED — Pre-population of edit form is not optional

The Technical Notes mark the GET `/coin/messages` endpoint as "optional." It is not optional — if the form renders blank every time a coin owner re-taps, they have no idea what their current messages are and can't do partial updates safely.

**Fix**: The template already receives `heads_message` and `tails_message` from `app.py` context. Pre-fill the form inputs directly in Jinja — no separate GET endpoint needed. Remove the "optional" framing; add to US-14-1 acceptance criteria:

> - [ ] Edit fields are pre-populated with current custom messages (or empty if none set)

---

### 3. REQUIRED — Auth failure needs a user-friendly message

US-14-1 says "server rejects if they don't match" — but gives no UX spec for what the user sees. A raw 401 or a blank failure is confusing.

Context: a user might bookmark the result page and try to edit messages days later. The CMAC/counter will be stale; the POST will fail.

**Fix**: Add to US-14-1 acceptance criteria:

> - [ ] If the POST auth fails (stale CMAC/counter), the form shows an inline message: "Tap your coin again to save changes." — not a generic error

---

### 4. MINOR — Design decision wording is ambiguous

Design Decisions table: "Who sees custom message on result page: Owner who tapped that coin."

"Owner" implies only the coin's creator sees it. But the message is stored per `coin_name` and shown to anyone who taps that coin. If I lend ZIPPY-HAWK-720 to a friend, they see "YES, AND...!" too.

**Fix**: Reword to: "Anyone who validates a tap of that coin." This matches the actual behavior and the original rationale ("it's the coin's identity").

---

## Acceptance Criteria to Add

**US-14-1 additions:**
- [ ] Edit fields are pre-populated with current saved messages (empty if none set)
- [ ] If POST auth fails (stale CMAC/counter), display inline: "Tap your coin again to save changes."

**US-14-6 addition:**
- [ ] Scramble animation uses Unicode-safe string iteration (`[...str]` spread, not `.split('')`) so emoji render correctly

---

## What's Good

- CMAC+counter auth is the right call — elegant reuse of existing cryptographic proof
- "Your coin shows yours, opponent shows canonical" rule is simple and correct
- 50-char client+server double validation with SQL injection protection — well scoped
- Keeping canonical HEADS/TAILS in game_state DB unchanged is the right separation
- Emoji in scope is the right decision — these are personal expression coins

**Verdict: Approved with fixes.** The emoji bug and pre-population issue must be in the implementation spec before Neo starts. Auth failure UX is required before ship.
