# Refactoring Plan - Technical Debt Reduction

**Author**: Neo (SWE)
**Date**: 2026-01-01
**Status**: DRAFT - Awaiting Approval

---

## Executive Summary

This plan addresses the technical debt identified by Trin's QA report:
- 3 F-grade complexity functions (CC > 40)
- 4 D-grade complexity functions (CC 21-30)
- 1 code duplication (46 lines)
- 77 mypy type errors
- 1 security issue (pyCrypto deprecation)

**Approach**: Test-first refactoring. Write characterization tests before touching any code.

---

## Phase 1: Quick Wins (Low Risk, High Value)

### 1.1 Remove Code Duplication

**Issue**: `Ntag424VersionInfo` duplicated in two locations:
- `commands/get_chip_version.py:10-53` (PRIMARY - keep this)
- `constants.py:716-758` (DUPLICATE - remove)

**Test Strategy**: No new tests needed - existing tests use the import from either location.

**Refactoring Steps**:
1. Search for all imports of `Ntag424VersionInfo`
2. Update imports to use `from ntag424_sdm_provisioner.commands.get_chip_version import Ntag424VersionInfo`
3. Delete the duplicate from `constants.py`
4. Run all tests to verify

**Risk**: LOW (simple import redirection)

---

### 1.2 Remove Unreachable Code

**Issue**: `maintenance_service.py:137` has unreachable code after `return`

**Test Strategy**: None needed - dead code.

**Refactoring Steps**:
1. Read the function
2. Delete unreachable lines
3. Run tests

**Risk**: NONE

---

### 1.3 Fix Unused Imports (vulture)

**Issue**:
- `diagnostics_service.py`: Unused `NdefRecordHeader`, `NdefTLV`, `NdefWellKnownType`
- `tui/widgets.py`: Unused `Optional`, unused `new_value` in watchers

**Test Strategy**: None needed for import removal. Watcher signatures are required by Textual framework (false positive).

**Refactoring Steps**:
1. Remove unused imports
2. Add `# noqa: ARG002` comments to Textual watcher methods (framework requirement)
3. Run ruff check

**Risk**: NONE

---

## Phase 2: Type Safety (Medium Risk)

### 2.1 UID Type Consistency

**Root Cause**: `CsvKeyManager.get_key(uid: str)` but many callers pass `bytes`

**Options**:
| Option | Description | Impact |
|--------|-------------|--------|
| A | Change CsvKeyManager to accept `bytes`, convert internally | 1 file change |
| B | Change all callers to convert `bytes` to `str` | 12+ file changes |
| C | Accept both with `uid: str | bytes`, normalize internally | 1 file change |

**Recommendation**: Option C (defensive, minimal changes)

**Test Strategy**:
```python
# tests/test_csv_key_manager_uid.py
def test_get_key_accepts_string():
    """get_key should work with hex string UID."""

def test_get_key_accepts_bytes():
    """get_key should work with bytes UID."""

def test_get_tag_keys_accepts_both():
    """get_tag_keys should accept str or bytes."""
```

**Refactoring Steps**:
1. Write tests for both input types (they will fail)
2. Update `get_key` signature to `uid: str | bytes`
3. Add normalization: `uid_str = uid.hex().upper() if isinstance(uid, bytes) else uid.upper()`
4. Apply same pattern to `get_tag_keys`, `save_tag_keys`, `provision_tag`
5. Run all tests

**Risk**: MEDIUM (API change, but backwards compatible)

---

## Phase 3: Complexity Reduction (Higher Risk)

### 3.1 `_check_android_nfc_conditions` (F-grade, 41+ decisions)

**Location**: `services/diagnostics_service.py:406`

**Analysis**: This function checks 4 conditions with multiple nested try/except blocks. Each condition is independent.

**Refactoring Strategy**: Extract Method Pattern

```python
# BEFORE: One monolithic function with 4 conditions
def _check_android_nfc_conditions(self, ndef_data, sdm_config) -> dict:
    # Condition 1: 50 lines
    # Condition 2: 50 lines
    # Condition 3: 50 lines
    # Condition 4: 30 lines

# AFTER: Orchestrator + 4 focused helpers
def _check_android_nfc_conditions(self, ndef_data, sdm_config) -> dict:
    checks = self._init_checks_dict()
    checks = self._check_condition_1_read_access(checks)
    checks = self._check_condition_2_ndef_format(checks, ndef_data)
    checks = self._check_condition_3_cc_file(checks)
    checks = self._check_condition_4_sdm_offsets(checks, sdm_config, ndef_data)
    checks["all_conditions_pass"] = all([
        checks["condition_1_read_access_free"],
        checks["condition_2_ndef_format"],
        checks["condition_3_cc_file_valid"],
        checks["condition_4_offsets_valid"],
    ])
    return checks

def _check_condition_1_read_access(self, checks: dict) -> dict:
    # Focused on just condition 1
    ...
```

**Test Strategy** (Characterization Tests):
```python
# tests/test_android_nfc_conditions.py
class TestAndroidNfcConditions:
    """Characterization tests - capture current behavior before refactoring."""

    def test_all_conditions_pass_with_valid_tag(self, simulator):
        """Capture expected output for valid provisioned tag."""
        # Run with simulator, save result as golden output

    def test_condition_1_fails_when_read_not_free(self):
        """Condition 1 should fail when read access != FREE."""

    def test_condition_2_fails_with_invalid_ndef(self):
        """Condition 2 should fail with malformed NDEF."""

    def test_condition_3_fails_without_cc_file(self):
        """Condition 3 should fail when CC file missing."""

    def test_condition_4_fails_with_bad_offsets(self):
        """Condition 4 should fail when SDM offsets invalid."""
```

**Risk**: MEDIUM (existing tests + characterization tests provide safety net)

---

### 3.2 `_discover_all_tags` (F-grade, 41+ decisions)

**Location**: `tui/screens/key_recovery.py:254`

**Analysis**: This function scans CSV and log files, extracting UIDs and keys. Mixed concerns: file I/O, parsing, data aggregation.

**Refactoring Strategy**: Extract + Delegate Pattern

```python
# BEFORE: One function doing file walk, CSV parsing, log parsing, aggregation
def _discover_all_tags(self) -> None:
    # Walk directories
    # Parse CSV files
    # Parse log files
    # Aggregate by UID

# AFTER: Orchestrator + specialized parsers
def _discover_all_tags(self) -> None:
    self._update_status("Scanning for CSV and log files...")
    candidates = self._collect_all_candidates()
    self._display_candidates(candidates)

def _collect_all_candidates(self) -> dict[str, list[KeyRecoveryCandidate]]:
    candidates: dict[str, list[KeyRecoveryCandidate]] = {}
    for file_path in self._walk_recovery_files():
        if file_path.suffix == '.csv':
            self._parse_csv_file(file_path, candidates)
        elif file_path.name.startswith('tui_') and file_path.suffix == '.log':
            self._parse_log_file(file_path, candidates)
    return candidates

def _parse_csv_file(self, path: Path, candidates: dict) -> None:
    # Focused CSV parsing

def _parse_log_file(self, path: Path, candidates: dict) -> None:
    # Focused log parsing
```

**Test Strategy**:
```python
# tests/test_key_recovery_parsing.py
class TestKeyRecoveryCsvParsing:
    def test_parse_valid_csv_row(self):
        """Parse a valid CSV row into KeyRecoveryCandidate."""

    def test_handle_missing_columns(self):
        """Gracefully handle missing optional columns."""

class TestKeyRecoveryLogParsing:
    def test_extract_uid_from_log(self):
        """Extract UID patterns from log content."""

    def test_extract_keys_from_log(self):
        """Extract key patterns from log content."""
```

**Risk**: MEDIUM

---

### 3.3 `_update_dashboard_tiles` (E-grade, 31-40 decisions)

**Location**: `tui/screens/read_tag.py:132`

**Analysis**: This function updates 6 dashboard tiles with complex conditional formatting.

**Refactoring Strategy**: Template Method Pattern

```python
# BEFORE: One function with 6 blocks of conditional formatting
def _update_dashboard_tiles(self, diagnostics: dict) -> None:
    # Chip tile: 10 lines
    # Database tile: 15 lines
    # Keys tile: 10 lines
    # Files tile: 10 lines
    # NDEF tile: 15 lines
    # SDM tile: 40 lines

# AFTER: One formatter per tile
def _update_dashboard_tiles(self, diagnostics: dict) -> None:
    self._update_chip_tile(diagnostics.get("chip", {}))
    self._update_database_tile(diagnostics.get("database_status", {}))
    self._update_keys_tile(diagnostics.get("key_versions_unauth", {}))
    self._update_files_tile(diagnostics.get("file_settings_unauth", "N/A"))
    self._update_ndef_tile(diagnostics.get("ndef", {}), diagnostics.get("cc_file", {}))
    self._update_sdm_tile(diagnostics.get("sdm_validation", {}))

def _update_chip_tile(self, chip_info: dict) -> None:
    # Focused on chip tile only
```

**Test Strategy**:
```python
# tests/test_read_tag_formatters.py
class TestDashboardFormatters:
    def test_format_chip_info_valid(self):
        """Format valid chip info dict."""

    def test_format_chip_info_error(self):
        """Format error case for chip info."""
```

**Risk**: LOW (pure formatting functions, easy to test)

---

## Phase 4: Security Fix

### 4.1 Migrate from pyCrypto to cryptography

**Issue**: `seritag_simulator.py` uses deprecated pyCrypto

**Current**:
```python
from Crypto.Cipher import AES
```

**Target**:
```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
```

**Test Strategy**: Existing tests use the simulator - they will catch any regression.

**Refactoring Steps**:
1. Add `cryptography` to dependencies (may already be there)
2. Update AES usage in `seritag_simulator.py`
3. Run all tests

**Risk**: LOW (well-tested migration path, simulator is test-only code)

---

## Implementation Order

| Priority | Task | Risk | Tests First? |
|----------|------|------|--------------|
| 1 | Remove `Ntag424VersionInfo` duplication | LOW | No |
| 2 | Remove unreachable code in `maintenance_service.py` | NONE | No |
| 3 | Fix unused imports | NONE | No |
| 4 | Fix UID type consistency | MEDIUM | YES |
| 5 | Refactor `_update_dashboard_tiles` | LOW | YES |
| 6 | Refactor `_check_android_nfc_conditions` | MEDIUM | YES |
| 7 | Refactor `_discover_all_tags` | MEDIUM | YES |
| 8 | Migrate pyCrypto to cryptography | LOW | No (existing tests) |

---

## Success Criteria

After refactoring:
- [ ] All 127 tests still pass
- [ ] No F-grade functions (CC < 30)
- [ ] No E-grade functions (CC < 20 preferred)
- [ ] mypy errors reduced by 50%+
- [ ] Zero pylint duplications
- [ ] bandit: 0 High severity

---

## Risk Mitigation

1. **Git branch**: Create `refactor/tech-debt-cleanup` branch
2. **Small commits**: One logical change per commit
3. **Frequent tests**: Run `pytest` after each change
4. **Rollback plan**: If tests fail after 2 attempts, revert and consult Oracle

---

**Awaiting approval from @Drew before proceeding.**
