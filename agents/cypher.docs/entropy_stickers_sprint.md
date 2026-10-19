# Entropy-weighted sticker awards — 2026-10-07

Status: COMPLETE, workspace release2026-10-07. Smith story, architecture and actual running-browser gates approved; Morpheus code and Oracle documentation approved. 126 server tests, syntax checks and extended mobile browser acceptance pass. No build, commit or deployment requested.

## Product stories

1. As a coin owner, I want sticker odds to reflect my coin's entropy and monobit p-value, so balanced real flip histories have the best odds. Collection ownership and history aggregate by coin name across both face UIDs. Maximum chance remains 50%; rarity and evolution remain unchanged.
2. As a new coin owner, I want to earn stickers before collecting enough flips for the monobit test. Entropy applies immediately; before 100 actual flips, the unavailable p-value contributes a neutral multiplier. A proposed 5% minimum prevents streaks/new coins from having no chance.
3. As a player, I want the instructions to say “Flip your real coin and tap the face that lands for the best sticker odds.” Explain that repeated same-side outcomes reduce odds, odds vary up to 50%, and short histories do not yet have a monobit score. Do not claim these two balance metrics prove physical randomness or detect intentional alternating outcomes.
4. As a developer, I want existing test Heads/Tails taps to continue awarding stickers under the same weighting policy, without changing genuine statistics. Replay decisions remain persisted once per UID/counter; invalid taps award nothing.

## Proposed policy

For actual count n and Heads proportion h/n, compute Shannon entropy H=-8*(q*log2(q)+(1-q)*log2(1-q)), with H=0 for a one-sided history. No byte padding. At n>=100 compute monobit p=erfc(abs(heads-tails)/sqrt(2*n)); otherwise p is unavailable and p_weight=1. Proposed chance = 0.5 * max(0.1, (H/8)*p_weight), bounded to [0.05,0.5]. The 5% floor and provisional p-value policy are game-design choices, not NIST statistical claims. Empty history should occur only outside an eligible recorded flip; defensively return the minimum chance. Root may choose a different documented floor after Smith review.

Examples: one-sided history yields 5%; balanced mature history yields 50%; H=7.2,p=0.5 yields22.5%; before100 flips,H=7.2 yields45%. Reaching100 activates the p-value multiplier; communicate that warm-up policy rather than presenting an unavailable p-value as an observed1.0.

## Architecture proposal (Morpheus)

Add sticker_odds.py with pure calculate_sticker_odds(heads,tails) and transaction-aware coin_sticker_odds(conn,coin_name,include_test). Read exact outcome counts from scan_logs filtered by coin_name and Heads/Tails, using the borrowed award transaction after inserting the current flip. Genuine eligibility includes only is_test IS FALSE; test eligibility uses test-inclusive history and the existing test:UID ledger namespace. Both face UIDs contribute to the same coin history and collection. Do not reuse analyze_flip_sequence_randomness's byte-padded output: it adds synthetic tails and can run the monobit test before100 actual observations. Existing leaderboard and battle metrics stay unchanged in this sprint.

Unify valid test and genuine persistence through record_validated_flip with optional is_test=False: test-ledger replay returns prior result before scan insertion; fresh test scan, scoring and award share a transaction and skip Flip Off progression. Genuine taps retain replay rejection and real-only statistics. This fixes duplicated test scans influencing score on refresh.

Persist the computed odds alongside the drop/no-drop result in the existing award JSON. Replays return the persisted decision, never recalculate or reroll after subsequent history. Existing ledger rows remain readable without new fields. The server calculates all weights; client parameters cannot override odds. Score computation and drop use one consistent snapshot. Preserve atomic scan/replay/award/evolution/Flip Off settlement.

## Two short phases

1. Backend: implement exact-count scoring and weighting, real/test history selection, persisted odds metadata. Verify known balanced/biased values, actual99/100 boundary, UID aggregation, current-flip inclusion, score bounds and persisted replay. Preserve rarity/evolution/wager behavior. Hand off Neo -> Trin -> Morpheus.
2. UX/documentation: replace flat50% claims with variable odds ceiling, real-flip guidance and warm-up/floor explanation in current instructions, sticker book and feature requirements. Preserve tapped-coin-only album and existing tab styling. Verify real browser and current server regression target. Smith approves actual experience; Oracle records policy; Mouse closes sprint. No automatic commit, build, push or deployment is implied by this new sprint.

## Consultation

Read Oracle context and existing COLLECTABLES/PRD decisions. Oracle memory.md and lessons.md absent. Prior choices retained: coin-name ownership, test award eligibility, atomic persistence and no duplicate rerolls. Read Mouse coordination context and current persona states. Existing statistics use byte padding; award scoring must avoid that bias.
