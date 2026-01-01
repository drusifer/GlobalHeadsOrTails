# Section 9 Comparison: NXP Spec vs Our Implementation

**Purpose:** Systematic comparison to find the bug causing INTEGRITY_ERROR (0x911E)

---

## Summary From Section 9

### Figure 9: CommMode.Full Structure

**Command APDU:**
```
CLA: 90h
Cmd: (command byte, e.g., 0x5F)
P1: 00h
P2: 00h
Lc: length of [CmdHeader + Encrypted + MAC]
Data Field:
  - CmdHeader [a bytes] - NOT encrypted, but IS in CMAC
  - E(SesAuthENCKey, CmdData) [b+p bytes] - Encrypted with padding
  - MAC [8 bytes] - Over CMD || CmdCtr || TI || CmdHeader || Encrypted
Le: 00h
```

**CMAC Input (per Figure 9 line 393):**
```
CMD || CmdCtr || TI || [CmdHeader] || [E(SesAuthENCKey, CmdData)]
```

**Key Points:**
1. CmdHeader is **PLAIN** (not encrypted)
2. CmdHeader **IS** included in CMAC
3. CmdData is **ENCRYPTED** before CMAC
4. MAC is over **ENCRYPTED** data, not plaintext

---

## ChangeFileSettings Specifics (Section 10.7.1)

**Table 69 Classification:**

**Command Header Parameters:**
- Cmd: 0x5F
- FileNo: 1 byte

**Command Data Parameters:**
- FileOption: 1 byte
- AccessRights: 2 bytes
- SDMOptions: [optional, if FileOption bit 6 set]
- SDMAccessRights: [optional]
- Offsets: [optional, 3 bytes each]

**This means:**
- **CmdHeader** = FileNo (1 byte, plain)
- **CmdData** = FileOption + AccessRights + SDM fields (encrypted)

---

## Our Implementation Review

### What We're Doing

```python
# In ChangeFileSettingsAuth:
def get_unencrypted_header(self) -> bytes:
    return bytes([self.config.file_no])  # FileNo

def build_command_data(self) -> bytes:
    return build_sdm_settings_payload(self.config)  # FileOption + AccessRights + SDM
```

### In AuthenticatedConnection.send():

```python
cmd = command.get_command_byte()  # 0x5F
unencrypted_header = command.get_unencrypted_header()  # FileNo
plaintext = command.build_command_data()  # Settings payload

# Encrypt plaintext
encrypted = self.encrypt_data(plaintext)  # With 0x80 padding

# CMAC over: Cmd || Ctr || Ti || Header || Encrypted
cmd_data_for_mac = unencrypted_header + encrypted
with_cmac = self.apply_cmac(cmd_header_bytes, cmd_data_for_mac)

# Build APDU: CLA CMD P1 P2 LC Header Encrypted MAC LE
```

**This matches Figure 9!** ✅

---

## Critical Questions to Answer

### Q1: Padding for Block-Aligned Data

**Spec (Section 9.1.4 line 181):**
> "if the plain data is a multiple of 16 bytes already, an additional padding block is added"

**Our 3-byte payload:**
- 3 bytes → pad to 16 bytes ✅ (not a multiple of 16)

**Our 16-byte test:**
- 16 bytes → Should become 32 bytes (16 + 16 padding block)?
- **Need to verify:** Did we test this?

### Q2: Encryption Exception

**Spec (Section 9.1.4 line 181):**
> "The only exception is during the authentication itself (AuthenticateEV2First and AuthenticateEV2NonFirst), where no padding is applied at all."

**Question:** Does this exception apply to ANY command during auth, or only to the auth commands themselves?

### Q3: Which Commands Use CommMode.Full?

**Spec says:** "all commands listed as such in Section 10.2"

**Action:** Need to check Section 10.2 to see if ChangeFileSettings is listed!

---

## Investigation Plan

### Step 1: Check Section 10.2 - Which Commands Use Full Mode?
- [ ] Read Section 10.2
- [ ] Find if ChangeFileSettings is listed for CommMode.Full
- [ ] Check if there are conditions/exceptions

### Step 2: Verify Padding Logic for Block-Aligned Data
- [ ] Re-test with 16-byte payload
- [ ] Check if we add extra padding block (should be 32 bytes total)
- [ ] Compare with spec line 181

### Step 3: Compare ChangeKey (Works) vs ChangeFileSettings (Fails)
- [ ] Both use same crypto
- [ ] Both use CmdHeader + CmdData pattern
- [ ] Find the ONE difference between them

### Step 4: Check Authentication State
- [ ] Verify auth doesn't expire between commands
- [ ] Check if Ti/session keys are still valid
- [ ] Verify counter management

---

## Next Action

**Immediately:** Read Section 10.2 to see which commands are supposed to use CommMode.Full!

This is CRITICAL - maybe ChangeFileSettings isn't supposed to use encryption at all, even when authenticated?

