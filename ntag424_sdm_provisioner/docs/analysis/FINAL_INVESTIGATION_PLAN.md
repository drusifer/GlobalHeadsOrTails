# Final Investigation Plan - ChangeFileSettings INTEGRITY_ERROR

**Source of Truth:** NXP Section 9 (Secure Messaging) + Section 10.2 (Command List)

**Finding:** Table 22 (line 1793) confirms **ChangeFileSettings uses CommMode.Full** ✅

---

## What We Know Is CORRECT

### ✅ 1. ChangeFileSettings Should Use CommMode.Full
**Per Table 22 line 1793:** `ChangeFileSettings | CommMode.Full`

**Our code:** Uses CommMode.Full ✅

### ✅ 2. Structure per Figure 9
**Command:**
```
CLA: 90
CMD: 5F
P1: 00
P2: 00
Lc: length
Data:
  - FileNo (plain, in CMAC)
  - Encrypted(FileOption + AccessRights + SDM)
  - MAC
Le: 00
```

**Our code:** Matches this structure ✅

### ✅ 3. CMAC Input per Figure 9
```
CMD || CmdCtr || TI || FileNo || Encrypted_Data
```

**Our code:** Matches this ✅

---

## Critical Items to Verify

### Item 1: Extra Padding Block (Section 9.1.4 line 181)

**NXP Spec:**
> "if the plain data is a multiple of 16 bytes already, an additional padding block is added"

**Question:** Does our padding logic do this?

**Test Cases:**
- 3 bytes → 16 bytes (3 + 0x80 + 12 zeros) ✅
- 15 bytes → 16 bytes (15 + 0x80) ✅
- 16 bytes → **32 bytes?** (16 + 0x80 + 15 zeros)
  - **Need to verify!**

**Action:** Check `crypto_primitives.py` padding function

---

### Item 2: Counter Increment Timing (Section 9.1.2)

**NXP Spec (lines 155-157):**
> "When a MAC on a command is calculated at PCD side that includes the CmdCtr, it uses the current CmdCtr. The CmdCtr is afterwards incremented by 1. At PICC side, a MAC appended at received commands is checked using the current value of CmdCtr. If the MAC matches, CmdCtr is incremented by 1 after successful reception of the command, and before sending a response."

**Flow:**
1. PCD: Calculate CMAC with counter N
2. PCD: Increment to N+1
3. PCD: Send command
4. PICC: Check CMAC with counter N
5. PICC: If OK, increment to N+1
6. PICC: Send response

**Our code:**
- Do we increment BEFORE or AFTER calculating CMAC?
- Do we use same counter for IV and CMAC?

**Action:** Review `auth_session.py` counter management

---

### Item 3: IV Construction (Section 9.1.4 lines 187-200)

**NXP Spec:**
```python
IV_cmd = E(SesAuthENCKey, A5 5A || TI || CmdCtr || 00000000_00000000)
```

**Where:**
- CmdCtr is LSB first (2 bytes)
- Encryption uses ECB mode
- CmdCtr is "current" value (before increment)

**Our code:**
- Check IV calculation
- Verify CmdCtr is LSB format
- Verify using ECB for IV

**Action:** Review `crypto_primitives.py` and `auth_session.py`

---

### Item 4: CMAC Truncation (Section 9.1.3 line 171)

**NXP Spec:**
> "The MAC used in NT4H2421Gx is truncated by using only the 8 even-numbered bytes out of the 16 bytes output as described [6] when represented in most-to-least-significant order."

**Translation:**
- 16-byte CMAC: [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
- "even-numbered bytes" = positions 2,4,6,8,10,12,14,16
- In 0-indexed: [1,3,5,7,9,11,13,15]
- **Python:** `cmac[1::2]`

**Our code:** Uses `[1::2]` ✅

**But wait!** "most-to-least-significant order" - does this mean we need to consider endianness?

**Action:** Double-check CMAC truncation

---

## Systematic Testing Plan

### Test 1: Compare with ChangeKey (Which Works!)

**Goal:** Find the ONE difference between ChangeKey (✅) and ChangeFileSettings (❌)

**Both use:**
- CommMode.Full (encrypted)
- Same CMAC format
- Same session keys
- Same counter
- Same TI

**Steps:**
1. Log full ChangeKey command (what we send)
2. Log full ChangeFileSettings command
3. Compare byte-by-byte:
   - CmdHeader handling
   - Padding bytes
   - CMAC input
   - IV calculation

**Action:** Create test script to send both and compare

---

### Test 2: Verify Padding with Block-Aligned Data

**Goal:** Test the "extra padding block" rule

**Test Case:**
- Plain: `01 ee e0` (3 bytes)
  - Padded: `01 ee e0 80 00 00 00 00 00 00 00 00 00 00 00 00` (16 bytes) ✅
  
- Plain: `01 ee e0 ... (13 more bytes)` (16 bytes exact)
  - Padded: **32 bytes?**
  - Expected: `01 ee e0 ... 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
  
**Action:** Test with 16-byte payload

---

### Test 3: Verify Counter State

**Goal:** Ensure counter is correct when command is sent

**Questions:**
- What is counter value after auth?
- Does it increment correctly?
- Is it the same for IV and CMAC?

**Steps:**
1. Complete AuthenticateEV2First
2. Log counter value: should be 0
3. Send ChangeKey (works)
4. Log counter: should be 1
5. Send ChangeFileSettings
6. Log counter: should be 2
7. Check if we're using 2 or 1 for ChangeFileSettings

**Action:** Add counter logging

---

### Test 4: Manual CMAC Calculation

**Goal:** Independently verify CMAC is correct

**Steps:**
1. Get exact command bytes we're sending
2. Extract: CMD, CmdCtr, TI, FileNo, EncryptedData
3. Manually calculate CMAC using PyCryptodome
4. Compare with what we sent
5. If different: find the discrepancy

**Action:** Create standalone verification script

---

## Implementation Review Checklist

### File: `crypto_primitives.py`

- [ ] `pad_iso7816_4()` - does it add extra block for 16-byte input?
- [ ] `calculate_iv()` - uses ECB mode?
- [ ] `calculate_iv()` - CmdCtr is LSB first?
- [ ] `cmac_truncate()` - uses [1::2]? ✅

### File: `auth_session.py`

- [ ] Counter initialized to 0 after auth?
- [ ] Counter incremented AFTER CMAC calculation?
- [ ] Same counter used for IV and CMAC?
- [ ] Counter LSB format in calculations?

### File: `commands/base.py`

- [ ] `encrypt_and_mac_with_header()` - correct order?
- [ ] CMAC input: CMD || Ctr || TI || Header || Encrypted?
- [ ] Padding applied before encryption?

### File: `commands/change_file_settings.py`

- [ ] `get_unencrypted_header()` returns FileNo only?
- [ ] `build_command_data()` returns settings payload?
- [ ] `needs_encryption()` returns True?

---

## Next Immediate Actions

1. **Read crypto_primitives.py** - check padding for 16-byte blocks
2. **Read auth_session.py** - verify counter timing
3. **Create comparison script** - ChangeKey vs ChangeFileSettings
4. **Log everything** - counter, IV, CMAC inputs, encrypted bytes

---

**Status:** Ready to systematically debug
**Priority:** Check padding function FIRST - most likely culprit

