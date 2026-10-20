# Collectables mobile acceptance

COMMAND: make -C ntag424_sdm_provisioner test_sticker_ui
EXPECTED: real two-coin collection/evolution/wager flow works on mobile without status or recovery ambiguity.
ACTUAL: PASS in Chromium at 390x844 using real temporary Flask/SQLite, deterministic UID validation and randomness seams; no production data used.
VERDICT: Running feature UX approved.

Validated 12 faction/36 form album; named rarity/levels; valid-tap drop and automatic 3-copy evolution reveal; exact pre-agreed copy wagers; locks; authenticated yield transfer; decline and cancellation refund; repeat offers; recovered start button/status; dismissed fanfare does not repeat at next poll; no horizontal overflow; collectables controls at least 44px; no JavaScript page errors.

Found during execution and fixed by root: start button remained hidden after match; stale waiting status and Close label after cancel; repeated polling fanfare. Rechecked fixes in real browser. Screenshot build/collectables-mobile.png visually inspected: album/art readable. Full artwork availability is separately checked after art production finishes.
