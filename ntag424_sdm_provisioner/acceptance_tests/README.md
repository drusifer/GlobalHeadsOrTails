# Acceptance Tests (Hardware Required)

**⚠️ These tests require real NTAG424 DNA tags and an NFC reader!**

This directory contains acceptance tests that validate the provisioner against real hardware. They are intentionally placed outside the `tests/` directory so pytest doesn't run them by default.

## Prerequisites

1. **Hardware**: ACR122U NFC reader (or compatible)
2. **Tags**: NTAG424 DNA tags (NXP or Seritag)
3. **Warning**: Some tests modify tag keys - use test tags only!

## Running Acceptance Tests

```powershell
# From ntag424_sdm_provisioner directory
# Run ALL acceptance tests (requires hardware):
& .venv\Scripts\python.exe -m pytest acceptance_tests/ -v

# Run a specific test:
& .venv\Scripts\python.exe -m pytest acceptance_tests/test_tui_simulation.py -v

# Run with extra output:
& .venv\Scripts\python.exe -m pytest acceptance_tests/ -v -s
```

## Test Categories

### Read-Only Tests (Safe)
These don't modify the tag:
- `test_fresh_tag_readonly.py` - Authentication only, no writes
- `test_tui_simulation.py` - TUI with real reader (reads only)

### Destructive Tests (Modify Keys!)
**⚠️ These will change tag keys - use expendable test tags!**
- `test_production_auth.py` - Full auth flow
- `test_changekey_*.py` - Key change operations
- `test_format_*.py` - Format/reset operations
- `test_session_validation.py` - Session key tests

## Tag Recovery

If a test fails mid-operation and corrupts a tag:
1. Check `tag_keys.csv` for saved keys
2. Use `examples/99_reset_to_factory.py` to reset
3. If keys are unknown, the tag may need factory reset via manufacturer

## Why Separate?

- **Cost**: Real tags are expensive (~$2-5 each)
- **Speed**: Hardware tests are slow (reader I/O)
- **CI/CD**: Can't run hardware tests in CI pipeline
- **Reliability**: Hardware tests can fail due to timing/connection issues

The main `tests/` directory uses mocks and simulators for fast, reliable CI testing.

