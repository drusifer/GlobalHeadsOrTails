# Trin Context

## Recent Decisions
- Run tests from `ntag424_sdm_provisioner/` subdir using `make test_server`
- Root `make test` is broken (Makefile.prj deleted) — do not use it

## Key Findings
- **All 50 server tests pass** — Neo's coin_message + CMAC auth changes are clean
  - No test fixes were needed
- **Test command**: `cd ntag424_sdm_provisioner && make test_server`
  - Covers: test_server_coin_messages.py, test_server_flip_off.py, test_server_flip_off_integration.py, test_server_logic.py

## Important Notes
- CoinMessageService tests (§14) fully cover: get/set messages, whitespace strip, upsert, 24-char cap, emoji, auth via CMAC mock
- api/flip now returns heads_message and tails_message in response payload
- PRD §14 and §15 documented by Cypher — Trin QA sign-off complete

---
*Last updated: 2026-04-22*
