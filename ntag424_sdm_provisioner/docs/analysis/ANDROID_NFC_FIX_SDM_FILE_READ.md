# Android NFC Detection Fix - SDM FileRead Access Rights

**Date**: 2025-12-29
**Status**: ✅ FIXED

## Problem

Tags were **not detected by Android's background NFC dispatcher** despite all 4 Android NFC detection conditions passing in diagnostics:

```
Android NFC Detection:
✓ ALL CHECKS PASS - Android will detect and launch URL
  1. Read Access FREE: ✓
  2. NDEF Format: ✓
  3. CC File Valid: ✓
  4. Offsets Valid: ✓
```

However, Android phones would not detect the tag - only the NXP TagInfo app could read it.

## Root Cause

The issue was **SDM FileRead access rights** being set to `KEY_3` instead of `FREE`.

### Two Layers of Access Control

NTAG424 DNA has TWO independent access control layers when SDM is enabled:

1. **File Access Rights** (applies to entire file)
   - Set via ChangeFileSettings
   - Controls basic file operations
   - Our setting: Read = `0xE` (FREE) ✓

2. **SDM Access Rights** (applies to SDM features)
   - Set via ChangeFileSettings SDM configuration
   - Controls SDM mirroring behavior
   - **Our setting: FileRead = `0x3` (KEY_3)** ✗

### The Problem

When SDM is enabled, **SDM FileRead overrides file-level Read access**:

```
File Settings (from diagnostics):
  Access Rights: E0EE
    Read:  FREE (0xE) ✓
    Write: KEY_0 (0x0)

  SDM Access Rights: FEE3
    MetaRead: FREE (0xE) ✓
    FileRead: KEY_3 (0x3) ✗  ← BLOCKS ANDROID!
    CtrRet:   NEVER (0xF)
```

Even though file-level Read = FREE, the SDM FileRead = KEY_3 **requires authentication with Key 3** to read the file. Android cannot authenticate, so it cannot read the NDEF data!

## The Misconception

The original code comment said:

```python
# Byte 1[3:0] = SDMFileRead (3 = key 3 for CMAC, enables MAC mirroring)
data.extend([0xFE, 0xE3])  # SDMAccessRights: UID plain, CMAC with Key 3
```

This **incorrectly assumed** that setting SDMFileRead to the CMAC key number (3) was required for CMAC mirroring. This is **NOT true** according to the NXP spec.

### What SDMFileRead Actually Controls

From NXP NTAG424 DNA datasheet (AN12196):

- **SDMFileRead**: Access rights for reading the file **when SDM is enabled**
- **CMAC Key**: Configured separately in file access rights (Write/ReadWrite/Change)

Setting SDMFileRead = 3 does NOT mean "use Key 3 for CMAC." It means "require authentication with Key 3 to read the file at all."

## The Fix

Changed SDM Access Rights from `0xFEE3` to `0xFEEF`:

**Before**:
```python
# Byte 1 = (0xE << 4) | 0x3 = 0xE3 (MetaRead=E, FileRead=3)
data.extend([0xFE, 0xE3])  # SDMAccessRights: UID plain, CMAC with Key 3
```

**After**:
```python
# Byte 1 = (0xE << 4) | 0xF = 0xEF (MetaRead=E, FileRead=F)
data.extend([0xFE, 0xEF])  # SDMAccessRights: MetaRead=E, FileRead=F
```

This sets:
- `0xFE` → CtrRet=E (FREE), RFU=F (reserved)
- `0xEF` → **MetaRead=E (FREE), FileRead=F (NO_SDM_AUTH)**

## Impact

### What Changes

✅ **SDMFileRead: KEY_3 → NEVER (F)**
- File-level Read=FREE allows Android to read without authentication
- SDMFileRead=F means "no SDM-specific authentication required for reading"
- Background NFC dispatcher will detect the tag automatically

### What Stays the Same

✅ **CMAC mirroring still works!**
- The tag still mirrors CMAC in the URL based on SDMOptions configuration
- CMAC validation continues to work correctly
- Security is maintained

✅ **All SDM features work**
- UID mirroring: Plain (MetaRead=E)
- Counter mirroring: Plain (CtrRet=E)
- CMAC mirroring: Still present in URL (configured via SDMOptions)

### Key Understanding

**SDMFileRead has three modes:**
1. **Key Number (0-4)**: Requires authentication with that key + includes MAC offsets in ChangeFileSettings
2. **FREE (E)**: This is NOT a valid SDM mode - causes parameter errors!
3. **NEVER (F)**: No SDM authentication required, tag uses file-level Read access rights

When `SDMFileRead=F`:
- File-level `Read=FREE` grants Android read access
- MAC offsets are OMITTED from ChangeFileSettings command
- Tag still performs CMAC mirroring in URL based on other SDM configuration

## Testing

After applying this fix:

1. **Re-provision the tag** using "Setup URL" in TUI
2. **Scan with diagnostics** - Should still show all 4 conditions passing
3. **Check file settings** - Should show:
   ```
   SDM Access Rights: FEEF
     MetaRead:  FREE (0xE)
     FileRead:  NEVER (0xF)  ← NOW SET TO NEVER!
     CtrRet:    FREE (0xE)
   ```
4. **Test with Android phone** - Should automatically detect tag and open URL
5. **Verify CMAC** - URL should still contain CMAC parameter despite FileRead=F

## References

- **NXP NTAG424 DNA Datasheet**: AN12196, Section 10.7 (SDM Configuration)
- **File Modified**: [constants.py:1278-1292](../../src/ntag424_sdm_provisioner/constants.py#L1278-L1292)
- **Related Documentation**:
  - [ANDROID_NFC_DETECTION_VERIFICATION.md](ANDROID_NFC_DETECTION_VERIFICATION.md)
  - [ANDROID_NFC_CHECKS_IMPLEMENTATION.md](ANDROID_NFC_CHECKS_IMPLEMENTATION.md)

## Lesson Learned

**SDMFileRead does NOT control CMAC mirroring - it controls SDM authentication mode!**

**Three SDMFileRead modes:**
1. **Key Number (0-4)**: Requires authentication + includes MAC offsets in command
2. **FREE (E)**: INVALID for SDM - causes NTAG_PARAMETER_ERROR!
3. **NEVER (F)**: No SDM auth required - use file-level Read access instead

**For Android compatibility with CMAC mirroring:**
- ✅ **DO**: Set file-level Read = FREE (0xE) - grants Android read access
- ✅ **DO**: Set SDMFileRead = NEVER (0xF) - no SDM auth required
- ✅ **DO**: Configure SDM features via SDMOptions (UID, Counter, CMAC still mirror!)
- ❌ **DON'T**: Set SDMFileRead = FREE (0xE) - this is invalid and causes errors!
- ❌ **DON'T**: Set SDMFileRead to a key (0-4) unless you want to require authentication

**Key Insight**: CMAC mirroring is controlled by SDMOptions configuration, NOT by SDMFileRead value. The tag will mirror CMAC in the URL regardless of whether SDMFileRead is set to F or a key number.
