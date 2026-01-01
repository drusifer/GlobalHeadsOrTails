# [Bob] State Management Issue Analysis

**Date**: 2025-11-27  
**Issue**: Agent state files not being created, context lost between persona switches

## Root Cause

**Templates exist but aren't being used:**
- ✅ `agents/_template_current_task.md`
- ✅ `agents/_template_context.md`  
- ✅ `agents/_template_next_steps.md`

**Problem**: Persona prompts don't explicitly require creating/updating these files.

## Current State

**Each persona.docs/ folder should contain:**
1. `current_task.md` - What the persona is working on RIGHT NOW
2. `context.md` - Recent decisions, findings, blockers
3. `next_steps.md` - What to do when resumed

**Reality**: Only the main `*_AGENT.md` files exist. No state files.

## Proposed Solution

### 1. State File Protocol (NEW)

**ENTRY (when persona activates):**
```markdown
1. Read `agents/CHAT.md` (understand team context)
2. Read `agents/[me].docs/context.md` (load my memory)
3. Read `agents/[me].docs/current_task.md` (what was I doing?)
```

**WORK:**
```markdown
4. Execute assigned work
5. Post updates to `agents/CHAT.md`
```

**EXIT (before switching to another persona):**
```markdown
6. Update `agents/[me].docs/context.md` (save findings)
7. Update `agents/[me].docs/current_task.md` (mark progress)
8. Update `agents/[me].docs/next_steps.md` (for next time)
```

### 2. Updated Agent Prompt Template

Add this section to ALL persona prompts:

```markdown
## State Management (CRITICAL)

Before you start work:
1. **LOAD STATE**: Read `agents/[yourname].docs/context.md` and `current_task.md`
2. **LOAD TEAM STATE**: Read `agents/CHAT.md` (last 10-20 messages)

While working:
3. **POST UPDATES**: Write to `agents/CHAT.md` after significant steps

Before you finish (MANDATORY):
4. **SAVE STATE**: Update your `.docs/` files:
   - `context.md`: Key decisions, findings, blockers
   - `current_task.md`: What you're working on, % complete
   - `next_steps.md`: What to do when you resume

**State files are your WORKING MEMORY. Without them, you forget everything!**
```

### 3. Enforcement via Bob

**Bob's new responsibility:**
- Monitor that state files are being updated
- Remind personas to save state before switching
- Alert if a persona resumes without loading their context

## Benefits

✅ **Persistent Context**: Each persona remembers their work  
✅ **Smooth Handoffs**: Next persona sees what happened  
✅ **No Duplication**: Agents check their context before re-doing work  
✅ **Better Decisions**: Accumulated knowledge, not fresh starts

## Implementation Plan

1. Create state file templates in each `.docs/` folder
2. Update all *_AGENT.md files with state management protocol
3. Add Bob monitoring/enforcement
4. Test with a full task cycle

## Example: Neo State Files

**neo.docs/current_task.md:**
```markdown
# Current Task: TUI Integration

## Status: In Progress (20%)

## What I'm Doing:
Wiring `ProvisioningService` to `ProvisionScreen` in the Textual TUI.

## Completed:
- [x] Reviewed TUI architecture
- [x] Located ProvisionScreen implementation

## Next:
- [ ] Add ProvisioningService import
- [ ] Wire up provision button handler
```

**neo.docs/context.md:**
```markdown
# Neo's Working Context

## Recent Decisions:
- Using existing TUI (NOT Pygame) per architectural correction
- ProvisionScreen already has worker pattern, just needs service wired

## Key Files:
- `src/ntag424_sdm_provisioner/tui/screens/provision.py`
- `src/ntag424_sdm_provisioner/services/provisioning_service.py`

## Blockers:
None currently

## Notes:
- Tests must pass before committing (Trin's requirement)
```

This creates **persistent agent memory** across the conversation!
