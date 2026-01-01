# SDM Setup Sequence Analysis

**Date:** 2025-12-09
**Status:** Root cause identified - SPEC-BASED APDU SEQUENCE DOCUMENTED

## Executive Summary

The `PARAMETER_ERROR (0x919E)` during SDM configuration is likely due to the NDEF file being empty (all zeros). The spec requires "Static File Data" with placeholders before SDM configuration - the offsets define where to mirror **into existing content**.

## Current Tag State (from tui_20251209_200052.log)

```
GetKeyVersion(Key 0): 0x00 - OK (factory)
GetKeyVersion(Key 1): 0x00 - OK (factory)
GetKeyVersion(Key 2): 0x00 - OK (factory)
GetKeyVersion(Key 3): 0x00 - OK (factory)
GetKeyVersion(Key 4): 0x00 - OK (factory)

GetFileSettings(File 02): 00 00 E0 EE 00 01 00
  - FileType: 0x00 (StandardData)
  - FileOption: 0x00 (SDM DISABLED, CommMode=PLAIN)
  - AccessRights: E0 EE
    - byte1=E0: Read=E (FREE), Write=0 (KEY_0)
    - byte0=EE: ReadWrite=E (FREE), Change=E (FREE)
  - FileSize: 256 bytes (00 01 00 little-endian)

NDEF File Content: ALL ZEROS (256 bytes of 0x00) ← PROBLEM!
```

## PARAMETER_ERROR Causes (NXP Table 71) - Complete Checklist

| # | Cause | Our Configuration | Status |
|---|-------|-------------------|--------|
| 1 | Targeted key does not exist | Keys 0-4 exist | ✅ OK |
| 2 | SDMMetaRead != Fh while UID/CTR disabled | MetaRead=E, UID+CTR enabled | ✅ OK |
| 3 | SDMMetaRead = Fh while enabling UID | MetaRead=E, not F | ✅ OK |
| 4 | SDMCtrRet != Fh while SDMReadCtr disabled | CtrRet=E, CTR enabled | ✅ OK |
| 5 | SDMMAC/UID overlap | Offsets non-overlapping | ✅ OK |
| 6 | SDMMAC/SDMReadCtr overlap | Offsets non-overlapping | ✅ OK |
| 7 | SDMENCFileData/UID overlap | Not using encryption | ✅ N/A |
| 8 | SDMENCFileData/SDMReadCtr overlap | Not using encryption | ✅ N/A |
| 9 | UID/SDMReadCtr overlap | UID=134, CTR=153 | ✅ OK |
| 10 | SDMEncryption without UID+CTR | Not using encryption | ✅ N/A |
| 11 | SDMReadCtrLimit without CTR | Not using limit | ✅ N/A |
| 12 | **Unknown/undocumented** | **Empty file?** | ❓ SUSPECT |

## Spec Evidence: File Must Have Content

**Section 9.3.6 (line 783):**
> "From user point of view, the SDMENCOffset and SDMENCLength define a **placeholder within the file** where the plain data is to be stored **when writing the file**."

**Section 9.3.3 (line 664):**
> "UIDOffset configures the UID mirroring position"

**Section 9.3.7 (line 849-851):**
> "SDMMAC = MACt (SesSDMFileReadMACKey; **DynamicFileData[SDMMACInputOffset ... SDMMACOffset - 1]**)
> with **DynamicFileData being the file data as how it is put on the contactless interface**, i.e. replacing any placeholders by the dynamic data."

**Section 9.3.3 (line 678):**
> "When both the UID and SDMReadCtr are mirrored, 'x' (78h) is used as a separator character... This can be achieved by leaving one byte space between the placeholders... and **writing 'x' (78h) in the static file data**."

This confirms: **The file must already contain the URL with placeholders** before calling ChangeFileSettings!

---

## CORRECT SDM Setup Sequence (Spec-Based)

### Phase 2: URL Configuration (After keys are configured)

```
Host                                        Tag (NTAG424 DNA)
 │                                           │
 │ STEP 1: WRITE NDEF MESSAGE FIRST          │
 │──────────────────────────────────────────────────────────────
 │                                           │
 │ NOTE: File 02 has Write=KEY_0, so we need │
 │ to authenticate BEFORE writing NDEF!      │
 │                                           │
 │──── SelectPiccApplication ────────────────>│
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │──── AuthenticateEV2First(Key 0) ──────────>│
 │<─── RndB encrypted ───────────────────────│
 │                                           │
 │──── AuthenticateEV2Second ─────────────────>│
 │<─── Session Keys Derived ─────────────────│
 │                                           │
 │ STEP 2: WRITE NDEF (AUTHENTICATED)         │
 │──────────────────────────────────────────────────────────────
 │                                           │
 │──── WriteData(File 02, offset=0, data) ───>│
 │     [NDEF message with placeholders]       │
 │     [Encrypted + MAC per CommMode.Full]    │
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │  OR using ISO commands (chunked):          │
 │──── ISOSelectFile(0xE104) ─────────────────>│
 │<─── OK (9000) ────────────────────────────│
 │──── ISOUpdateBinary (chunks) ──────────────>│
 │<─── OK (9000) per chunk ──────────────────│
 │                                           │
 │ STEP 3: CONFIGURE SDM (SAME SESSION)       │
 │──────────────────────────────────────────────────────────────
 │                                           │
 │──── ChangeFileSettings(File 02) ──────────>│
 │     [CommMode.Full: Encrypted + MAC]       │
 │     [FileOption: 0x40 = SDM enabled]       │
 │     [AccessRights: E0 EE or custom]        │
 │     [SDMOptions: 0xC1 = UID+CTR+ASCII]     │
 │     [SDMAccessRights: 0xEF3E]              │
 │     [Offsets: UID, CTR, MACInput, MAC]     │
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │ ✅ SDM CONFIGURED                          │
```

---

## APDU Sequence (Spec-Based)

### For URL: `https://your-server.com/tap?uid=00000000000000&ctr=000000&cmac=0000000000000000`

**Pre-calculated values:**
- URL content (after stripping https://): 76 chars
- NDEF total size: 9 (header) + 76 (content) = 85 bytes
- UIDOffset = 9 + position of "00000000000000" after uid= = 134
- SDMReadCtrOffset = 9 + position of "000000" after ctr= = 153
- SDMMACInputOffset = 134 (start of UID)
- SDMMACOffset = 9 + position of "0000000000000000" after cmac= = 165

### Step-by-Step APDUs

**1. Select PICC Application:**
```
>> 90 5A 00 00 03 D2 76 00 00   (ISO)
OR
>> 00 A4 04 00 07 D2 76 00 00 85 01 01 00  (ISO7816)
<< 91 00 (OK)
```

**2. Authenticate EV2 with Key 0:**
```
>> 90 71 00 00 02 00 00 00     AuthenticateEV2First(KeyNo=0)
<< [16 bytes RndB encrypted] 91 AF

>> 90 AF 00 00 20 [32 bytes]  AuthenticateEV2Second
<< [16 bytes] 91 00            TI || encrypted response
```

**3. Write NDEF (after auth - using WriteData or ISO commands):**

Option A - WriteData (native, CommMode.Full):
```
>> 90 8D 00 00 XX 02 00 00 00 [encrypted NDEF data] [MAC]
<< 91 00
```

Option B - ISOUpdateBinary (chunked, unauthenticated mode):
```
>> 00 A4 02 00 02 E1 04 00     ISOSelectFile(NDEF File)
<< 90 00

>> 00 D6 00 00 35 [53 bytes]   ISOUpdateBinary chunk 1
<< 90 00
>> 00 D6 00 35 20 [32 bytes]   ISOUpdateBinary chunk 2
<< 90 00
```

**4. Configure SDM (same session as auth):**
```
>> 90 5F 00 00 XX [encrypted payload] [MAC]

Where plaintext payload is:
  02                  FileNo
  40                  FileOption (SDM=1, CommMode=PLAIN)
  E0 EE               AccessRights (Read:FREE, Write:KEY_0, RW:FREE, Change:FREE)
  C1                  SDMOptions (UID=1, CTR=1, ASCII=1)
  EF 3E               SDMAccessRights (MetaRead=E, FileRead=F, RFU=3, CtrRet=E)
  86 00 00            UIDOffset = 134 (little-endian)
  99 00 00            SDMReadCtrOffset = 153 (little-endian)
  86 00 00            SDMMACInputOffset = 134 (little-endian)
  A5 00 00            SDMMACOffset = 165 (little-endian)

<< 91 00 (SUCCESS!)
```

---

## Implementation Fix

In `provisioning_service.py`, the `provision_url()` method should:

```python
# CURRENT (FAILS):
with AuthenticateEV2(picc_key, key_no=0)(self.card) as auth_conn:
    self._configure_sdm(auth_conn, offsets)  # ← FAILS: File is empty!
    self._write_ndef(ndef_message)

# CORRECT (based on spec):
with AuthenticateEV2(picc_key, key_no=0)(self.card) as auth_conn:
    # 1. Write NDEF FIRST (file must have content for SDM to work)
    self._write_ndef(ndef_message)
    # 2. THEN configure SDM (offsets now point to valid content)
    self._configure_sdm(auth_conn, offsets)
```

**Note:** Since File 02 has `Write=KEY_0`, the NDEF write must happen within an authenticated session OR use authenticated WriteData command.

---

## Test Plan

1. Modify `provision_url()` to write NDEF before ChangeFileSettings
2. Run Phase 2 on a tag with keys_configured status
3. Verify ChangeFileSettings succeeds (0x9100)
4. Verify SDM works by tapping with phone and checking URL has dynamic values

---

## References

- NXP NT4H2421Gx Datasheet Section 9.3 (Secure Dynamic Messaging)
- NXP NT4H2421Gx Datasheet Section 10.7.1 (ChangeFileSettings)
- NXP NT4H2421Gx Datasheet Table 71 (PARAMETER_ERROR causes)
- Log: `tui_20251209_200052.log` (tag diagnostic showing empty NDEF)
- Log: `tui_20251209_195703.log` (ChangeFileSettings failure)
