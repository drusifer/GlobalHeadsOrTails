# SDM Offset Calculation Bug Analysis

**Date:** 2025-12-09
**Status:** Root cause identified, fix pending

## Problem

`ChangeFileSettings` command fails with `NTAG_PARAMETER_ERROR (0x919E)` during Phase 2 (Setup URL) of SDM provisioning.

## Root Cause

The `calculate_sdm_offsets()` function in `sdm_helpers.py` calculates SDM mirror offsets incorrectly. All offsets are **+6 bytes too high**.

### Evidence from Comparison Script

```
======================================================================
OFFSET COMPARISON
======================================================================
UIDOffset:       spec=134, code=140, diff=6
ReadCtrOffset:   spec=153, code=159, diff=6
MACInputOffset:  spec=134, code=140, diff=6
MACOffset:       spec=165, code=171, diff=6
```

### The Bug

In `sdm_helpers.py` line 37:

```python
ndef_overhead = 7  # WRONG
```

The code then searches for parameter positions in the **full URL** (including `https://`):

```python
url = f"{template.base_url}?{'&'.join(params)}"  # Full URL with https://
uid_param = url.find("uid=")  # Position includes https:// prefix
uid_offset = ndef_overhead + uid_param + 4
```

### Why It's Wrong

**NDEF Type 4 Tag file structure:**
```
Offset 0-1:  NLEN (2 bytes) - length of NDEF message
Offset 2:    TLV Type (0x03)
Offset 3:    TLV Length
Offset 4:    NDEF Record Header (0xD1)
Offset 5:    Type Length (0x01)
Offset 6:    Payload Length
Offset 7:    Type (0x55 = 'U')
Offset 8:    URI Prefix Code (0x04 = https://)
Offset 9+:   URL content WITHOUT the https:// prefix
```

**Correct calculation:**
- NDEF header size = 9 bytes (before URL content starts)
- URL content in NDEF = URL without `https://` prefix (8 chars stripped)

**Current (buggy) calculation:**
- Uses `ndef_overhead = 7`
- Searches in full URL (includes `https://`)
- `code_offset = 7 + (stripped_pos + 8) = 15 + stripped_pos`

**Correct calculation:**
- Use `ndef_overhead = 9`
- Search in URL without prefix
- `spec_offset = 9 + stripped_pos`

**Difference:** `15 + stripped_pos - (9 + stripped_pos) = 6`

This explains the constant +6 byte difference in all offsets.

## Fix Required

In `calculate_sdm_offsets()`:

1. Change `ndef_overhead = 7` to `ndef_overhead = 9`
2. Strip the URL prefix before searching for parameter positions

OR equivalently:

1. Keep `ndef_overhead = 7`
2. Subtract prefix length (8) from positions, then add 2 for the NLEN field

The cleanest fix is option 1: use correct header size and search in stripped URL.

## Files Affected

- `src/ntag424_sdm_provisioner/commands/sdm_helpers.py` - `calculate_sdm_offsets()`

## Test Verification

After fix, run:
```powershell
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe tests/debug_scripts/compare_sdm_payload.py
```

Expected result: All offsets should match (diff=0).
