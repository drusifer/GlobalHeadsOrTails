# Morpheus - Current Context

**Last Updated**: 2026-01-27 12:26

## Recent Decisions
- **Coin Naming Architecture**: Designed enhancement for 2-tag-per-coin tracking
  - Schema: Add `coin_name` field to TagKeys dataclass
  - API: 4 new methods (assign, get, validate, list)
  - TUI: Enhanced provision screen with coin_name input
  - Status: Architecture complete, ready for Neo implementation
  - Doc: `morpheus.docs/COIN_NAMING_ARCHITECTURE.md`

## Key Files Being Worked On
- `src/ntag424_sdm_provisioner/csv_key_manager.py` (coin_name enhancement)
- `src/ntag424_sdm_provisioner/tui/screens/provision.py` (coin_name input)
- `src/ntag424_sdm_provisioner/tui/screens/tag_status.py` (coin display)

## Active Decisions
- Coin tracking is production critical (Drew's request)
- Backwards compatible design (existing tags have coin_name = "")
- Validation prevents duplicate outcomes per coin
- 3-phase implementation: Schema → TUI → Validation

## Team Dependencies
- Neo: Ready to start Phase 1 (Schema & API)
- Trin: Preparing test plan
- Oracle: Will document in ARCH.md after completion

## Notes
- Outcome enum (HEADS/TAILS) already exists - good foundation
- CSV migration is graceful (empty string for missing field)
- Estimated 4.5 hours total implementation time
