# Trin Context

## Collectables QA — 2026-10-06
- Confirmed requirements from user discussion and Smith catalog. Coin owns copies; 50% eligible real-tap drops, four rarities, 3:1 unlocked evolution to level3; optional pre-agreed locked Flip Off stakes.
- 107 server tests pass via make -C ntag424_sdm_provisioner test_collectables. Added independent API file tests/test_server_sticker_api.py (22 tests), plus borrowed transaction and settlement evolution regressions.
- SignedKeys fixture is a simple deterministic valid/invalid validation seam and uses UID.uid (UID.__str__ is descriptive). Crypto algorithm independently covered elsewhere; these tests verify endpoint authorization, not CMAC primitive mathematics.
- Discovered and resolved with root: raw-case UID replay, malformed JSON crashes, scan/drop/progress separate-transaction crash gap. Borrowed connections ensure rollback all scan/drop/progress/terminal stake updates. Final uncommitted HEADS tap determines entropy winner in full API regression.
- Inventory decoration caches immutable catalog and omits art prompts. Wager evolution_events migration persists consumed-copy explanation; optional include_expired exposes returned/cancelled state for album.
