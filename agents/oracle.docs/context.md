# Oracle — Context

## Recent Decisions
- §14 implementation complete (2026-04-22): both phases done, 52/52 tests, handed to Smith for user test

## Key Findings
- §14 added `coin_message_service.py` + `POST /api/coin/messages` route + full template/JS integration
- Architecture: same shared SQLite DB, `CoinMessageService` follows `FlipOffService` pattern
- Test coverage: `tests/test_server_coin_messages.py` (18 tests)

## Important Notes
- PRD: `agents/cypher.docs/custom_messages_prd.md`
- Arch doc: `agents/morpheus.docs/arch_custom_messages.md`

---
*Last updated: 2026-04-22*
