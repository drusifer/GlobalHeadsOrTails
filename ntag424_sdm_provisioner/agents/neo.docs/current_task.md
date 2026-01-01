# Neo - Current Task

**Status**: Active - US-1.3 TUI Integration

## Task: US-1.3 - Integrate TagDiagnosticsService into TUI

**Assigned By**: Mouse (Sprint Manager)  
**Priority**: HIGH - Critical path blocker

## Tasks
1. Create `DiagnosticsServiceAdapter` (follow ProvisionScreen pattern)
2. Refactor `TagStatusScreen` to use `TagDiagnosticsService`
3. Refactor `ReadTagScreen` to use `TagDiagnosticsService`
4. Remove deprecated `TagStatusCommand` and `ReadTagCommand`
5. Verify tests pass

## Reference Pattern
- `src/ntag424_sdm_provisioner/tui/screens/provision.py` (ServiceAdapter pattern)
- Use `CardManager()` context manager
- Use `WorkerManager.execute_command()`

## Acceptance Criteria
- ✅ Both screens use `TagDiagnosticsService`
- ✅ No direct command usage
- ✅ Tests pass
- ✅ Deprecated commands removed

## Next Priority
Start implementation immediately - pattern already proven.
