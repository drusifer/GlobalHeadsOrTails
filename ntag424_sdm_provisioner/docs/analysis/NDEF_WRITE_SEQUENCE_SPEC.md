# NDEF Write Sequence Specification

**Purpose:** Document the correct APDU sequence for authenticated NDEF writes to NTAG424 DNA tags.  
**Date:** 2025-12-01  
**Status:** Investigation - Fixing LENGTH_ERROR (0x917E)

---

## Problem Statement

We're getting `NTAG_LENGTH_ERROR (0x917E)` when attempting to write NDEF data after authentication.

### Current (Failing) Sequence

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Host                                                    Tag               │
│   │                                                       │                │
│   │──── SelectPiccApplication ──────────────────────────▶│                │
│   │     [00 A4 04 00 07 D2 76 00 00 85 01 01 00]          │                │
│   │◀──── ✓ OK (0x9000) ─────────────────────────────────│                │
│   │                                                       │                │
│   │──── GetChipVersion ─────────────────────────────────▶│                │
│   │     [90 60 00 00 00]                                  │                │
│   │◀──── ✓ OK (0x9100) with UID ────────────────────────│                │
│   │                                                       │                │
│   │──── AuthenticateEV2First (Key 0) ───────────────────▶│                │
│   │     [90 71 00 00 02 00 00 00]                         │                │
│   │◀──── ✓ RndB encrypted ──────────────────────────────│                │
│   │                                                       │                │
│   │──── AuthenticateEV2First Part 2 ────────────────────▶│                │
│   │     [90 AF 00 00 20 {RndA||RndB'} 00]                 │                │
│   │◀──── ✓ Session established ─────────────────────────│                │
│   │      Ti=6f4a04ff, Counter=0                           │                │
│   │                                                       │                │
│   │──── ISOSelectFile (NDEF_FILE E104) ─────────────────▶│                │
│   │     [00 A4 02 00 02 E1 04 00]                         │                │
│   │◀──── ✓ OK (0x9000) ─────────────────────────────────│                │
│   │                                                       │                │
│   │──── ISOUpdateBinary + MAC (WRONG!) ─────────────────▶│  ❌ WRONG CMD  │
│   │     [90 D6 00 00 5A {offset}{80-byte NDEF}{8-byte MAC} 00]             │
│   │◀──── ❌ LENGTH_ERROR (0x917E) ──────────────────────│                │
│   │                                                       │                │
└────────────────────────────────────────────────────────────────────────────┘
```

### Root Cause Analysis

From NXP NT4H2421Gx Datasheet Table 22 (Command Set):

| Command          | CLA | INS | Communication Mode           |
|------------------|-----|-----|------------------------------|
| ISOUpdateBinary  | 00  | D6  | **CommMode.Plain ONLY**      |
| WriteData        | 90  | 8D  | Comm. mode of targeted file  |

**Issue #1:** `ISOUpdateBinary (0xD6)` does **NOT support secure messaging** (MAC or Full encryption). It only works in `CommMode.Plain`.

**Issue #2:** We're using CLA=`0x90` with INS=`0xD6`, mixing native and ISO command formats.

**Issue #3:** Frame size exceeds limit. The APDU `5A` = 90 bytes of data, which is too large for a single frame with authenticated overhead.

---

## Correct Sequence (Per NXP Spec Section 10.8.2)

### Option A: Use Native WriteData Command (0x8D)

For authenticated writes, use **WriteData (0x8D)** which respects the file's communication mode.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Host                                                    Tag               │
│   │                                                       │                │
│   │──── SelectPiccApplication ──────────────────────────▶│                │
│   │     [00 A4 04 00 07 D2 76 00 00 85 01 01 00]          │                │
│   │◀──── ✓ OK (0x9000) ─────────────────────────────────│                │
│   │                                                       │                │
│   │──── GetChipVersion ─────────────────────────────────▶│                │
│   │     [90 60 00 00 00]                                  │                │
│   │◀──── ✓ OK (0x9100) with UID ────────────────────────│                │
│   │                                                       │                │
│   │──── AuthenticateEV2First (Key 0) ───────────────────▶│                │
│   │◀──── ✓ Session established ─────────────────────────│                │
│   │      Ti=XXXXXXXX, Counter=0                           │                │
│   │                                                       │                │
│   │──── WriteData (File 0x02, offset 0, 80 bytes) ──────▶│                │
│   │     [90 8D 00 00 XX 02 00 00 00 50 00 00 {DATA} {MAC} 00]              │
│   │     FileNo=0x02, Offset=0x000000, Length=0x000050     │                │
│   │     + CommMode.MAC: append 8-byte truncated CMAC      │                │
│   │◀──── ✓ OK (0x9100) ─────────────────────────────────│                │
│   │      Counter incremented to 1                         │                │
│   │                                                       │                │
└────────────────────────────────────────────────────────────────────────────┘
```

### WriteData Command Format (Section 10.8.2)

```
┌─────┬─────┬────┬────┬────┬────┬────────┬────────┬────────┬────────────────┬────┐
│ CLA │ INS │ P1 │ P2 │ Lc │ Le │ FileNo │ Offset │ Length │ Data           │ Le │
│ 90  │ 8D  │ 00 │ 00 │ XX │ 00 │ 1 byte │ 3 bytes│ 3 bytes│ up to 248 bytes│ 00 │
└─────┴─────┴────┴────┴────┴────┴────────┴────────┴────────┴────────────────┴────┘

For NDEF file (0x02) at offset 0 with 80 bytes:
- FileNo = 0x02
- Offset = 0x00 0x00 0x00 (LSB first)
- Length = 0x50 0x00 0x00 (80 = 0x50, LSB first)
```

### CommMode.MAC Format (Section 9.1.9)

For commands with MAC protection:

```
MAC Input = CMD || CmdCtr || TI || CmdHeader || CmdData
         = 8D  || 0000   || Ti || 02 000000 500000 || {80 bytes NDEF}

Full APDU = [90 8D 00 00 Lc] [FileNo Offset Length] [Data] [MAC_truncated] [00]
          = [90 8D 00 00 5B] [02 00 00 00 50 00 00] [80 bytes] [8 bytes MAC] [00]
          
Total Data = 7 (header) + 80 (data) + 8 (MAC) = 95 bytes
```

### Data Size Limits

Per spec Table 81:
- **Data:** "up to 248 bytes including secure messaging"
- With MAC: 248 - 8 = 240 bytes max plaintext
- With Full: (248 - 8) / block * 16 - padding = ~224 bytes max plaintext

Our 80-byte NDEF + 7-byte header + 8-byte MAC = **95 bytes** → Should fit in single frame!

---

## Option B: Use ISOUpdateBinary Without MAC

If NDEF file is configured for `CommMode.Plain` (no MAC required):

```
│   │──── ISOSelectFile (NDEF_FILE E104) ─────────────────▶│                │
│   │     [00 A4 02 00 02 E1 04 00]                         │                │
│   │◀──── ✓ OK (0x9000) ─────────────────────────────────│                │
│   │                                                       │                │
│   │──── ISOUpdateBinary (offset 0, 80 bytes) ───────────▶│  ✓ PLAIN ONLY  │
│   │     [00 D6 00 00 50 {80-byte NDEF data}]              │                │
│   │◀──── ✓ OK (0x9000) ─────────────────────────────────│                │
```

**Note:** This only works if:
1. NDEF file (0x02) has `CommMode.Plain` configured
2. Write access is granted (either free or auth state checked)

---

## Implementation Fix

### Root Cause #2: Wrong Order

The provisioning flow was writing NDEF **before** configuring file settings.
The NDEF file starts in `CommMode.Plain` - sending a MAC causes LENGTH_ERROR.

### Correct Flow Order

```python
# provisioning_service.py - CORRECT ORDER

# 1. Authenticate with Key 0
auth_conn = self._authenticate(current_keys)

# 2. Configure SDM settings FIRST (sets CommMode.MAC on NDEF file)
self._configure_sdm(auth_conn, offsets)

# 3. Write NDEF (NOW file is in CommMode.MAC, WriteData with MAC works)
self._write_ndef_authenticated(auth_conn, ndef_message)
```

### WriteData Implementation

```python
# Use native WriteData (0x8D) with MAC
def _write_ndef_authenticated(self, auth_conn, ndef_message):
    auth_conn.send(WriteDataAuth(
        file_no=0x02,          # NDEF file
        offset=0,              # Start of file
        data=ndef_message      # NDEF data
    ))
```

### Required: Create WriteDataAuth Command

```python
class WriteDataAuth(AuthApduCommand):
    """Native WriteData with CommMode.MAC support."""
    
    def __init__(self, file_no: int, offset: int, data: bytes):
        super().__init__(use_escape=True)
        self.file_no = file_no
        self.offset = offset
        self.data = data
    
    def get_command_byte(self) -> int:
        return 0x8D  # WriteData
    
    def get_unencrypted_header(self) -> bytes:
        # FileNo + Offset (3 bytes) + Length (3 bytes)
        return bytes([
            self.file_no,
            self.offset & 0xFF,
            (self.offset >> 8) & 0xFF,
            (self.offset >> 16) & 0xFF,
            len(self.data) & 0xFF,
            (len(self.data) >> 8) & 0xFF,
            (len(self.data) >> 16) & 0xFF,
        ])
    
    def needs_encryption(self) -> bool:
        return False  # CommMode.MAC = plaintext + MAC
    
    def build_command_data(self) -> bytes:
        return self.data
```

---

## Command Chaining (If Data > ~55 bytes per frame)

For very large writes that exceed frame limits, use ISO 14443-4 chaining:

```
│   │──── WriteData (chunk 1, 55 bytes) ──────────────────▶│                │
│   │     [90 8D 00 00 XX ...data... 00]                    │                │
│   │◀──── MORE_FRAMES (0x91AF) ──────────────────────────│                │
│   │                                                       │                │
│   │──── AdditionalFrame (chunk 2) ──────────────────────▶│                │
│   │     [90 AF 00 00 XX ...more data... 00]               │                │
│   │◀──── MORE_FRAMES (0x91AF) ──────────────────────────│                │
│   │                                                       │                │
│   │──── AdditionalFrame (final chunk + MAC) ────────────▶│                │
│   │     [90 AF 00 00 XX ...last data + MAC... 00]         │                │
│   │◀──── OK (0x9100) ───────────────────────────────────│                │
```

**Important (Section 9.1.2):** 
- MAC is calculated over the ENTIRE chained data
- Counter increments only ONCE after complete command
- Each chunk is NOT independently MACed

---

## Summary

| Approach | Command | INS | CommMode | Our Case |
|----------|---------|-----|----------|----------|
| ❌ Current | ISOUpdateBinary | 0xD6 | Plain only | Fails with MAC |
| ✅ Fix | WriteData | 0x8D | Per file config | Supports MAC |

**Action Items:**
1. Create `WriteDataAuth` command class using INS=0x8D
2. Update `_write_ndef_authenticated()` to use `WriteDataAuth`
3. MAC is calculated over: `CMD || CmdCtr || TI || Header || Data`
4. Counter increments after successful write

---

## References

- NXP NT4H2421Gx Datasheet Rev. 3.0, Section 10.8.2 (WriteData)
- NXP NT4H2421Gx Datasheet Rev. 3.0, Section 9.1.9 (MAC Communication Mode)
- NXP NT4H2421Gx Datasheet Rev. 3.0, Table 22 (Command APDUs)

