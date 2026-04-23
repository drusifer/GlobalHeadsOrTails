# Agent Tasks - Quick Reference

## TL;DR - Get Started in 30 Seconds

```
1. Press Ctrl+Shift+B
2. Select "Agent: Morpheus - Architecture Review"
3. Enter your architecture question/review task
4. Type "yes" when asked to delegate
5. Press Enter and task auto-delegates to next agent
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Show all tasks | `Ctrl+Shift+B` or Terminal → Run Task |
| Quick run last task | `Ctrl+Shift+B` → Last selected |
| Show status | `Ctrl+Shift+T` → "Agent: Show Status" |

## Task Menu

```
Agent: Morpheus - Architecture Review    [Tech Lead - Design decisions]
Agent: Neo - Implement/Refactor          [Engineer - Write code]
Agent: Trin - Quality Assurance          [QA - Verify & test]
Agent: Oracle - Documentation            [Writer - Document work]
Agent: Watch & Auto-Delegate             [Automation - Auto-chain tasks]
Agent: Show Status                       [Reporting - Show CHAT.md]
```

## Workflow Types

### Full Architecture → Code → Test → Docs Chain
```
Morpheus review → Neo implement → Trin test → Oracle document
(Auto with watcher, or manual task switching)
```

### Bug Fix Workflow
```
Morpheus analyze bug → Neo implement fix → Trin verify → Oracle document
```

### Code Review Workflow
```
Morpheus review code → Neo refactor → Trin test → Oracle update docs
```

## State Files (The "Message Bus")

```
agents/CHAT.md                              ← Read-only activity log
agents/morpheus.docs/context.md             ← Morpheus's work state
agents/neo.docs/context.md                  ← Neo's work state
agents/trin.docs/context.md                 ← Trin's work state
agents/oracle.docs/context.md               ← Oracle's work state
agents/*/next_delegation.json               ← Delegation signal (auto-detected by watcher)
```

## Manual Delegation (No Watcher)

1. Run Morpheus task (`Ctrl+Shift+B`)
2. Morpheus displays: "Delegate to next agent? (yes/no)"
3. Type `yes` and press Enter
4. Manually run Neo task (`Ctrl+Shift+B` → Neo)
5. Repeat for Trin, then Oracle

## Auto Delegation (With Watcher)

1. Start watcher once: `Ctrl+Shift+B` → "Agent: Watch & Auto-Delegate"
2. Run Morpheus task (`Ctrl+Shift+B`)
3. Morpheus completes and writes `next_delegation.json`
4. **Watcher automatically invokes Neo**
5. **Watcher automatically invokes Trin when Neo delegates**
6. **Watcher automatically invokes Oracle when Trin delegates**
7. Done! Full chain runs automatically

## Common Tasks

| Scenario | Who to Run |
|----------|-----------|
| Design new feature | **Morpheus** (design) → **Neo** (code) → **Trin** (test) → **Oracle** (docs) |
| Fix a bug | **Morpheus** (analyze) → **Neo** (fix) → **Trin** (verify) |
| Review code | **Morpheus** (review) → **Neo** (refactor) → **Trin** (test) |
| Update docs | **Oracle** |
| Run tests | **Trin** |

## Persona Roles at a Glance

| Persona | Role | Asks | Delivers |
|---------|------|------|----------|
| **Morpheus** | Tech Lead | Architecture decisions, design reviews, constraints | Design document, next delegate (Neo) |
| **Neo** | Engineer | Implementation specs, files to change, test requirements | Code changes, test results, next delegate (Trin) |
| **Trin** | QA | Test files, acceptance criteria, quality gates | Test report, coverage, approval, next delegate (Oracle) |
| **Oracle** | Writer | Implementation details, requirements, audience | Documentation, updated ARCH.md, knowledge base |

## What Gets Saved (Persistence)

After each task:
- ✅ Work saved to `agents/[persona].docs/context.md` 
- ✅ Updates logged to `agents/CHAT.md` (append-only)
- ✅ State survives task termination (context is persistent)
- ✅ Delegation visible in `next_delegation.json`

## Debugging

**Check what agents have done**:
```powershell
# View last 20 updates
Get-Content agents/CHAT.md | Select-Object -Last 20

# View Morpheus's current work
Get-Content agents/morpheus.docs/context.md

# View Neo's implementation plan
Get-Content agents/neo.docs/context.md
```

**Check if delegation is ready**:
```powershell
# Does next_delegation.json exist?
Test-Path agents/morpheus.docs/next_delegation.json

# View the delegation
Get-Content agents/morpheus.docs/next_delegation.json | ConvertFrom-Json
```

## Full Documentation

→ See **AGENT_TASKS.md** for detailed usage  
→ See **.github/copilot-instructions.md** Section 7 for persona schemas  
→ See **AGENTS.md** for Bob Protocol background

---

**Status**: ✅ Ready to use  
**Start here**: `Ctrl+Shift+B` → "Agent: Morpheus - Architecture Review"
