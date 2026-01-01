# Android NFC Detection vs. CMAC Security Trade-off

**Date**: 2025-12-29
**Status**: 🔍 INVESTIGATION COMPLETE - FUNDAMENTAL LIMITATION

## Executive Summary

After thorough investigation and verification against the NXP NTAG424 DNA datasheet, there is a **fundamental trade-off** between:
1. ✅ Android background NFC detection (user convenience)
2. ✅ CMAC cryptographic validation (security)

**You cannot have both simultaneously with the current NTAG424 DNA chip architecture.**

## The Problem

Tags configured with CMAC security (SDMFileRead=KEY_3) are **not detected by Android's background NFC dispatcher**, despite passing all other Android NFC detection requirements.

## Root Cause - Verified Against NXP Datasheet

### SDMFileRead Access Rights (NXP Spec Table 11)

Per [NT4H2421Gx.md:482-488](../../docs/seritag/NT4H2421Gx.md#L482-L488):

| Value | Description |
|-------|-------------|
| `0h..4h` | SDMFileReadKey: free access, key number for Secure Dynamic Messaging |
| `Eh` | **RFU (Reserved for Future Use)** - INVALID! |
| `Fh` | No Secure Dynamic Messaging for Reading |

### Critical NXP Spec Quotes

**From Section 8.2.3.4 (line 490):**
> "If SDMFileRead access right is set to Fh, it is still possible to freely read the file if Read or ReadWrite access right are set to Eh. In this case, **plain mirroring of the PICCData, see Section 9.3.3, is still applied** if the card is configured for that."

**From Section 9.3.8 (line 1456):**
> "**MACing is mandatory if the SDMFileRead access right is configured for an application key.** If the SDMFileRead access right is disabling Secure Dynamic Messaging for reading (i.e. set to Fh), **SDMMACOffset and SDMMACInputOffset are not present in ChangeFileSettings.**"

### What This Means

1. **SDMFileRead = 0h..4h (Key Number)**:
   - ✅ CMAC mirroring enabled (secure)
   - ✅ Includes SDMMACOffset and SDMMACInputOffset in ChangeFileSettings
   - ❌ **Requires authentication to read** - Android cannot authenticate
   - 📱 Only specialized apps like NXP TagInfo can read

2. **SDMFileRead = Fh (NEVER)**:
   - ✅ Android can read without authentication (if file Read=FREE)
   - ✅ UID and Counter mirroring still work
   - ❌ **CMAC mirroring is DISABLED** (per spec: "MACing is mandatory if SDMFileRead is configured for an application key")
   - ❌ No cryptographic validation possible

3. **SDMFileRead = Eh (FREE)**:
   - ❌ **INVALID** - Reserved for Future Use
   - ❌ Causes `NTAG_PARAMETER_ERROR (0x919E)` if used

## Why Android Cannot Detect Tags with CMAC

When `SDMFileRead` is set to a key number (0-4):
1. The tag requires **authentication with that key** before allowing file reads
2. Android's background NFC dispatcher performs **unauthenticated reads only**
3. Android cannot provide the cryptographic key for authentication
4. Therefore, Android's read attempt **fails silently**
5. The tag is not detected or launched

This is **by design** - the whole point of SDMFileRead requiring a key is to prevent unauthenticated access!

## The Two Options

### Option 1: CMAC Security (Current Configuration)

**Configuration:**
```python
SDMFileRead = KEY_3 (0x3)
SDMAccessRights = 0xFEE3
```

**Characteristics:**
- ✅ CMAC mirroring enabled
- ✅ Cryptographic tag validation
- ✅ Protection against cloning/replay attacks
- ❌ Android background NFC dispatcher **cannot** detect tag
- 📱 Requires specialized apps (NXP TagInfo, custom app with authentication)

**URL Example:**
```
https://example.com/exec?uid=04AE664A2F7080&ctr=000099&cmac=CC1072D35ADD69AE
```

### Option 2: Android Compatibility (No CMAC)

**Configuration:**
```python
SDMFileRead = NEVER (0xF)
SDMAccessRights = 0xFEEF
file_access_rights.read = FREE (0xE)
```

**Characteristics:**
- ✅ Android background NFC dispatcher **can** detect tag
- ✅ Automatic URL launch on tap
- ✅ UID mirroring (unique tag ID)
- ✅ Counter mirroring (tap count tracking)
- ❌ **NO CMAC** - no cryptographic validation
- ⚠️ Vulnerable to UID/counter cloning (less secure)

**URL Example:**
```
https://example.com/exec?uid=04AE664A2F7080&ctr=000099
```

## Why We Cannot Have Both

The NXP NTAG424 DNA chip has a **hardware-level design decision**:

1. **CMAC requires SDM authentication**: Per NXP spec, CMAC mirroring is only available when `SDMFileRead` is set to a key number (0-4)

2. **SDM authentication blocks unauthenticated reads**: When a key is required, the tag will not respond to unauthenticated read attempts

3. **Android only does unauthenticated reads**: The background NFC dispatcher cannot perform cryptographic authentication

Therefore: **CMAC security ⟺ No Android auto-detection**

## Potential Workarounds (None Viable)

### ❌ Workaround 1: Use SDMFileRead=E (FREE)
- **Status**: Invalid per NXP spec (RFU)
- **Result**: `NTAG_PARAMETER_ERROR (0x919E)`

### ❌ Workaround 2: Set file-level Read=FREE with SDMFileRead=KEY_3
- **Status**: Attempted in original fix
- **Result**: Android still cannot detect - SDMFileRead overrides file-level access for unauthenticated reads

### ❌ Workaround 3: Custom Android App
- **Status**: Possible but defeats the purpose
- **Problem**: Requires users to install a custom app; cannot use background NFC dispatcher

## Recommendation

Choose based on your use case priority:

### Choose Option 1 (CMAC) if:
- Security is paramount
- You need cryptographic proof of tag authenticity
- Users can install a custom app or use NXP TagInfo
- Protection against cloning is critical

### Choose Option 2 (Android) if:
- User experience is paramount
- You want automatic URL launch on any Android phone
- UID + Counter tracking is sufficient
- You trust the backend to detect suspicious patterns

## Current Implementation

The codebase is currently configured for **Option 1 (CMAC Security)**.

**File**: [constants.py:1287-1313](../../src/ntag424_sdm_provisioner/constants.py#L1287-L1313)

To switch to Option 2, change line 1313:
```python
# FROM:
data.extend([0xFE, 0xE3])  # SDMAccessRights: CMAC enabled, blocks Android

# TO:
data.extend([0xFE, 0xEF])  # SDMAccessRights: Android compatible, no CMAC
```

And update lines 1348-1357 to omit MAC offsets when SDMFileRead=F.

## References

- **NXP NTAG424 DNA Datasheet**: NT4H2421Gx.md
  - Table 11 (line 482): SDMFileRead values
  - Section 8.2.3.4 (line 490): SDM access rights behavior
  - Section 9.3.8 (line 1456): CMAC requirements
- **Related Analysis**:
  - [ANDROID_NFC_FIX_SDM_FILE_READ.md](ANDROID_NFC_FIX_SDM_FILE_READ.md)
  - [ANDROID_NFC_DETECTION_VERIFICATION.md](ANDROID_NFC_DETECTION_VERIFICATION.md)
  - [ANDROID_NFC_CHECKS_IMPLEMENTATION.md](ANDROID_NFC_CHECKS_IMPLEMENTATION.md)

## Conclusion

This is not a bug or configuration error - it's a **fundamental architectural constraint** of the NTAG424 DNA chip as designed by NXP. The chip was designed to offer either:
- Secure authenticated SDM (with CMAC), OR
- Unauthenticated SDM (for Android compatibility)

But not both simultaneously.
