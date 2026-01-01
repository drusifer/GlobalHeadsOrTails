# Section 9 Analysis Plan - Systematic Review

**Goal:** Compare NXP Section 9 (source of truth) with our implementation to find discrepancies.

---

## Phase 1: Read and Document Section 9 Requirements

### 9.1.2 Command Counter (Lines 149-161)
**NXP Spec Says:**
- [ ] CmdCtr reset to 0000h after successful AuthenticateEV2First
- [ ] Represented LSB first in calculations
- [ ] PCD calculates MAC with current CmdCtr, THEN increments by 1
- [ ] PICC checks MAC with current CmdCtr, increments by 1 AFTER successful command
- [ ] For CommMode.Full: non-increased value for command, increased value for response
- [ ] Command chaining doesn't affect counter (single command)

**Our Implementation:**
- [ ] Check: Counter initialized to 0
- [ ] Check: Counter in LSB format
- [ ] Check: We increment AFTER successful command (not before MAC)
- [ ] Check: IV uses same counter as CMAC

### 9.1.3 MAC Calculation (Lines 163-175)
**NXP Spec Says:**
- [ ] CMAC per NIST SP 800-38B
- [ ] Truncated by "8 even-numbered bytes" = bytes at positions 2,4,6,8,10,12,14,16 = indices [1::2]
- [ ] IV for CMAC: zero byte IV

**Our Implementation:**
- [ ] Check: Using CMAC from PyCryptodome
- [ ] Check: Truncation [1::2] (odd indices)
- [ ] Check: Zero IV for CMAC

### 9.1.4 Encryption (Lines 177-204)
**NXP Spec Says:**
- [ ] AES-128 CBC mode
- [ ] Padding: ISO/IEC 9797-1 Method 2 = 0x80 + zeros
- [ ] "If plain data is multiple of 16 bytes already, an additional padding block is added"
- [ ] Exception: No padding during authentication itself
- [ ] IV = E(SesAuthENCKey, A5 5A || TI || CmdCtr || zeros) using ECB mode
- [ ] IV uses current (non-incremented) CmdCtr

**Our Implementation:**
- [ ] Check: CBC mode
- [ ] Check: 0x80 padding
- [ ] Check: Extra block if already aligned? **CRITICAL**
- [ ] Check: IV calculation matches
- [ ] Check: IV uses ECB mode

### 9.1.9 MAC Communication Mode (Lines 331-374)
**NXP Spec Says:**
- [ ] MAC calculated over: Cmd || CmdCtr || TI || [CmdHeader] || [CmdData]
- [ ] MAC appended to unpadded plain command
- [ ] If MAC invalid: INTEGRITY_ERROR, auth lost, no MAC in error response

**Our Implementation:**
- [ ] Check: MAC input format
- [ ] Check: CmdHeader handling

### 9.1.10 Full Communication Mode (Lines 376-395)
**NXP Spec Says:**
- [ ] Data encrypted first, then MACed
- [ ] MAC over: Cmd || CmdCtr || TI || [CmdHeader] || [E(encrypted data)]
- [ ] Padding applied before encryption
- [ ] If padding invalid: INTEGRITY_ERROR

**Our Implementation:**
- [ ] Check: Encrypt then MAC order
- [ ] Check: CmdHeader in MAC calculation
- [ ] Check: Padding validation

---

## Phase 2: Critical Items to Verify

### CRITICAL #1: Extra Padding Block (Line 181)
**Spec:** "if the plain data is a multiple of 16 bytes already, an additional padding block is added"

**Question:** Does this apply to ChangeFileSettings or only to file data?
**Test:** Try 16-byte payload - does it need 32 bytes (16 + 16 padding)?

### CRITICAL #2: CmdHeader in CMAC
**Spec:** "Cmd || CmdCtr || TI || [CmdHeader] || [CmdData or Encrypted]"

**Question:** For ChangeFileSettings:
- Is FileNo the CmdHeader?
- Should it be in encrypted data or separate?

### CRITICAL #3: CommMode for ChangeFileSettings
**Spec Section 10.7.1:** "The communication mode can be either CommMode.Plain or CommMode.Full based on current access right of the file"

**Question:** 
- Current file: Change=KEY_0 (requires auth)
- Should we use CommMode.Full (encrypted)?
- Or does "based on current access right" mean something else?

---

## Phase 3: Systematic Testing Plan

### Test 1: Verify Counter Handling
- [ ] Log counter before/after each command
- [ ] Verify it's used correctly in IV and CMAC
- [ ] Check it increments at right time

### Test 2: Verify Padding for Block-Aligned Data
- [ ] Test with exactly 16-byte payload
- [ ] Check if we add extra 16-byte padding block
- [ ] Compare with spec line 181

### Test 3: Verify CMAC Input Format
- [ ] Print exact CMAC input bytes
- [ ] Compare with Figure 8 and Figure 9 from Section 9
- [ ] Verify CmdHeader position

### Test 4: Check Authentication State
- [ ] Verify we're actually authenticated when sending command
- [ ] Check if auth state persists across commands
- [ ] Verify Ti and session keys are correct

---

## Phase 4: Implementation Review

### Files to Review Against Section 9:
1. `src/ntag424_sdm_provisioner/crypto/auth_session.py`
   - Counter management
   - CMAC calculation
   - IV calculation

2. `src/ntag424_sdm_provisioner/crypto/crypto_primitives.py`
   - Padding logic
   - Truncation logic
   - Encryption

3. `src/ntag424_sdm_provisioner/commands/base.py`
   - encrypt_and_mac_with_header
   - encrypt_and_mac_no_padding
   - send() method

4. `src/ntag424_sdm_provisioner/commands/change_file_settings.py`
   - needs_encryption()
   - get_unencrypted_header()
   - build_command_data()

---

## Next Steps

1. **Read Section 9.1.10 (Full Communication Mode) in detail** - This is what ChangeFileSettings should use
2. **Compare Figure 9 with our encrypted command structure**
3. **Check if "additional padding block" rule applies**
4. **Verify CmdHeader is in correct position**
5. **Create test that exactly matches an NXP example from Section 9**

---

**Status:** Ready to begin systematic analysis

