# PRD §14 — Custom Coin Messages

**Status:** Approved with fixes — ready for Morpheus
**Author:** Cypher
**Date:** 2026-04-22

---

## Overview

Coin owners can set custom display text for Heads and Tails outcomes on their specific NFC tag. The canonical HEADS/TAILS event mapping is unchanged — custom messages are display-only personalization layered on top.

**Example**: ZIPPY-HAWK-720 shows "YES, AND...!" when heads flips, "NO, THANK YOU" when tails flips.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth model | CMAC + counter from last tap, validated server-side | Cryptographic proof of physical possession; taps are unique and non-replayable |
| Who sees custom message on result page | Anyone who validates a tap of that coin | It's the coin's identity — stored per coin_name, shown to any valid tapper |
| Flip Off live feed (`#live-flip-outcome`) | Custom message for YOUR coin's flips; HEADS/TAILS for opponent | Personalization is personal — you see yours, not theirs |
| Edit UI availability | Only when `coin_name` present (validated NFC tap) | UX enforced; no tap = no edit |
| Storage | New `coin_custom_messages` table | Keeps game_state schema clean |
| Recent Flips table | Canonical HEADS/TAILS always | Cross-coin consistency |
| Empty message | Reverts to "HEADS" / "TAILS" | Zero-config default |
| Character limit | 50 chars per message | Fits outcome display; prevents overflow |
| Emoji support | In scope | DB must support Unicode/wide chars |
| Concurrent edits | N/A — NFC taps are unique, cannot be replayed | No race condition possible |
| Input validation | Client-side `maxlength=50` + server-side sanitization | Defense in depth against injection |

---

## User Stories

### US-14-1: Set Custom Messages
**As** a coin owner who just validated a tap on my NFC coin,
**I want** to set a custom display message for Heads and one for Tails,
**So that** my coin shows my personalized text instead of plain "HEADS" / "TAILS" every time it's flipped.

**Acceptance Criteria:**
- [ ] After a validated NFC tap, an edit control is visible on the result page for that coin's messages
- [ ] Two fields are shown: one for Heads message, one for Tails message (each max 50 chars, emoji allowed)
- [ ] Submitting the form saves both messages to the DB under that `coin_name`
- [ ] The save request is authenticated with the `cmac` and `ctr` from the last tap; server rejects if they don't match the stored game state for that coin
- [ ] Edit fields are pre-populated with current saved messages (empty if none set) — use template context values, no separate GET needed
- [ ] A success confirmation is shown inline (no full page reload)
- [ ] If POST auth fails (stale CMAC/counter), display inline: "Tap your coin again to save changes." — not a generic error
- [ ] The edit control is NOT shown when `coin_name` is absent (error/invalid tap states)

### US-14-2: View Custom Outcome on Flip Result
**As** a coin owner who just tapped my coin,
**I want** to see MY coin's custom Heads or Tails message in the big animated outcome reveal,
**So that** my coin feels distinct and personal.

**Acceptance Criteria:**
- [ ] If the validated coin has a custom message for the current outcome, it is used as `finalText` in `showOutcome()`
- [ ] The scramble animation works correctly with the custom message (any string up to 50 chars, including emoji)
- [ ] The canonical HEADS/TAILS outcome is stored unchanged in game_state DB
- [ ] The heads/tails counter increment animation still triggers on the canonical outcome
- [ ] If no custom message is set, default "HEADS" / "TAILS" is shown

### US-14-3: Custom Messages in Flip Off Live Feed (Own Coin Only)
**As** a coin owner watching a Flip Off battle I'm in,
**I want** to see my coin's custom message in the live flip feed for my flips,
**But** see "HEADS" / "TAILS" for my opponent's flips,
**So that** personalization is mine, not imposed on others' coins.

**Acceptance Criteria:**
- [ ] In `#live-flip-outcome`, when a flip event is for `my_coin`: display the coin's custom message (if set)
- [ ] In `#live-flip-outcome`, when a flip event is for an opponent coin: display "HEADS" or "TAILS" (canonical)
- [ ] The `my_coin` context is already available on the page from the validated tap session

### US-14-4: Clear Custom Messages
**As** a coin owner, after validating a tap on my coin,
**I want** to clear one or both custom messages,
**So that** my coin reverts to showing the default "HEADS" / "TAILS" text.

**Acceptance Criteria:**
- [ ] Clearing (emptying) a message field and saving persists the empty string (treated as "use default")
- [ ] After clearing, subsequent taps of that coin show "HEADS" / "TAILS" again

### US-14-5: Messages Persist Across Sessions
**As** a coin owner,
**I want** my custom messages to be remembered after I leave the page,
**So that** I don't have to re-enter them every time I use my coin.

**Acceptance Criteria:**
- [ ] Custom messages survive server restarts (stored in SQLite)
- [ ] Subsequent taps of the same coin automatically display the stored custom messages

### US-14-6: Emoji Support
**As** a coin owner,
**I want** to use emoji in my custom messages (e.g., "🎉 YES!" / "😢 NO"),
**So that** I can express myself beyond ASCII text.

**Acceptance Criteria:**
- [ ] Emoji characters are accepted in both Heads and Tails message fields
- [ ] Emoji are stored and retrieved correctly from SQLite (database configured for Unicode/UTF-8 wide chars)
- [ ] Emoji render correctly in the `showOutcome()` scramble animation (note: scramble uses A-Z chars for unrevealed positions — emoji reveal as themselves once their index is selected)
- [ ] Emoji count toward the 50-char limit by Unicode codepoint (not byte count)
- [ ] Scramble animation uses Unicode-safe iteration (`[...str]` spread, not `.split('')`) so emoji are not broken into surrogate pairs

---

## Technical Notes (for Morpheus)

### DB
- New table: `coin_custom_messages (coin_name TEXT PRIMARY KEY, heads_message TEXT NOT NULL DEFAULT '', tails_message TEXT NOT NULL DEFAULT '')`
- SQLite connection must use `PRAGMA encoding = "UTF-8"` (likely already set; confirm)
- Use parameterized queries only — no string interpolation

### API
- `POST /coin/messages`
- Request body: `{ coin_name, heads_message, tails_message, cmac, ctr }`
- Server validates: (1) `cmac` and `ctr` match the stored last-tap game state for `coin_name`; (2) messages ≤ 50 chars each after stripping; (3) no injection
- Returns: `{ heads_message, tails_message }` on success; 401 if CMAC/counter invalid; 400 if validation fails

### Template / Server
- `app.py` fetches custom messages for the validated `coin_name` after a successful tap and passes `heads_message`/`tails_message` to the template context
- Edit form pre-populates from template context (`heads_message`, `tails_message`) — no separate GET endpoint needed

### JS
- `showOutcome(outcome, customMessage)` — use `customMessage` as `finalText` if non-empty, fall back to `outcome`
- Live feed handler: check if flip event coin matches `my_coin`; if yes, use custom message; if no, use canonical outcome

### Validation
- Client: `maxlength="50"` on both inputs; strip on submit
- Server: length check + parameterized DB write
- No HTML/script allowed (strip tags server-side)

---

## Out of Scope (§14)
- Custom messages for opponent coins in Flip Off live feed (they always show HEADS/TAILS)
- Custom messages in completed battle result cards
- Per-user authentication beyond CMAC/counter validation
- Message history / audit log
