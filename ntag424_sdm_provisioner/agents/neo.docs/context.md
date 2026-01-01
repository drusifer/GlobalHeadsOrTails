# Neo - Current Context

**Last Updated**: 2025-11-27 23:00

## Implementation Details
- **Tag Status**: Uses `TagStatusCommand` (headless) + `TagStatusScreen` (TUI).
- **Key Detection**: Tries factory keys first, then registered keys from CSV.
- **Worker**: Uses standard `WorkerManager` pattern.

## Codebase State
- TUI tests passing (before this change).
- New files added: `tag_status_command.py`, `tag_status.py`.
