# Agent Local Context

## Recent Decisions

- **2026-04-22**: Approved §14 Custom Coin Messages with required fixes. See `smith.docs/review_custom_messages.md`.

## Key Findings

- **Emoji + scramble animation bug**: `showOutcome()` uses `finalText.split('')` which breaks emoji into UTF-16 surrogate pairs. Must use `[...finalText]` spread for Unicode-safe iteration. Affects both the map and the index array length calculation.
- **Form pre-population**: Should use Jinja template context (`heads_message`, `tails_message`) — no separate GET endpoint needed. Marked "optional" in original PRD, corrected to required.
- **Auth failure UX**: CMAC/counter stale on old result pages. Error must say "Tap your coin again to save changes." — not a generic 401.
- **Design decision ambiguity**: "Owner who tapped" was ambiguous — corrected to "anyone who validates a tap of that coin." Custom message is per coin_name, not per user.

## Important Notes

- Flip Off live feed rule (US-14-3): your coin's flips → custom message; opponent's flips → HEADS/TAILS. The custom message is already in client context from the validated tap, no SSE changes needed.
- The 50-char emoji limit should be counted by Unicode codepoint using `[...str].length`, not `str.length`.

---
*Last updated: 2026-04-22*
