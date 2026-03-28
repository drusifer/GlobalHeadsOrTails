---
name: Smith Review — PRD §13 Flip Off Challenge
type: review
date: 2026-03-26
status: approved-with-notes
---

# Smith Review: Flip Off Challenge (PRD §13)

**Decision: APPROVED with notes**

## Required Fix (pre-arch)

### Tap-Navigation Conflict
PRD §13.4 puts the "Challenge" button on the leaderboard and then asks user to tap their NFC coin in a modal. **Problem**: NFC taps navigate the browser to the coin's result URL — the modal is lost.

**Fix**: Move challenge initiation to the **result page** (after validated tap):
```
1. User taps NFC coin → validated → lands on result page
2. Result page shows "Start a Flip Off" button (only if coin valid + no active challenge)
3. User selects opponent from inline leaderboard (not their own coin)
4. Selects battle size: 10 / 25 / 50 / 100
5. Challenge created → status = pending
```
This is cleaner — challenger identity is already confirmed by the tap that brought them to the page.

---

## Minor Notes (non-blocking, pass to Morpheus/Neo)

- **UI copy**: Add brief explanation near the result — e.g. "Higher entropy = more random coin = winner (max 1.0)". Most users won't know Shannon entropy.
- **Expiry**: 30-day expiry is too long for a game feature. Recommend 7 days of inactivity.
- **Bit-encoding**: §13.5 should explicitly state that the same H=1/T=0 encoding used in `analyze_flip_sequence_randomness()` is used for challenge entropy — so Trin has a clear test target.

---

## What's Good
- Shannon entropy as winner criterion: fair, physics-driven, elegant
- Passive flip collection (reuse validated tap flow): correct technical approach
- One active challenge per coin: prevents abuse
- Battle size choice (10/25/50/100): good user agency
