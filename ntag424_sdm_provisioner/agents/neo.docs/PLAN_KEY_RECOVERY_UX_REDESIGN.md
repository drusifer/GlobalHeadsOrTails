# Key Recovery UX Redesign Plan

## Problem Statement

1. **Bug**: Key recovery says keys worked but doesn't actually restore a working set
2. **UX Issues**: Current UI doesn't clearly show:
   - The 3 keys for each tag and their current status
   - Which specific keys were validated during testing
   - Whether a restore was actually effective

## Proposed Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KEY RECOVERY TOOL                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TAG STATUS                                                                  │
│ UID: 04B7664A2F7080   HW: PRO   DB: PROV                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ KEY 0 (PICC):  825f8399...  DB: ✓  HW: v01  TESTED: ✓                   ││
│ │ KEY 1 (App):   3865245e...  DB: ✓  HW: v01  TESTED: ✓                   ││
│ │ KEY 3 (SDM):   c099b6d1...  DB: ✓  HW: v01  TESTED: -                   ││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ BACKUP KEY CANDIDATES                                                       │
│ ┌───────┬────────┬────────┬────────┬─────────┬──────────┬─────────────────┐│
│ │Source │ Status │ Date   │ PICC   │ App     │ SDM      │ Tested          ││
│ ├───────┼────────┼────────┼────────┼─────────┼──────────┼─────────────────┤│
│ │backup1│ prov   │ 12/25  │ 825f.. │ 3865..  │ c099..   │ ✓ PICC ✓ App    ││
│ │backup2│ failed │ 12/20  │ 825f.. │ 0000..  │ 0000..   │ ✓ PICC          ││
│ │tag_key│ prov   │ 11/08  │ 825f.. │ 3865..  │ c099..   │ -               ││
│ └───────┴────────┴────────┴────────┴─────────┴──────────┴─────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ PHONE TAP TEST (reused from diagnostics)                                    │
│ URL: ...exec?uid=04B7664A2F7080&ctr=000005&cmac=A1B2C3D4E5F6G7H8            │
│ ✓ VALID SDM - CMAC matches                                                  │
│                                                                             │
│ Android NFC Detection:                                                      │
│   1. Read Access FREE: ✓                                                    │
│   2. NDEF Format: ✓                                                         │
│   3. CC File Valid: ✓                                                       │
│   4. Offsets Valid: ✓                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Scan Tag] [Test Selected] [Restore to DB] [Set to Factory] [Back]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Fix the Core Bug
**Files**: `tui/screens/key_recovery.py`, `services/key_recovery_service.py`

1. **Investigate why restore doesn't work**
   - Check if `save_tag_keys` is actually being called with correct UID
   - Verify the keys being restored match what was tested
   - Add logging to trace the full restore flow

2. **Fix UID type consistency in restore flow**
   - Ensure `uid` passed to `TagKeys` is a `UID` object or string that gets converted
   - Verify the `save_tag_keys` fix from earlier session is applied correctly

### Phase 2: Create Enhanced Tag Keys Status Widget
**Files**: `tui/widgets.py`

1. **Create `TagKeysDetailWidget`** - shows all 3 keys with their status:
   ```python
   class TagKeysDetailWidget(Static):
       """Shows detailed key status for a tag."""

       # Properties for each key
       picc_key: str  # Key 0 value (hex)
       app_key: str   # Key 1 value (hex)
       sdm_key: str   # Key 3 value (hex)

       picc_in_db: bool
       app_in_db: bool
       sdm_in_db: bool

       picc_tested: bool | None  # None = not tested, True = passed, False = failed
       app_tested: bool | None
       sdm_tested: bool | None

       hw_key0_version: int | None
       hw_key1_version: int | None
       hw_key3_version: int | None
   ```

### Phase 3: Create Candidates Table Widget
**Files**: `tui/widgets.py` or `tui/screens/key_recovery.py`

1. **Create `KeyCandidatesTable`** using Textual's `DataTable`:
   - Columns: Source, Status, Date, PICC, App, SDM, Tested
   - Show partial key values (first 8 chars)
   - Color-code by status (provisioned=green, failed=red, etc.)
   - Indicate which keys were tested with checkmarks

### Phase 4: Extract Phone Tap Component
**Files**: `tui/widgets.py`

1. **Create `PhoneTapWidget`** - reusable component from `read_tag.py`:
   - Extract the SDM validation display logic from `_update_dashboard_tiles`
   - Make it a standalone widget that accepts `sdm_validation` dict
   - Reuse in both `ReadTagScreen` and `KeyRecoveryScreen`

### Phase 5: Redesign Key Recovery Screen Layout
**Files**: `tui/screens/key_recovery.py`

1. **New layout structure**:
   ```
   - Header
   - TagKeysDetailWidget (top section - shows 3 keys status)
   - KeyCandidatesTable (middle section - selectable backup keys)
   - PhoneTapWidget (shows SDM validation when tested)
   - Button bar (Scan, Test, Restore, Set Factory, Back)
   - Footer
   ```

2. **Update button handlers**:
   - "Test Selected" - test the selected candidate, update tested column
   - "Restore to DB" - save keys and refresh TagKeysDetailWidget
   - "Set to Factory" - new button, saves all-zero keys

### Phase 6: Add "Set to Factory" Feature
**Files**: `tui/screens/key_recovery.py`, `csv_key_manager.py`

1. **Add button**: "Set to Factory"
2. **Implementation**:
   - Create TagKeys with all 00 keys
   - Save to database with status "factory"
   - Refresh display to show new state

### Phase 7: Improve Test Feedback
**Files**: `services/key_recovery_service.py`, `tui/screens/key_recovery.py`

1. **Track which keys were validated**:
   - PICC (Key 0) - validated if AuthenticateEV2 succeeds
   - App (Key 1) - validated if... (need to check how this is used)
   - SDM (Key 3) - validated if CMAC check passes

2. **Return detailed test results**:
   ```python
   {
       "picc_works": True,
       "app_works": True,  # or None if not tested
       "sdm_works": True,  # based on CMAC validation
   }
   ```

## File Changes Summary

| File | Changes |
|------|---------|
| `tui/widgets.py` | Add `TagKeysDetailWidget`, `PhoneTapWidget` |
| `tui/screens/key_recovery.py` | Complete redesign of layout and flow |
| `tui/screens/read_tag.py` | Refactor to use `PhoneTapWidget` |
| `services/key_recovery_service.py` | Return detailed test results |
| `csv_key_manager.py` | Already fixed for UID handling |

## Testing Plan

1. **Manual Testing**:
   - Scan a provisioned tag
   - Verify 3 keys displayed correctly
   - Test a backup candidate
   - Verify tested columns update
   - Restore keys
   - Verify TagKeysDetailWidget shows restored keys
   - Run phone tap test to verify SDM works

2. **Edge Cases**:
   - Tag not in database
   - No backup candidates found
   - Partial key set (some keys are 00)
   - Factory tag (all keys 00)
