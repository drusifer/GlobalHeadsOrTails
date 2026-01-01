# Session Summary - 2025-11-11

## Overview
Fixed multiple bugs preventing SDM configuration and improved tool menu UX.

---

## Bugs Fixed

### 1. ✅ SDMUrlTemplate Type Error
**Problem**: Tools passed `bytes` to `calculate_sdm_offsets()` which expects `SDMUrlTemplate` object
```
ERROR: 'bytes' object has no attribute 'uid_placeholder'
```

**Solution**: Applied DRY principle
- Created `build_sdm_url_template(base_url)` in `tool_helpers.py`
- Created `configure_sdm_with_offsets(auth_conn, template)` in `tool_helpers.py`
- Eliminated ~60 lines of duplicate code across two tools

**Files Changed**:
- `tool_helpers.py` - Added 2 shared functions
- `configure_sdm_tool.py` - Simplified
- `provision_factory_tool.py` - Simplified

---

### 2. ✅ Precondition Logic Bug (AND vs OR)
**Problem**: "Provision Factory Tag" never appeared in menu, even for factory tags

**Root Cause**: Used `all(checks)` for AND logic, but `|` operator means OR

```python
preconditions = TagPrecondition.NOT_IN_DATABASE | TagPrecondition.STATUS_FACTORY
# Means: "available if NOT in DB OR if factory status" (either works)

# But matching used:
return all(checks)  # WRONG! Requires BOTH conditions
```

**Solution**: Changed to `any(checks)` for correct OR logic

**Files Changed**:
- `tools/base.py` - Line 131: `all()` → `any()`

---

### 3. ✅ Tool Availability UX Enhancement
**Problem**: Hidden tools gave no indication why they were unavailable

**Solution**: Show ALL tools in menu
- Available tools: Numbered (1, 2, 3...)
- Unavailable tools: Marked "X." with reason
- Polymorphic `tool.is_available(tag_state)` returns `True` or `(False, reason)`

**Architecture**:
```python
# Tool Protocol
def is_available(self, tag_state: TagState):
    """Each tool decides its own availability."""
    if not meets_requirements:
        return False, "human readable reason"
    return True

# Runner delegates to tool
result = tool.is_available(tag_state)
if result is True:
    # Show numbered
else:
    _, reason = result
    # Show "X." with reason
```

**Files Changed**:
- `tools/base.py` - Added `is_available()` to Tool protocol
- `tools/runner.py` - Shows all tools, filters by availability
- All 7 tool files - Implemented `is_available()`
- Removed old `preconditions` attribute
- Cleaned up `TagPrecondition` imports

**Tests**: Created 17 unit tests in `test_tool_availability.py` - all passing

---

### 4. ✅ ChangeFileSettingsAuth Missing Methods
**Problem**: `ChangeFileSettingsAuth` didn't support `auth_conn.send()` pattern

**Solution**: Implemented required `AuthApduCommand` methods:
- `get_command_byte()` → `0x5F`
- `get_unencrypted_header()` → file number
- `build_command_data()` → plaintext payload (no auth_conn parameter)

**Files Changed**:
- `commands/change_file_settings.py`

---

### 5. ✅ CMAC Counter Timing Bug **← CRITICAL!**
**Problem**: All authenticated commands failing with 0x911E (INTEGRITY_ERROR)

**Root Cause**: Counter was incremented BEFORE CMAC calculation
```python
# WRONG:
self.session_keys.cmd_counter += 1  # Increment to 1
cmd_ctr_bytes = self.session_keys.cmd_counter.to_bytes(2, 'little')  # Use 1
# CMAC calculated with counter=1, but card expects counter=0!
```

**Solution**: Use current counter, increment only after success
```python
# CORRECT:
current_counter = self.session_keys.cmd_counter  # Save current (0)
cmd_ctr_bytes = current_counter.to_bytes(2, 'little')  # Use 0
# auth_conn.send() increments AFTER 9100 response
```

**Files Changed**:
- `crypto/auth_session.py` - Fixed `apply_cmac()`

---

### 6. ✅ SDM_ENABLED Flag Misplaced
**Problem**: SDM_ENABLED (0x40) was incorrectly included in SDMOptions byte

**Root Cause**: Confusion between FileOption and SDMOptions
```python
# WRONG:
sdm_options = FileOption.SDM_ENABLED | FileOption.UID_MIRROR  # 0x40 | 0x80 = 0xC0

# CORRECT:
file_option = CommMode.MAC | 0x40  # SDM_ENABLED here
sdm_options = FileOption.UID_MIRROR | FileOption.READ_COUNTER  # 0x80 | 0x40 = 0xC0
```

**Per NXP Spec**:
- **FileOption**: Bits[1:0]=CommMode, Bit 6=SDM Enable
- **SDMOptions**: Bit 7=UID_MIRROR, Bit 6=READ_COUNTER, Bit 5=COUNTER_LIMIT

**Files Changed**:
- `commands/sdm_helpers.py` - Fixed default SDMOptions
- `tools/tool_helpers.py` - Fixed SDMOptions value

---

## Test Results

✅ **17/17 tool availability tests passing**
✅ **No linter errors**
✅ **Authentication working** (even on Seritag HW 48.0!)

---

## Current Status

### Working:
- ✅ EV2 Authentication (Phase 1 & 2)
- ✅ Session key derivation
- ✅ Tool menu UX with availability reasons
- ✅ Counter management (use current, increment after success)

### Needs Testing:
- ⏳ ChangeFileSettingsAuth with fixed counter + SDMOptions
- ⏳ Complete SDM configuration flow
- ⏳ End-to-end provisioning with Seritag tags

---

## Files Modified

### Core Library (4 files)
1. `crypto/auth_session.py` - Counter timing fix
2. `commands/change_file_settings.py` - Added auth_conn.send() support
3. `commands/sdm_helpers.py` - Fixed SDMOptions default
4. `tools/tool_helpers.py` - DRY helpers + fixed SDMOptions

### Tools (8 files)
5. `tools/base.py` - Added `is_available()` to Tool protocol
6. `tools/runner.py` - Show all tools with reasons
7-13. All 7 tool files - Implemented `is_available()`

### Documentation (1 file)
14. `LESSONS.md` - Documented all findings

### Tests (1 file)
15. `tests/test_tool_availability.py` - 17 new tests (NEW!)

**Total**: 15 files modified/created

---

## Next Steps

1. **Test SDM Configuration** - Try Configure SDM tool again
   - Counter now correct (0, not 1)
   - SDMOptions now correct (0xC0 = UID+COUNTER, not UID+COUNTER+ENABLED)
   
2. **If still 0x911E** - May need to check:
   - CMAC input structure
   - Encryption IV calculation
   - SDM payload byte order

3. **Try Provision Factory** - Should now appear in menu

---

## Key Learnings

1. **DRY Prevents Bugs**: Duplicate code had inconsistent implementations
2. **Type Hints Matter**: Function parameter types document what objects are expected
3. **AND vs OR**: When using `|` for flags, matching must use `any()` not `all()`
4. **Polymorphism > If-Else**: Let tools explain themselves rather than central logic
5. **Counter Timing**: Use current value in crypto, increment only after success
6. **Flag Placement**: Read spec carefully - similar named flags go in different bytes

---

**Status**: Ready for next test iteration with Seritag tag

