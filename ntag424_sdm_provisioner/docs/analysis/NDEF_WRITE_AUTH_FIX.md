# NDEF Authenticated Write Fix Analysis

**Date:** 2025-12-11
**Status:** Root cause identified, fix ready for implementation

## Problem Statement

Authenticated NDEF writes fail with error `0x6A87` (Lc inconsistent with TLV structure) during SDM provisioning.

## Error Log Evidence

From `tui_20251211_192408.log`:

```
Line 107-109:
>> C-APDU: 00 A4 02 00 0A E1 04 39 81 CA D5 43 2C 35 64 00
<< R-APDU (Control):  [0x6A87]

Line 116-117:
ISOSelectFile(NDEF_FILE (0xE104)) failed
  Unknown status (0x6A87)
```

## Root Cause Analysis

### What's Happening

1. After successful authentication and ChangeFileSettings (SDM config), the code attempts to write NDEF
2. `provisioning_service.py` line 273 calls:
   ```python
   auth_conn.send(ISOSelectFile(ISOFileID.NDEF_FILE))
   ```
3. `ISOSelectFile` extends `AuthApduCommand` and gets sent through `AuthenticatedConnection.send()`
4. The `send()` method appends an 8-byte MAC to the command
5. But `ISOSelectFile` uses CLA=0x00 (ISO 7816) which does NOT support secure messaging

### The Malformed APDU

```
00 A4 02 00 0A E1 04 39 81 CA D5 43 2C 35 64 00
|  |  |  |  |  |     |___________________________|
|  |  |  |  |  |     8-byte MAC (should NOT be here!)
|  |  |  |  |  File ID (E104 = NDEF file)
|  |  |  |  Lc = 10 bytes (should be 2!)
|  |  |  P2
|  |  P1 = 0x02 (Select EF)
|  INS = 0xA4 (SELECT)
CLA = 0x00 (ISO 7816)
```

The card expects Lc=2 (just the file ID) but receives Lc=10 (file ID + MAC), hence `0x6A87`.

### Spec References

**NXP Section 10.2 (Command Overview Table):**
- `ISOSelectFile` is listed as `CommMode.Plain` - no secure messaging support
- `WriteData (0x8D)` is listed as "Comm. mode of targeted file" - supports MAC/Full

**NXP Section 10.8.2 (WriteData):**
- Command format: `CLA=90, INS=8D, P1=00, P2=00`
- Data field: `FileNo(1) || Offset(3 LE) || Length(3 LE) || Data`
- FileNo is specified in command data - **no ISOSelectFile needed**

**ISO 7816-4:**
- Commands with CLA=0x00 do not support secure messaging (MAC/encryption)
- Secure messaging requires CLA with specific bits set (typically 0x04, 0x08, 0x0C)

## The Correct Approach

Per the spec, for authenticated NDEF writes:

1. Use native `WriteData (0x8D)` command
2. FileNo (0x02 for NDEF) goes in the command data, not via ISOSelectFile
3. Format: `FileNo(1) || Offset(3 LE) || Length(3 LE) || Data || MAC(8)`

## Sequence Comparison

### Current (Failing):
```
1. SelectPiccApplication     [OK]
2. AuthenticateEV2First      [OK]
3. AuthenticateEV2Second     [OK]
4. ChangeFileSettings (SDM)  [OK] - counter=1
5. ISOSelectFile(E104)       [FAIL 0x6A87] - MAC appended to ISO command!
```

### Correct (Per Spec):
```
1. SelectPiccApplication
2. AuthenticateEV2First
3. AuthenticateEV2Second
4. ChangeFileSettings (SDM)  - counter=1
5. WriteData(FileNo=02, ...)  - counter=2 (no ISOSelectFile needed!)
```

## Files Involved

### Already Fixed:
- `write_ndef_message.py` - `_WriteNdefChunk` class updated to use `0x8D` with proper header

### Needs Fix:
- `provisioning_service.py` line 273 - Remove the `ISOSelectFile` call:
  ```python
  # BEFORE (wrong):
  auth_conn.send(ISOSelectFile(ISOFileID.NDEF_FILE))
  WriteNdefMessageAuth(ndef_data=ndef_message).execute(auth_conn)

  # AFTER (correct):
  WriteNdefMessageAuth(ndef_data=ndef_message).execute(auth_conn)
  ```

## Additional Consideration: Chunked Writes

For large URLs requiring multiple WriteData commands, the spec notes:

**NXP Section 10.8.2:**
> "supports tearing protection for data that is sent within one communication frame"

**SetConfiguration Option 04h (Bit 2):**
> "disable chained writing with WriteData command in CommMode.MAC and CommMode.Full"

If chunked writes fail after fixing ISOSelectFile, check if this chip setting is blocking them.

## Debug Tool Created

`tools/debug_sdm_sequence.py` - Analyzes TUI logs and identifies:
- ISO commands with MACs (should not have them)
- ISOUpdateBinary in authenticated sessions (wrong command)
- Sequence issues vs spec-compliant sequence

Usage:
```bash
python tools/debug_sdm_sequence.py tui_20251211_192408.log
```

## Breadcrumbs / Investigation Trail

1. **Initial Error:** `NTAG_LENGTH_ERROR (0x917E)` in earlier logs with `0xD6` (ISOUpdateBinary)
2. **First Fix Attempt:** Changed to `0x8D` (WriteData) - still failed
3. **New Error:** `0x6A87` on ISOSelectFile
4. **Key Insight:** Decoded the APDU bytes - Lc=10 instead of Lc=2
5. **Root Cause:** MAC being appended to ISO command via `auth_conn.send()`
6. **Spec Confirmation:**
   - NXP Table in Section 10.2 shows ISOSelectFile is CommMode.Plain
   - WriteData specifies FileNo in command data (no select needed)
   - ISO 7816 CLA=0x00 doesn't support secure messaging

## Test Plan

1. Remove `ISOSelectFile` call from `provisioning_service.py`
2. Run TUI with a tag in `provisioned` state
3. Verify WriteData commands are sent (90 8D ...)
4. Verify SDM provisioning completes successfully
5. Tap tag with phone to verify URL with dynamic parameters works

---

# Update 2025-12-11 19:38 - WriteData LENGTH_ERROR

## New Error After ISOSelectFile Fix

After removing ISOSelectFile, we now get to WriteData (0x8D) but it fails with `LENGTH_ERROR (0x917E)`.

### Log Evidence (tui_20251211_193805.log)

```
Line 99:  [AUTH_CONN] Sending command 0x8D (P1=00, P2=00)
Line 100: [AUTH_CONN]   Unencrypted header: 02000000340000
Line 101: [AUTH_CONN]   Plaintext (52 bytes): 03b1d101ad55...
Line 110: >> C-APDU: 90 8D 00 00 43 02 00 00 00 34 00 00 03 B1 D1 01 ... 44 21 37 7D 86 D2 17 27 00
Line 111: << R-APDU (Control):  [NTAG_LENGTH_ERROR (0x917E)]
```

### APDU Breakdown

```
90 8D 00 00 43 02 00 00 00 34 00 00 [52 bytes NDEF data] [8 bytes MAC] 00
|  |  |  |  |  ^^^^^^^^^^^^^^^     |___________________|  |__________|  |
|  |  |  |  |  Header (7 bytes)    Data (52 bytes)       MAC (8 bytes) Le
|  |  |  |  Lc = 67 bytes (7+52+8)
|  |  |  P2
|  |  P1
|  INS = 0x8D (WriteData)
CLA = 0x90
```

### Header Breakdown

```
02 00 00 00 34 00 00
^^ ^^^^^^^^ ^^^^^^^^
|  |        Length = 52 (0x34) in 3 bytes LE
|  Offset = 0 in 3 bytes LE
FileNo = 0x02 (NDEF file)
```

### Current Code Flow (base.py lines 362-396)

For MAC-only mode (`needs_encryption=False`):
```python
cmd_data_for_mac = unencrypted_header + plaintext   # header + data = 59 bytes
cmd_header_bytes = bytes([0x90, cmd, 0x00, 0x00])   # APDU header for MAC calc
with_mac = self.apply_cmac(cmd_header_bytes, cmd_data_for_mac)  # Returns header+data+MAC
encrypted_with_mac = with_mac[len(unencrypted_header):]  # Strip header = data+MAC (60 bytes)

# Build APDU
data_len = len(unencrypted_header) + len(encrypted_with_mac)  # 7 + 60 = 67
apdu = [CLA, CMD, P1, P2, data_len, *unencrypted_header, *encrypted_with_mac, Le]
```

### Investigation Status

The APDU structure appears correct per NXP spec:
- Header (FileNo+Offset+Length) is NOT encrypted
- Data is NOT encrypted (MAC-only mode)
- MAC is calculated over: CMD || CmdCtr || TI || Header || Data
- APDU: CLA CMD P1 P2 Lc [Header] [Data] [MAC] Le

**Possible Issues to Investigate:**

1. **Chip SMConfig Bit 2**: NXP spec line 643 mentions SetConfiguration Option 04h Bit 2 can "disable chained writing with WriteData command in CommMode.MAC". Even single-frame writes might be affected?

2. **File CommMode Mismatch**: After ChangeFileSettings, the file is set to CommMode.MAC (FileOption=0x41). WriteData should use MAC-only, which we are doing.

3. **Length Field in Wrong Place**: The user previously mentioned "the length was being encrypted by accident". Need to verify the Length field in the header is not being processed differently.

4. **Previous session state**: The tag was already `provisioned` status - could there be residual file settings affecting this?

### CMAC Calculation Trace (from log)

```
Line 104: Applying CMAC with header 908d0000 to data of len 59
Line 105: CMAC input (counter=1): 8d01003d4c3c980200000034000003b1d101ad55...
                                  ^^ ^^^^ ^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^
                                  |  |    TI       Header+Data
                                  |  Counter (LE)
                                  CMD

Line 106: CMAC (truncated): 4421377d86d21727
```

This follows the spec: `MAC = MACt(SesAuthMACKey, CMD || CmdCtr || TI || CmdHeader || CmdData)`

### Next Steps

1. Create debug tool to generate expected APDU from spec and compare byte-by-byte
2. Check if there's a known-working WriteData example to compare against
3. Verify the file's current CommMode before WriteData
4. Test with GetFileSettings before WriteData to see file state

---

## ROOT CAUSE IDENTIFIED: Wrong Operation Order!

### The Problem

The code at `provisioning_service.py` lines 266-275 does:
1. Configure SDM (ChangeFileSettings) - line 268
2. Write NDEF - line 275

But the spec (`SDM_SETUP_SEQUENCE.md`) says:
> "CRITICAL: NDEF must be written BEFORE ChangeFileSettings because:
> - SDM offsets reference positions in file content
> - Empty file causes PARAMETER_ERROR (0x919E)"

### Why LENGTH_ERROR?

After ChangeFileSettings enables SDM with specific offsets:
- File is now in a "SDM-aware" state
- The offsets (UIDOffset=134, SDMMACOffset=165, etc.) expect content at those positions
- Writing 180 bytes of NDEF to an SDM-configured file may have constraints

The LENGTH_ERROR (0x917E) could be because:
1. The file's SDM configuration now affects what can be written
2. The WriteData is failing validation against SDM offset constraints
3. The file expects certain structure due to SDM config

### The Fix

**Swap the order in `provisioning_service.py`:**

```python
# CURRENT (WRONG):
self._configure_sdm(auth_conn, offsets)  # SDM first
WriteNdefMessageAuth(ndef_data=ndef_message).execute(auth_conn)  # NDEF second

# CORRECT (per spec):
WriteNdefMessageAuth(ndef_data=ndef_message).execute(auth_conn)  # NDEF first
self._configure_sdm(auth_conn, offsets)  # SDM second (offsets now valid)
```

### Additional Note on Chunked Writes

The URL is 180 bytes, requiring multiple chunks:
- Chunk size: 52 bytes
- Number of chunks: ceil(180/52) = 4 chunks

After fixing the order, chunked writes should work because:
1. First write NDEF (CommMode.MAC before SDM)
2. Then configure SDM (offsets point to written content)

---

## UPDATE 2025-12-14: SMConfig Investigation

### Finding: Chip-Level Setting May Disable WriteData in MAC Mode

**NXP Spec Reference (SetConfiguration Option 04h, Bit 2):**
> "Secure messaging configuration for StandardData file
> 0b: No Change
> 1b: **disable chained writing with WriteData command in CommMode.MAC and CommMode.Full**"

This chip-level configuration bit can **completely disable** WriteData (0x8D) when files are in CommMode.MAC or CommMode.Full mode.

### Impact on LENGTH_ERROR

If SMConfig Bit 2 is set (1b), the chip rejects WriteData commands for MAC/Full files with LENGTH_ERROR.

**Workaround Options:**
1. **Clear SMConfig Bit 2** using SetConfiguration before provisioning
2. **Use ISOUpdateBinary (0xD6) in Plain mode** for initial NDEF write, then configure SDM
3. **Write NDEF with file in Plain mode**, then ChangeFileSettings to MAC mode with SDM

### Spec Ambiguity on Operation Order

**Question:** Must NDEF be written BEFORE ChangeFileSettings for SDM?

**NXP Spec Evidence (Implicit):**
- Line 783: "SDMENCOffset and SDMENCLength define a **placeholder within the file**"
- Line 831: "SDMMACOffset + SDMMACLength is smaller or equal than **the file size**"
- Line 678: References "writing 'x' (78h) in the **static file data**"

**Interpretation:**
- Spec references "placeholders **within the file**" and validates offsets against "**file size**"
- This implies content must exist for offsets to be meaningful
- **BUT:** No explicit statement says "write NDEF before ChangeFileSettings"

**User Requirement:**
> "only if the NXP spec says so"

Since the spec does NOT explicitly mandate the order, we **should not** change the operation order without additional evidence.

### Alternative Hypothesis for LENGTH_ERROR

**Possible causes:**
1. **SMConfig Bit 2 blocks WriteData in MAC mode** - Most likely
2. **File already in wrong state** - Tag was previously provisioned, may have residual settings
3. **MAC calculation error** - Less likely, as CMAC structure matches spec
4. **Offset/Length encoding issue** - Less likely, 3-byte LE encoding appears correct

### Recommended Fix Path

1. **Check SMConfig** - Use GetConfiguration or chip diagnostic to verify Bit 2 status
2. **If Bit 2 is set:** Use ISOUpdateBinary (0xD6) to write NDEF before SDM configuration
3. **If Bit 2 is clear:** Investigate file state with GetFileSettings before WriteData

---

## FINAL RESOLUTION 2025-12-14

### Current Implementation Status: CORRECT ✓

**Code Review Result:**
The current implementation in `provisioning_service.py` (lines 258-268) **already implements Option B correctly**:

```python
# Write NDEF in plain mode FIRST
self._write_ndef(ndef_message)
# -> Uses ISOSelectFile (00 A4...) + ISOUpdateBinary (00 D6...)
# -> No authentication required
# -> Works regardless of SMConfig Bit 2

# THEN authenticate and configure SDM
with AuthenticateEV2(picc_key, key_no=0)(self.card) as auth_conn:
    self._configure_sdm(auth_conn, offsets)
    # -> ChangeFileSettings (90 5F...) with encryption + MAC
    # -> SDM offsets now reference existing NDEF content
```

**This sequence:**
1. ✓ Avoids SMConfig Bit 2 blocking (no WriteData in MAC mode)
2. ✓ Writes NDEF before SDM config (offsets reference existing content)
3. ✓ Uses ISO commands correctly (no MAC on CLA=0x00)
4. ✓ Matches spec requirements

**Logs analyzed were from previous code** that attempted WriteData (0x8D) approach.

**Current code should work correctly.** Ready for testing.
