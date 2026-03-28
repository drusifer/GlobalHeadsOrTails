# Neo — Context

## Recent Decisions
- Flip-off SSE-first architecture adopted (see agents/morpheus.docs/arch_flipoff_sse.md)
- expire_stale_challenges changed from days=7/int to hours=24/list[dict]
- EventSource moved outside recentFlipsBody guard — always connected
- tickCountdowns setInterval added for live expiry countdown
- end_condition type decided: win/draw/yield/expired
- active_challenges added to /api/flip JSON response (flipoff fetch-callback fix)
- renderBattles now called from fetch callback AND onmessage handler

## Key Findings
- app.py: _check_expired() helper wired to index + api_flip routes
- flip_off_service.py: get_all_coin_stats() added for W/L/D leaderboard
- index.html: renderBattles, showResultCard, hideResultCard, showFanfare, prependRecentCompleted present — SSE-first migration complete
- Root cause of flipoff-not-updating: fetch callback updated recent flips directly from /api/flip response, but flipoff ONLY updated via SSE. On mobile NFC tap (fresh page nav), SSE can be missed/delayed.
- Fix: added active_challenges to /api/flip response; fetch callback now calls renderBattles directly
- Fix: renderBattles moved before showLiveFlip in onmessage so hasActiveChallenges is accurate when showLiveFlip runs

## Important Notes
- Tests: 34/34 pass (added 2 new integration tests for /api/flip challenge counting)
- api_flip integration tests: test_api_flip_increments_challenge_flip_count, test_api_flip_response_includes_active_challenges
- NOTE: test mode (drew_test_outcome) still does NOT increment challenge flip counts — this is intentional

---
*Last updated: 2026-03-27*
