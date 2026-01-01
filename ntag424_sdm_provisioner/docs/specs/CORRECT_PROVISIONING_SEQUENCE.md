# CORRECT PROVISIONING SEQUENCE

**Date:** 2025-12-01
**Status:** AUTHORITATIVE - This is the correct sequence based on NXP datasheet analysis
**Source:** NXP NT4H2421Gx Datasheet Section 10.7.1 + Drew's guidance

---

## Objective

Provision a factory-fresh NTAG424 DNA tag as a secure game coin with:
1. Unique cryptographic keys (not factory defaults)
2. SDM-enabled dynamic URLs with UID, Counter, and CMAC
3. Server-side verification capability

---

## Complete Sequence Diagram

```
Host                                        Tag (NTAG424 DNA)
 │                                           │
 │──────────────────────────────────────────────────────────────
 │ STEP 1: GET TAG STATUS
 │──────────────────────────────────────────────────────────────
 │                                           │
 │──── SelectPiccApplication ────────────────>│
 │<─── OK (9000) ────────────────────────────│
 │                                           │
 │──── GetChipVersion (3 parts) ─────────────>│
 │<─── UID: 04xxxxxxxxxx ────────────────────│
 │                                           │
 │──── GetFileSettings(File 0x02) ───────────>│
 │<─── Access Rights, CommMode, SDM state ───│
 │                                           │
 │──── GetKeyVersion(Key 0) ──────────────────>│
 │<─── Version (0x00 = factory) ─────────────│
 │                                           │
 │──── GetKeyVersion(Key 1) ──────────────────>│
 │<─── Version (0x00 = factory) ─────────────│
 │                                           │
 │──── GetKeyVersion(Key 3) ──────────────────>│
 │<─── Version (0x00 = factory) ─────────────│
 │                                           │
 │ [Decision: Factory or Provisioned?]        │
 │                                           │
 │──────────────────────────────────────────────────────────────
 │ STEP 2: IF FACTORY → SET KEYS FIRST
 │──────────────────────────────────────────────────────────────
 │                                           │
 │ IF (key_version == 0x00):                  │
 │                                           │
 │ [Generate new random keys]                 │
 │ [Save to database: status='pending']       │
 │                                           │
 │ ┌──────────────────────────────────────────────────────┐
 │ │ SESSION 1: Change PICC Master Key (Key 0)           │
 │ └──────────────────────────────────────────────────────┘
 │                                           │
 │──── AuthenticateEV2First(Key 0) ──────────>│
 │     [Using factory key: 0x00...00]         │
 │<─── Challenge (RndB encrypted) ───────────│
 │                                           │
 │──── AuthenticateEV2Second ─────────────────>│
 │     [RndA || RndB']                        │
 │<─── Session Keys Derived ─────────────────│
 │     [Ti, Session ENC, Session MAC]         │
 │                                           │
 │──── ChangeKey(Key 0 → new PICC Master) ───>│
 │     [CommMode.Full: Encrypted + MAC]       │
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │ ⚠️  SESSION 1 INVALIDATED (Key 0 changed) │
 │                                           │
 │ ┌──────────────────────────────────────────────────────┐
 │ │ SESSION 2: Change App Keys (Keys 1 & 3)             │
 │ └──────────────────────────────────────────────────────┘
 │                                           │
 │──── AuthenticateEV2First(Key 0) ──────────>│
 │     [Using NEW PICC Master key]            │
 │<─── Challenge (RndB encrypted) ───────────│
 │                                           │
 │──── AuthenticateEV2Second ─────────────────>│
 │<─── Session Keys Derived ─────────────────│
 │                                           │
 │──── ChangeKey(Key 1 → new App Read) ──────>│
 │     [CommMode.Full: Encrypted + MAC]       │
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │──── ChangeKey(Key 3 → new SDM MAC) ───────>│
 │     [CommMode.Full: Encrypted + MAC]       │
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │ ✅ SESSION 2 ENDS (do NOT do file settings here!)
 │                                           │
 │──────────────────────────────────────────────────────────────
 │ STEP 3: IF KEYS SET → AUTH AND CHANGE FILE SETTINGS
 │──────────────────────────────────────────────────────────────
 │                                           │
 │ IF (keys are custom):                      │
 │                                           │
 │ ┌──────────────────────────────────────────────────────┐
 │ │ SESSION 3: Configure SDM & Write NDEF               │
 │ └──────────────────────────────────────────────────────┘
 │                                           │
 │──── AuthenticateEV2First(Key 0) ──────────>│
 │     [Using current PICC Master key]        │
 │<─── Challenge (RndB encrypted) ───────────│
 │                                           │
 │──── AuthenticateEV2Second ─────────────────>│
 │<─── Session Keys Derived ─────────────────│
 │                                           │
 │──── ChangeFileSettings(File 0x02) ────────>│
 │     [CommMode.Full: Encrypted + MAC]       │
 │     [Enable SDM, set access rights]        │
 │     [Configure offsets: UID, Ctr, MAC]     │
 │<─── OK (9100) ────────────────────────────│
 │                                           │
 │ ✅ SESSION 3 ENDS                          │
 │                                           │
 │ [Write NDEF - Unauthenticated ISO commands]│
 │                                           │
 │──── ISOSelectFile(0xE104) ─────────────────>│
 │<─── OK (9000) ────────────────────────────│
 │                                           │
 │──── ISOUpdateBinary (chunk 1) ────────────>│
 │     [NDEF with placeholders]               │
 │<─── OK (9000) ────────────────────────────│
 │                                           │
 │──── ISOUpdateBinary (chunk 2) ────────────>│
 │<─── OK (9000) ────────────────────────────│
 │                                           │
 │──── ISOUpdateBinary (chunk 3) ────────────>│
 │<─── OK (9000) ────────────────────────────│
 │                                           │
 │──── ISOUpdateBinary (chunk 4 - final) ────>│
 │<─── OK (9000) ────────────────────────────│
 │                                           │
 │ [Update database: status='provisioned']    │
 │                                           │
 │ ✅ PROVISIONING COMPLETE                   │
 │                                           │
```

---

## Critical Rules

### ✅ DO:
1. **Always read tag state first** (Step 1) before attempting changes
2. **Use 3 separate auth sessions:**
   - Session 1: Change Key 0 only
   - Session 2: Change Keys 1 & 3 only
   - Session 3: ChangeFileSettings + Write NDEF
3. **Close each session** after its specific task
4. **Use CommMode.Full** for ChangeKey and ChangeFileSettings (when authenticated)
5. **Use CommMode.Plain** for ISO commands (ISOSelectFile, ISOUpdateBinary)

### ❌ DON'T:
1. **Don't** combine ChangeKey and ChangeFileSettings in the same session
2. **Don't** skip reading tag state (GetFileSettings, GetKeyVersion)
3. **Don't** try to use Session 1 after changing Key 0 (it's invalidated)
4. **Don't** guess the CommMode - it depends on current file access rights

---

## Why This Sequence?

### Problem with 2-Session Approach (Current Code):
```
SESSION 2:
  Auth with NEW Key 0
  ChangeKey(Key 1)      ← OK
  ChangeKey(Key 3)      ← OK
  ChangeFileSettings    ← FAILS with 919E PARAMETER_ERROR!
```

### Why It Fails:
1. The session may be in an invalid state after multiple ChangeKey operations
2. The file's "change" access right may require a fresh authentication
3. Violates separation of concerns: key management vs file configuration

### Correct 3-Session Approach:
- **Session 1:** ONLY change Key 0 (session invalidates)
- **Session 2:** ONLY change Keys 1 & 3 (close session)
- **Session 3:** ONLY configure file + write NDEF (fresh auth context)

---

## State Transitions

```
Factory State
  │ key_version = 0x00
  │ File 0x02 has factory defaults
  │
  ├─> STEP 1: Read status ────> [Confirmed: Factory]
  │
  ├─> STEP 2: Set keys ───────> Keys Changed State
  │    │ key_version = 0x01+
  │    │ Keys are custom
  │    │ SDM NOT configured
  │    │
  │    └─> STEP 3: Configure SDM ──> Provisioned State
  │         │ SDM enabled
  │         │ NDEF written
  │         │ Database: status='provisioned'
  │         │
  │         └────────────────────────> ✅ READY FOR USE
```

---

## Error Recovery

### If Step 2 Fails (Key Change):
- Tag state: Partially provisioned (some keys changed)
- Recovery: Read key versions, determine which keys need changing
- Re-run Step 2 with appropriate old keys for XOR calculation

### If Step 3 Fails (File Settings):
- Tag state: Keys changed, SDM not configured
- Recovery: Can safely re-run Step 3 (keys already set)
- Check: GetFileSettings to see current state

---

## Implementation Checklist

- [ ] Add GetFileSettings command call in Step 1
- [ ] Add GetKeyVersion command calls in Step 1
- [ ] Separate SESSION 2 and SESSION 3 (close after Keys 1 & 3)
- [ ] Create new SESSION 3 for ChangeFileSettings
- [ ] Add state detection logic (factory vs provisioned)
- [ ] Add error recovery for partial provisioning
- [ ] Test sequence with fresh factory tag
- [ ] Verify all 3 sessions complete successfully

---

## References

- **NXP Datasheet:** Section 10.7.1 ChangeFileSettings
- **NXP Datasheet:** Section 10 Command Set (APDU table)
- **Source Discussion:** CHAT.md 2025-12-01 (Drew's 3-step guidance)
