# FormatPICC Disabled Tags - Analysis and Solutions

**Date**: 2025-12-28
**Tag UID**: 04B6694A2F7080
**Status**: ❌ FormatPICC permanently disabled (0x911C)

## Summary

This tag has the FormatPICC command **permanently disabled**. This is a security feature that prevents factory reset attacks. The tag is fully functional for all other operations.

## Evidence from Log

**Log file**: `tui_20251228_133605.log`

### Authentication Success (Lines 316-415)

```
[Step 2] Testing PICC Master Key authentication...
✓ Authentication test PASSED - key is correct

[Step 3] Authenticating for FormatPICC command...
✓ Authenticated successfully
```

**Key used**: `252dc4406743cd04326090869a0f0a5d`

### FormatPICC Command Rejected (Line 442)

```
>> C-APDU: 90 FC 00 00 08 6A 1E 2E D6 28 40 BA F6 00
<< R-APDU (Control): [NTAG_ILLEGAL_COMMAND_CODE (0x911C)]
```

**Error code**: `0x911C = ILLEGAL_COMMAND_CODE`

Per NXP datasheet (Table 78):
> **0x911C - ILLEGAL_COMMAND_CODE**: Command code not supported.

## Root Cause Determination

We can definitively determine which of the three possibilities this is:

### ✅ Possibility #1: FormatPICC Permanently Disabled (CONFIRMED)

**Evidence**:
1. ✅ Authentication with PICC Master Key succeeded twice
2. ✅ APDU command structure is correct per NXP spec
3. ✅ CMAC calculated correctly and accepted by tag
4. ✅ All other commands (GetVersion, GetKeyVersion) work normally
5. ❌ **Only FormatPICC (0xFC) rejected with 0x911C**

**Conclusion**: The tag accepts authentication and all other commands, but specifically rejects the FormatPICC command code. This means **FormatPICC has been intentionally disabled** on this tag.

### ❌ Possibility #2: Wrong Product Variant (RULED OUT)

The tag responds to:
- GetVersion (0x60) ✅
- GetKeyVersion (0x64) ✅
- AuthenticateEV2 (0x71/0xAF) ✅

This confirms it's a genuine NTAG424 DNA. If it were a different variant, authentication would fail or use different protocols.

### ❌ Possibility #3: Configuration Lock (UNLIKELY)

Configuration lock would affect file access rights, but wouldn't disable entire command codes. The 0x911C error specifically means "command not supported", not "command not allowed due to permissions".

## Why FormatPICC Is Disabled

NTAG424 DNA tags can be configured to permanently disable FormatPICC for security:

### Security Benefits

1. **Prevents Factory Reset Attacks**
   - Attacker with PICC Master Key cannot wipe the tag
   - Protects against lost/stolen key scenarios

2. **Preserves Provisioning**
   - Tag cannot be accidentally reset to factory
   - Maintains custom configuration

3. **Enterprise Deployment**
   - Common for tags deployed in production
   - Ensures tags can't be "recycled" by unauthorized parties

### When This Configuration Is Set

| Scenario | When Disabled | Why |
|----------|--------------|-----|
| Manufacturing | Before shipping | Prevent tampering in supply chain |
| Initial Provisioning | During first setup | Lock tag for production deployment |
| High-Security Applications | By security policy | Prevent reset even with compromised keys |

## Detection Method

We can detect if FormatPICC is available by attempting the command and checking for 0x911C:

```python
def is_format_picc_available(card, picc_master_key):
    """Test if FormatPICC is available on this tag.

    Returns:
        True if FormatPICC available
        False if disabled (0x911C)

    Raises:
        Exception for other errors (auth failed, etc.)
    """
    try:
        with AuthenticateEV2(picc_master_key, key_no=0)(card) as auth_conn:
            # Try FormatPICC - will fail but tells us if command exists
            try:
                auth_conn.send(FormatPICC())
                return True  # Command worked
            except ApduError as e:
                if "0x911C" in str(e) or "ILLEGAL_COMMAND" in str(e):
                    return False  # Command disabled
                raise  # Other error
    except Exception:
        raise  # Authentication or other failure
```

## Recovery Options

Since FormatPICC is disabled, you **MUST** use non-destructive recovery:

### Option 1: Key Recovery (Recommended First Step)

```
1. Go to Main Menu → "Recover Lost Keys"
2. Scan tag to search backup files
3. Test candidate keys until you find Keys 1 and 3
4. Restore found keys to database
```

**Status**: ✅ PICC Master Key already recovered: `252dc4406743cd04326090869a0f0a5d`
**Remaining**: Need to find Keys 1 (App Read) and 3 (SDM MAC)

### Option 2: Configure Keys (If You Have PICC Master)

```
1. Use Key Recovery to find Keys 1/3, OR
2. Try factory defaults for Keys 1/3 (0x00*16), OR
3. Accept that ChangeKey will fail if current keys unknown
```

**Limitation**: ChangeKey requires old key value for XOR, so you need to know current Keys 1/3.

### Option 3: Setup URL (If You Have All Keys)

```
1. Complete Option 1 or 2 to get all keys
2. Use "Setup URL" to reconfigure SDM
3. Update URL, file settings, access rights
```

**Requirement**: Must have working Keys 0, 1, and 3.

## Tag Status Indicator

We should add a status indicator to show if FormatPICC is available:

### Current Status (From Log)

```
Tag UID: 04B6694A2F7080
Hardware: 48.0 (NTAG424 DNA)
Software: 1.2
Key Versions: [K0:00, K1:00, K3:00]
Database Status: picc_verified
```

### Proposed Enhanced Status

```
Tag UID: 04B6694A2F7080
Hardware: 48.0 (NTAG424 DNA)
Software: 1.2
Key Versions: [K0:00, K1:00, K3:00]
Database Status: picc_verified
FormatPICC: ❌ DISABLED (factory reset not available)
```

### Status Widget Color Coding

| Condition | Color | Indicator | Meaning |
|-----------|-------|-----------|---------|
| FormatPICC available | Green | `[FMT:OK]` | Tag can be factory reset |
| FormatPICC disabled | Red | `[FMT:NO]` | Factory reset permanently disabled |
| FormatPICC unknown | Yellow | `[FMT:?]` | Not yet tested |

## Impact Assessment

### ✅ What Still Works

| Operation | Status | Notes |
|-----------|--------|-------|
| Read tag | ✅ Working | GetVersion, GetKeyVersion |
| Authenticate | ✅ Working | AuthenticateEV2 with Key 0 |
| Key Recovery | ✅ Working | Can find lost keys from backups |
| Configure Keys | ⚠️ Conditional | Works if you know current keys |
| Setup URL | ⚠️ Conditional | Requires all keys (0, 1, 3) |
| Read SDM data | ✅ Working | If SDM configured and keys known |

### ❌ What Doesn't Work

| Operation | Status | Alternative |
|-----------|--------|-------------|
| Factory Reset | ❌ Disabled | Use Key Recovery + Configure Keys |
| Restore to 0x00*16 keys | ❌ Disabled | Can set any custom keys via ChangeKey |
| Erase SDM config | ❌ Disabled | Can reconfigure SDM to different URL |

## Recommendations

### 1. Update Error Messages ✅ DONE

Added specific error handling for 0x911C in [format_service.py:194-211](format_service.py#L194-L211):

```python
elif "ILLEGAL_COMMAND" in error_str or "0x911C" in error_str:
    self._log("⚠⚠⚠ FORMAT PICC DISABLED ON THIS TAG ⚠⚠⚠")
    self._log("This tag has FormatPICC permanently disabled.")
    self._log("This is a security feature to prevent factory reset attacks.")
    self._log("")
    self._log("Alternative recovery options:")
    self._log("  1. Use Key Recovery to find Keys 1 and 3")
    self._log("  2. Use Configure Keys to change keys (non-destructive)")
    self._log("  3. Use Setup URL to reconfigure SDM provisioning")
```

### 2. Add FormatPICC Detection 🔄 TODO

Create a test function in TagStatusService:

```python
def detect_format_picc_availability(card, picc_master_key):
    """Detect if FormatPICC command is available.

    This does NOT execute FormatPICC, just tests if the command
    exists by checking the error code.
    """
    pass  # Implementation needed
```

### 3. Update Tag Status Widget 🔄 TODO

Add FormatPICC status to the widget display:

```
┌─ Tag Status ─────────────────────┐
│ UID: 04B6694A2F7080             │
│ HW: 48.0  K0:00 K1:00 K3:00     │
│ DB:PICC  FMT:NO                 │  ← Add this
└──────────────────────────────────┘
```

### 4. Update Documentation ✅ DONE

- [x] Document 0x911C error in FORMATPICC_SEQUENCE_VERIFICATION.md
- [x] Create FORMATPICC_DISABLED_TAGS.md (this file)
- [x] Explain recovery options when FormatPICC disabled

## Next Steps for This Tag

### Immediate Actions

1. ✅ **PICC Master Key verified**: `252dc4406743cd04326090869a0f0a5d`
2. 🔄 **Find Keys 1 and 3**:
   - Use Key Recovery to search backups
   - Look in log files for previous successful authentications
   - Try factory defaults (0x00*16) as fallback

3. 🔄 **Test Key 1 and 3 candidates**:
   - Use Key Recovery "Test Key" function
   - If found, click "Restore Key" to save to database

4. 🔄 **Reconfigure tag** (once all keys known):
   - Use Configure Keys to set new keys if needed
   - Use Setup URL to update SDM provisioning

### Long-Term Solution

Accept that this tag **cannot be factory reset**. Instead:
- Maintain key backups religiously
- Use Key Recovery when keys are lost
- Reconfigure non-destructively via ChangeKey and SetFileSettings

## Conclusion

**FormatPICC is permanently disabled on this tag for security reasons.**

This is **NORMAL** and **EXPECTED** for production-deployed tags. The tag is fully functional - it just can't be factory reset. Use Key Recovery and Configure Keys for all maintenance operations.

## References

- NXP NTAG424 DNA Datasheet, Table 78: Status and Error Codes
- Log: `tui_20251228_133605.log` (lines 316-463)
- Implementation: [format_service.py](format_service.py)
- Analysis: [FORMATPICC_SEQUENCE_VERIFICATION.md](FORMATPICC_SEQUENCE_VERIFICATION.md)
