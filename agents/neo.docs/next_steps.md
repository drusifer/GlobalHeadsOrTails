# Neo — Next Steps

## Resume Instructions
1. Read CHAT.md bottom 20 lines for context
2. Run: cd ntag424_sdm_provisioner && make test_server (34 should pass)

## Open Items
- Playwright SW tests (test_sw_nfc.py) timeout on ARM Pi — needs investigation
  or should be skipped/marked slow. SW works correctly (manually verified).

## Key Files Changed This Session
- server/app.py — added active_challenges to /api/flip response
- server/templates/index.html — renderBattles in fetch callback + onmessage order fix
- tests/test_server_flip_off_integration.py — api_flip() helper + 2 new tests

*Last updated: 2026-03-27*
