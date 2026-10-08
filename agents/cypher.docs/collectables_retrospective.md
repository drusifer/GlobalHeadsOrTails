# Collectables sprint retrospective — 2026-10-06

- **Neo:** Shared SQLite transactions prevent scan/reward/progress/settlement drift. Explicit borrowed-connection seams made interruption and rollback tests practical without mocking frameworks.
- **Trin:** Independent API tests caught boundary cases beyond domain tests. Keep regressions for concurrent tap replay, migrated tables, interrupted progress and the final uncommitted scan deciding a winner.
- **Morpheus:** Checking ownership alone is insufficient when the chosen match may change between an HTTP precheck and a write. Yield authorization must be enforced against the actual wager inside the transaction.
- **Oracle:** Keep the accepted rules in PRD §16, the feature runbook in COLLECTABLES.md and creative specification in Smith's catalog; index all three. Do not ship test-generated changes to a tracked runtime DB.
- **Mouse:** Artwork, not code, became the critical path. Resumable generation, exclusive image locks and safe stale-lock recovery preserved completed work after a process interruption. Concurrent mkf jobs share one log; interim art tasks bypass the wrapper using its documented MKF_ACTIVE entry until generation completes.
- **Cypher:** One question at a time clarified coin identity, rarity versus level, automatic evolution and optional fixed wagers. User delegated remaining creative decisions to Smith; those decisions were recorded before implementation.
- **Smith:** Running actual mobile UI found hidden restart controls, stale waiting copy and repeated completion overlays that static review missed. Preserve the real-browser regression script for future collection packs.

Future product tuning: review the initial 50% drop rate using real play feedback; new packs can reuse the catalog/manifest pipeline. Neither requires more scope in this sprint.
