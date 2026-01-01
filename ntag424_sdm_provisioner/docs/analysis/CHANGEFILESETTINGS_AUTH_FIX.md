# ChangeFileSettings Authentication Fix

**Date:** 2025-12-07
**Status:** CRITICAL - BLOCKER
**Log Reference:** `tui_20251207_182114.log`

---

## Summary - Correct Analysis of Dec 7 Log

I've now analyzed the correct log (`tui_20251207_182114.log` from today). Here's what I found:

### The Issue:

**ChangeFileSettings is being sent PLAIN instead of authenticated** (line 261-263):
- **Sent as:** `90 5F 00 00 0D 02 40 EE E0 ...` (CommMode.Plain)
- **Response:** `NTAG_LENGTH_ERROR (0x917E)`
- **Should be:** Encrypted + CMAC through the authenticated session

Even though we're in SESSION 3 with active auth (Ti=339cba65, counter=0), the ChangeFileSettings command bypasses the auth session.

### What Works Fine:

**NDEF Write with Auto-Chunking** (lines 267-276):
- 80 bytes split into 52 + 28 byte chunks
- Uses ISO UpdateBinary (0x00 0xD6) - CommMode.Plain
- Both chunks succeed perfectly
- No issues with unauthenticated chunking

### Test Sequence for Multi-Chunk Authenticated WriteData:

I've documented in CHAT.md how multi-chunk authenticated writes SHOULD work:

```
SESSION:
  ├─ Auth → Ti, Session keys, counter=0
  ├─ WriteData Chunk 1 (48 bytes, counter=0, Ti) + CMAC
  ├─ WriteData Chunk 2 (48 bytes, counter=1, SAME Ti) + CMAC
  └─ Continue with same Ti, incrementing counter per chunk
```

**Key points:**
- Same Ti across ALL chunks (session persists)
- Counter increments for each chunk
- Separate CMAC for each chunk
- Each chunk is a complete WriteData command with its own offset/length

### Root Cause & Fix:

**ChangeFileSettings is NOT using `AuthenticatedConnection.send()`**. It needs to be sent through the auth session to get proper encryption + CMAC.

---

## The Fix

**Location:** `provisioning_service.py`, SESSION 3

### Current (WRONG):
```python
# Bypasses auth session
change_file_settings.execute(self.connection)
```

### Correct (RIGHT):
```python
# Goes through auth session - encrypted + CMAC
with auth_session as auth_conn:
    auth_conn.send(ChangeFileSettings(...))
```

---

## Expected Behavior After Fix

**Before Fix:**
```
Line 261: ChangeFileSettings (PLAIN) → 90 5F 00 00 0D 02 40 EE E0 ...
Line 263: Response: NTAG_LENGTH_ERROR (0x917E)
```

**After Fix:**
```
ChangeFileSettings (CommMode.Full):
  1. Plaintext: 13 bytes (02 40 EE E0 C1 FE EF 26 00 00 39 00 00 00)
  2. Encrypted with PKCS7 padding: 16 bytes
  3. CMAC calculated: 8 bytes
  4. Total sent: FileNo + Encrypted(16) + CMAC(8) ≈ 25 bytes
  5. Response: OK (0x9100) ✓
```

---

## Impact

**Priority:** CRITICAL - This is the #1 blocker for provisioning

**Affects:**
- All provisioning operations in SESSION 3
- ChangeFileSettings command reliability
- SDM configuration success rate

**Does NOT affect:**
- Key provisioning (SESSION 1 & 2) - these work correctly
- NDEF writes with ISO commands - these work correctly with auto-chunking

---

## Related: Multi-Chunk Authenticated Writes

While fixing ChangeFileSettings, note that **authenticated chunked writes** are a future consideration if we ever need to use WriteData (0x8D) for large payloads instead of ISO UpdateBinary (0xD6).

**Current approach:**
- NDEF writes use ISO UpdateBinary (CommMode.Plain)
- Auto-chunking works perfectly for unauthenticated writes
- No auth session needed

**Future approach (if needed):**
- Use authenticated WriteData (0x8D) with CommMode.MAC
- Chunk large data while maintaining session state
- Each chunk: separate CMAC with incremented counter, same Ti

**Test sequence documented above** shows how this would work.

---

## Verification

After applying the fix, verify:

1. ✅ ChangeFileSettings sent with encryption + CMAC
2. ✅ Response is 0x9100 (not 0x917E)
3. ✅ SDM configuration completes successfully
4. ✅ Full provisioning sequence succeeds
5. ✅ NDEF writes continue to work with auto-chunking

---

## References

- **Log:** `tui_20251207_182114.log` lines 261-276
- **Spec:** `CORRECT_PROVISIONING_SEQUENCE.md` - SESSION 3
- **NXP Datasheet:** Section 10.7.1 ChangeFileSettings (CommMode.Full required)
- **Discussion:** CHAT.md 2025-12-07 (Morpheus analysis)
