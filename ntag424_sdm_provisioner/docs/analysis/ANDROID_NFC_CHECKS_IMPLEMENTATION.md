# Android NFC Detection Checks - Implementation Summary

**Date**: 2025-12-28
**Status**: ✅ COMPLETE

## Overview

Added comprehensive Android NFC detection validation to the diagnostics tool. The system now verifies all 4 critical conditions required for Android background NFC detection and displays the results in the TUI.

## What Was Added

### 1. Service Layer - Android NFC Validation Logic

**File**: [diagnostics_service.py](../src/ntag424_sdm_provisioner/services/diagnostics_service.py)

#### New Method: `_check_android_nfc_conditions()`

Validates all 4 conditions required for Android NFC detection:

```python
def _check_android_nfc_conditions(self, ndef_data: bytes, sdm_config: Any) -> dict[str, Any]:
    """Check all 4 conditions required for Android NFC detection.

    Returns:
        Dict with check results for each condition
    """
```

**Conditions Checked**:

1. **Condition 1: File 2 Read Access = FREE**
   - Reads file settings for NDEF file (File 2)
   - Verifies Read Access = `0x0E` (FREE)
   - Android requires free read access to detect NDEF

2. **Condition 2: NDEF Format Wrapper**
   - Validates NDEF binary structure
   - Checks for proper headers: `[03] [Len] [D1] [01] [Len] [55] [04]`
   - Verifies:
     - TLV Tag = `0x03` (NDEF Message)
     - NDEF Header = `0xD1` (MB=1, ME=1, SR=1, TNF=Well-Known)
     - Type Length = `0x01`
     - URI Type = `0x55` ('U' for URI)
     - URI Prefix = `0x04` (https://)

3. **Condition 3: CC File Valid (E1 04 marker)**
   - Reads full CC file (23 bytes)
   - Validates NDEF File Control TLV structure
   - Checks:
     - TLV Tag = `0x04` (NDEF File Control)
     - File ID = `0xE104` (File 2)
     - Read Access = `0x00` (FREE)

4. **Condition 4: SDM Offsets Valid**
   - Validates SDM offset calculations
   - Checks for overlaps:
     - UID (14 bytes) must not overlap Counter
     - Counter (6 bytes) must not overlap CMAC
     - CMAC (16 bytes) must fit within file size
   - Verifies all offsets are within file bounds

**Return Structure**:

```python
{
    "condition_1_read_access_free": bool,
    "condition_2_ndef_format": bool,
    "condition_3_cc_file_valid": bool,
    "condition_4_offsets_valid": bool,
    "all_conditions_pass": bool,
    "details": {
        "read_access": "...",
        "ndef_format": {...},
        "cc_file": {...},
        "sdm_offsets": {...}
    }
}
```

#### Updated Method: `_simulate_phone_tap()`

Enhanced to include Android NFC checks in the phone tap simulation:

```python
# === ANDROID NFC DETECTION CHECKS ===
result["android_nfc_checks"] = self._check_android_nfc_conditions(ndef_info["data"], sdm_config)
```

### 2. TUI Display - Visual Feedback

**File**: [read_tag.py](../src/ntag424_sdm_provisioner/tui/screens/read_tag.py)

#### Updated `_update_dashboard_tiles()` Method

Added Android NFC detection status to the URL validation tile:

```python
# === ANDROID NFC DETECTION CHECKS ===
android_checks = sdm_validation.get("android_nfc_checks", {})
if isinstance(android_checks, dict):
    url_content += "\n\n[bold yellow]Android NFC Detection:[/]\n"

    all_pass = android_checks.get("all_conditions_pass", False)
    if all_pass:
        url_content += "[green bold]✓ ALL CHECKS PASS - Android will detect and launch URL[/]\n"
    else:
        url_content += "[yellow]⚠ Some checks failed - Android may not detect tag[/]\n"

    # Show individual condition status
    url_content += f"  1. Read Access FREE: {'[green]✓[/]' if c1 else '[red]✗[/]'}\n"
    url_content += f"  2. NDEF Format: {'[green]✓[/]' if c2 else '[red]✗[/]'}\n"
    url_content += f"  3. CC File Valid: {'[green]✓[/]' if c3 else '[red]✗[/]'}\n"
    url_content += f"  4. Offsets Valid: {'[green]✓[/]' if c4 else '[red]✗[/]'}"
```

**Visual Indicators**:
- ✅ Green checkmarks for passing conditions
- ❌ Red X marks for failing conditions
- Summary message indicating overall Android compatibility

### 3. Documentation

**File**: [ANDROID_NFC_DETECTION_VERIFICATION.md](ANDROID_NFC_DETECTION_VERIFICATION.md)

Comprehensive documentation verifying the implementation of all 4 conditions:
- Detailed explanation of each condition
- NXP datasheet references
- Code implementation references
- Binary structure diagrams
- Android NFC detection flow

## How It Works

### User Workflow

1. **User scans a provisioned tag** in the "Read Tag Info" screen
2. **Diagnostics service runs** all checks automatically
3. **TUI displays results** in the URL validation tile:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SDM URL VALIDATION & ANDROID NFC CHECKS

   Base: https://example.com

   UID: 04B6694A2F7080  Counter: 1  CMAC: 1A2B3C...
   ✓ VALID - CMAC matches

   Android NFC Detection:
   ✓ ALL CHECKS PASS - Android will detect and launch URL
     1. Read Access FREE: ✓
     2. NDEF Format: ✓
     3. CC File Valid: ✓
     4. Offsets Valid: ✓
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

### Behind the Scenes

1. **Service reads tag data**:
   - File settings (for Read Access check)
   - NDEF file data (for format and offset checks)
   - CC file (for E1 04 marker check)

2. **Validation runs automatically**:
   - Each condition is checked independently
   - Detailed results stored for debugging
   - Overall pass/fail status calculated

3. **TUI renders results**:
   - Color-coded visual feedback
   - Individual condition status
   - Clear messaging about Android compatibility

## Benefits

### For Users

1. **Instant Feedback**: Know immediately if Android will detect the tag
2. **Troubleshooting**: See exactly which condition(s) are failing
3. **Confidence**: Verify provisioning before deploying tags

### For Developers

1. **Comprehensive Validation**: All 4 conditions checked automatically
2. **Detailed Diagnostics**: Full details available for debugging
3. **Maintainability**: Clear separation between service logic and UI

## Example Output

### All Checks Pass (Provisioned Tag)

```
Android NFC Detection:
✓ ALL CHECKS PASS - Android will detect and launch URL
  1. Read Access FREE: ✓
  2. NDEF Format: ✓
  3. CC File Valid: ✓
  4. Offsets Valid: ✓
```

### Some Checks Fail (Misconfigured Tag)

```
Android NFC Detection:
⚠ Some checks failed - Android may not detect tag
  1. Read Access FREE: ✗
  2. NDEF Format: ✓
  3. CC File Valid: ✓
  4. Offsets Valid: ✓
```

### Detailed Check Results (Debug)

Available in `diagnostics["sdm_validation"]["android_nfc_checks"]["details"]`:

```python
{
    "read_access": "0x0E (FREE)",
    "ndef_format": {
        "tlv_tag": "0x03 (✓)",
        "ndef_header": "0xD1 (✓)",
        "type_length": "0x01 (✓)",
        "uri_type": "0x55 (✓)",
        "uri_prefix": "0x04 (✓)"
    },
    "cc_file": {
        "tlv_tag": "0x04 (✓)",
        "ndef_file_id": "0xE104 (✓)",
        "ndef_read_access": "0x00 (✓)",
        "cc_length": 23
    },
    "sdm_offsets": {
        "uid_offset": 32,
        "uid_end": 46,
        "ctr_offset": 50,
        "ctr_end": 56,
        "cmac_offset": 62,
        "cmac_end": 78,
        "file_size": 100,
        "no_uid_ctr_overlap": true,
        "no_ctr_cmac_overlap": true,
        "within_bounds": true
    }
}
```

## Testing

To test the Android NFC checks:

1. **Start the TUI**:
   ```bash
   python -m ntag424_sdm_provisioner.tui.app
   ```

2. **Navigate to "Read Tag Info"**

3. **Scan a provisioned tag**

4. **Check the "SDM URL VALIDATION & ANDROID NFC CHECKS" tile**

Expected results for a correctly provisioned tag:
- ✅ All 4 conditions pass
- ✅ Message: "Android will detect and launch URL"
- ✅ All individual checks show green checkmarks

## Files Modified

1. **diagnostics_service.py** (lines 303-512)
   - Added `_check_android_nfc_conditions()` method
   - Updated `_simulate_phone_tap()` to run Android checks
   - **Bug Fix (2025-12-29)**: Fixed Condition 1 check to use `AccessRights.from_bytes()` to properly parse access rights from raw bytes

2. **read_tag.py** (lines 260-320)
   - Updated `_update_dashboard_tiles()` to display Android check results
   - Added visual indicators for each condition

## Bug Fixes

### Issue: Condition 1 Access Rights Parsing Error

**Problem**: Initial implementation attempted to access `file_settings.access_rights.read`, but `access_rights` is raw bytes (type `bytes`), not an `AccessRights` object.

**Error Message**:
```
AttributeError: 'bytes' object has no attribute 'read'
```

**Root Cause**: The `FileSettingsResponse.access_rights` field stores the raw 2-byte access rights data directly, not a parsed `AccessRights` object. The wire format is:
- Byte 0: `[Read|Write]` nibbles
- Byte 1: `[ReadWrite|Change]` nibbles

**Solution**: Use `AccessRights.from_bytes()` to parse the raw bytes before accessing the `read` attribute:

```python
# BEFORE (incorrect):
read_access = file_settings.access_rights.read

# AFTER (correct):
access_rights = AccessRights.from_bytes(file_settings.access_rights)
read_access = access_rights.read
```

**Example**: For access rights bytes `[0xE0, 0xEE]`:
- `0xE0 = [E|0]` → Read=0xE (FREE), Write=0x0 (Key 0)
- `0xEE = [E|E]` → ReadWrite=0xE (FREE), Change=0xE (FREE)
- Result: `read_access = 0xE = AccessRight.FREE` ✓

**Status**: ✅ Fixed in [diagnostics_service.py:394-402](../../src/ntag424_sdm_provisioner/services/diagnostics_service.py#L394-L402)

## References

- **NXP NTAG424 DNA Datasheet**: Section 8.2.3.2 (Capability Container File)
- **NFC Forum Type 4 Tag Specification**: Referenced in NXP datasheet
- **Verification Document**: [ANDROID_NFC_DETECTION_VERIFICATION.md](ANDROID_NFC_DETECTION_VERIFICATION.md)

## Conclusion

The Android NFC detection checks are now fully integrated into the diagnostics tool. Users can verify that their provisioned tags will work correctly with Android phones before deployment.

**Status**: ✅ Ready for testing with real Android devices
