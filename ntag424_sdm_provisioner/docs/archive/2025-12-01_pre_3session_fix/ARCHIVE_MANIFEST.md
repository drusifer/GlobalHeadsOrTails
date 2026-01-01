# Archive Manifest - 2025-12-01 Pre-3-Session Fix

**Date:** 2025-12-01
**Reason:** These documents describe a 2-session provisioning approach that conflicts with the correct 3-session sequence

---

## Authoritative Replacement

**NEW SPEC (Correct):**
- `docs/specs/CORRECT_PROVISIONING_SEQUENCE.md`
  - 3-session approach (SESSION 1, 2, 3)
  - Based on NXP datasheet analysis and Drew's guidance
  - ChangeFileSettings in separate SESSION 3

---

## Archived Documents

### 1. `EXAMPLE_22_UPDATED.md.archived`
**Conflict:** Describes 2-session approach
- Line 33: "6. Re-authenticate with new PICC Master Key"
- Line 34: "7. Configure SDM (ChangeFileSettings)"
- **Problem:** SDM config happens in same session as key changes

**What was wrong:**
```
SESSION 2:
  - Auth with NEW Key 0
  - ChangeKey(1, 3)
  - ChangeFileSettings  ← Causes 919E error
```

**Correct approach:**
```
SESSION 2: Auth → ChangeKey(1, 3) → END
SESSION 3: Auth → ChangeFileSettings → Write NDEF
```

---

### 2. `TOOL_ARCHITECTURE_COMPLETE.md.archived`
**Conflict:** References provision_factory_tool.py which uses 2-session approach
- Line 24: "provision_factory_tool.py (~250 lines) - Full provisioning flow"

**Status:** Tool architecture is valid, but provisioning implementation needs update

---

## Migration Notes

### Code Changes Required:
1. Update `provisioning_service.py` to use 3 sessions
2. Add GetFileSettings and GetKeyVersion in Step 1
3. Separate ChangeFileSettings into SESSION 3
4. Update provision_factory_tool.py to match new sequence

### Documentation Changes:
- Reference `CORRECT_PROVISIONING_SEQUENCE.md` as authoritative
- Update any tool documentation to reflect 3-session approach

---

## Historical Context

These documents were created during earlier provisioning work when we thought the 2-session approach was correct. The 919E error on ChangeFileSettings led us to discover that ChangeFileSettings needs to be in a separate authentication session.

**Discovery:** 2025-12-01 log analysis revealed ChangeFileSettings failing when executed in same session as ChangeKey commands.

**Root Cause:** File settings changes require a fresh authentication context, not one that's been "used" for key changes.
