# Agent Local Context

## Recent Decisions

- Added §14 Custom Coin Messages to PRD — covers form UX, CMAC auth model, 24-char limit, persistence
- Added §15 Secret Masking — documents mask_key utility and what is/isn't masked
- PRD lives at: `ntag424_sdm_provisioner/docs/PRD.md`

## Key Findings

- WHAT: PRD was last updated 2026-03-26 (through §13 Flip Off)
  - WHY: Neo implemented Custom Messages and secret masking in 2026-04-22 session; PRD needed catching up
- WHAT: Custom message auth model changed from DB-based validate_tap_auth to direct CMAC crypto
  - WHY: "Tap again" was unworkable UX — new tap opens a new page, the old cmac+ctr would be stale

## Important Notes

- §14 Definition of Done has two open items: unit tests for set_coin_messages and Trin QA sign-off
- §13 (Flip Off) still has open items: end_condition column, SSE payload standardization, yield fanfare

---
*Last updated: 2026-04-22*
