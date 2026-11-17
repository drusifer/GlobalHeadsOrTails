# Collectables sprint — The Twelve Clans

## Scope and acceptance criteria

1. Each coin owns a persistent DB collection; every genuine validated, non-test flip independently has a 50% award chance, including Flip Off flips. Invalid/replayed requests do not award. Updated user decision: developer test Heads/Tails flips also use normal sticker odds and evolution, with a separate idempotency namespace. Award decisions are idempotent for tag UID/counter, including no-drop decisions.
2. Conditional drop rarity weights: Common 60%, Uncommon 25%, Rare 12%, Legendary 3%; uniform family selection within tier. All drops begin level 1. Three unlocked copies of one family and level combine automatically into one next-level copy, cascading to level 3; rarity unchanged. Level-3 duplicates remain.
3. Twelve RPG factions, distributed 5/4/2/1 by rarity, have distinct looks and three named forms, original narrative quotes and 36 distinct illustrations. Creative reference: agents/smith/collectables_catalog.md. Reuse adjacent recard RTG art-generation/packing scripts.
4. Sticker Book appears beside Recent Flips and Leaderboard using existing tab styles. Season description appears without a tap; only currently owned forms display for the tapped coin, with locked copies, progress, rarity and level as text. Drops and automatic evolution are explained immediately. Mobile controls meet 44px targets.
5. Optional Flip Off wagers: challenger chooses one exact copy and offers it, challenged coin sees the offered copy and chooses its own before accepting. Neither stake can change after offer/acceptance; no wager match progress before acceptance. Both identities are authenticated using valid coin tap CMAC; ownership is resolved server-side.
6. Stake locks prevent further wagers/evolution. Winner receives both, including a yield after acceptance. Draw, cancellation, decline and expiry return originals. Settlement is atomic and exactly once, followed by evolution of unlocked holdings. Pending offer yield cancels rather than forfeits an unaccepted stake.
7. Existing non-wager Flip Off behavior remains supported. Collection and wager status refresh while waiting even when no new flip occurs.

## Architecture (Morpheus)

Oracle consultation: existing Oracle context documents SQLite persistence and polling; no memory.md or lessons.md exists. Keep standard WSGI and SQLite; no new service/infra. Inventory uses individual immutable copy IDs, family+level and lock challenge ID. Award ledger provides per-UID/counter idempotency. Wager terms and challenge terminal state share one SQLite write transaction; BEGIN IMMEDIATE serializes ownership changes. Catalog ships with app. New collection endpoint and wager actions integrate existing page; authenticated mutations never trust submitted coin_name.

Smith explicitly approved story and architecture gates with acceptance notes in the creative catalog. Running-app validation remains required.

## Phases (Mouse, reviewed by Morpheus)

- Phase 1: catalog/art pipeline; persistent award/evolution service; deterministic domain tests.
- Phase 2: atomic optional wager lifecycle; authenticated API integration; integration/security tests.
- Phase 3: album/reveal/mobile wager UI; actual browser verification; packed artwork, documentation and sprint close.

Deployment is outside this sprint; prepare and validate local changes only.
