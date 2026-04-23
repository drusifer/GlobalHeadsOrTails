# VS Code Agent Tasks - Implementation Summary

**Date**: 2025-12-06  
**Status**: ✅ Complete and Ready for Use  
**Created**: `.vscode/tasks.json`, `scripts/run-agent.ps1`, `scripts/watch-delegations.ps1`

---

## What Was Built

A complete **VS Code integration for the Bob Protocol**, enabling AI agents (and developers) to work together using:
- **Native VS Code task UI** for easy access (`Ctrl+Shift+B`)
- **File-based state management** for reliable agent coordination
- **Automatic delegation chaining** for multi-agent workflows
- **Persistent context** across agent transitions

### System Components

| Component | File | Purpose |
|-----------|------|---------|
| **VS Code Tasks** | `.vscode/tasks.json` | 6 agent tasks accessible from Task menu |
| **Orchestrator Script** | `scripts/run-agent.ps1` | Manages single agent execution + context + delegation |
| **Watcher Script** | `scripts/watch-delegations.ps1` | Monitors and auto-invokes next agent in chain |
| **Documentation** | `.github/copilot-instructions.md` (Section 7) | Persona tool schemas and patterns |
| **Usage Guide** | `AGENT_TASKS.md` | Detailed guide for humans and AI agents |
| **Quick Reference** | `AGENT_TASKS_QUICK_REF.md` | 1-page cheat sheet |
| **Updated** | `START_HERE.md` | Links to new agent task system |

---

## Features

### ✅ Persona Tasks
Run any persona directly from VS Code:
- **Morpheus** - Architecture Review & Design Decisions
- **Neo** - Implementation & Refactoring
- **Trin** - Quality Assurance & Verification
- **Oracle** - Documentation & Knowledge Synthesis
- **Watcher** - Automatic delegation chaining
- **Status** - View recent activity

### ✅ State Management
Each agent has persistent state:
- `context.md` - Current work state (survives terminal close)
- `task_request.json` - Input specification (can be manually created)
- `next_delegation.json` - Delegation signal (auto-detected by watcher)
- `execution.log` - Audit trail of executions

### ✅ Automatic Delegation Chaining
When running the watcher:
1. Morpheus completes → writes delegation → watcher auto-invokes Neo
2. Neo completes → writes delegation → watcher auto-invokes Trin
3. Trin completes → writes delegation → watcher auto-invokes Oracle
4. Full workflow without manual task switching

### ✅ Transparent Communication
All agent activity logged to `agents/CHAT.md`:
```
[2025-12-06 10:15:23] [MORPHEUS] Architecture review complete
[2025-12-06 10:15:24] [MORPHEUS] → Delegating to Neo for implementation
[2025-12-06 10:15:25] [NEO] Starting implementation
[2025-12-06 10:22:17] [NEO] ✓ Implementation complete (all tests pass)
```

---

## How It Works

### Manual Workflow (No Watcher)

```
Developer runs:
  Ctrl+Shift+B → "Agent: Morpheus - Architecture Review"
  
Morpheus reads:
  1. agents/morpheus.docs/task_request.json (input)
  2. agents/morpheus.docs/context.md (background)

Morpheus works and updates:
  agents/morpheus.docs/context.md (new work state)
  agents/CHAT.md (posts message)

Morpheus outputs:
  agents/morpheus.docs/next_delegation.json
  (signals: delegate to Neo)

Developer manually runs:
  Ctrl+Shift+B → "Agent: Neo - Implement/Refactor"
  
Neo reads:
  1. agents/neo.docs/task_request.json (from Morpheus's delegation)
  2. agents/morpheus.docs/context.md (architecture decision)
  
Neo implements...
```

### Automatic Workflow (With Watcher)

```
Developer starts:
  Ctrl+Shift+B → "Agent: Watch & Auto-Delegate"
  (runs in background terminal)

Developer runs:
  Ctrl+Shift+B → "Agent: Morpheus - Architecture Review"

Morpheus completes and writes:
  agents/morpheus.docs/next_delegation.json

Watcher detects file (every 3 seconds):
  1. Reads next_delegation.json
  2. Parses delegate_to: "neo"
  3. Auto-runs: scripts/run-agent.ps1 -Agent neo -Task implement

Neo runs automatically:
  1. Loads context from morpheus.docs/context.md
  2. Implements changes
  3. Writes next_delegation.json → delegate to trin

Watcher detects Neo's delegation:
  Auto-runs: scripts/run-agent.ps1 -Agent trin -Task quality-gate

Trin runs automatically:
  1. Loads context
  2. Runs tests
  3. Writes next_delegation.json → delegate to oracle

Watcher detects Trin's delegation:
  Auto-runs: scripts/run-agent.ps1 -Agent oracle -Task document-feature

Oracle documents...

Result: Full workflow (Morpheus → Neo → Trin → Oracle) with ZERO manual task switching!
```

---

## Directory Structure

```
.vscode/
└── tasks.json                                    [NEW] Task definitions

scripts/
├── run-agent.ps1                                [NEW] Agent orchestrator
└── watch-delegations.ps1                        [NEW] Auto-delegation watcher

agents/
├── CHAT.md                                      [EXISTING] Shared activity log
├── morpheus.docs/
│   ├── Morpheus_SE_AGENT.md                     [EXISTING] Persona definition
│   ├── context.md                               [STATE] Current work
│   ├── task_request.json                        [STATE] Input specification
│   ├── next_delegation.json                     [STATE] Delegation signal
│   └── execution.log                            [STATE] Audit trail
├── neo.docs/
│   └── ... (same structure)
├── trin.docs/
│   └── ... (same structure)
└── oracle.docs/
    └── ... (same structure)

.github/
└── copilot-instructions.md                      [UPDATED] Added Section 7: Agentic Personas as Tools (254 lines)

Documentation/
├── AGENT_TASKS_QUICK_REF.md                     [NEW] 1-page quick reference
├── AGENT_TASKS.md                               [NEW] Detailed usage guide
└── START_HERE.md                                [UPDATED] Links to new system
```

---

## Usage Quick Start

### First Time Using Agent Tasks

```powershell
# 1. Open VS Code in workspace
cd C:\Users\drusi\VSCode_Projects\GlobalHeadsAndTails
code .

# 2. Press Ctrl+Shift+B to open Task menu
# 3. Select "Agent: Morpheus - Architecture Review"
# 4. Enter architecture question when prompted
# 5. Respond "yes" when asked to delegate
# 6. Either:
#    A) Manually run next agent (Ctrl+Shift+B → Neo)
#    B) Or start watcher first (see below)
```

### Using Automatic Delegation Chain

```powershell
# Terminal 1: Start the watcher (keeps running)
cd C:\Users\drusi\VSCode_Projects\GlobalHeadsAndTails
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/watch-delegations.ps1

# Terminal 2 (main VS Code): Run first agent
# Ctrl+Shift+B → "Agent: Morpheus - Architecture Review"

# Watcher automatically invokes subsequent agents:
# Morpheus → Neo → Trin → Oracle
# No manual task switching needed!
```

### View Activity Log

```powershell
# See what agents have been doing
Get-Content agents/CHAT.md | Select-Object -Last 20

# Or use VS Code task:
# Ctrl+Shift+T → "Agent: Show Status"
```

---

## Persona Reference

### Morpheus - Architecture Review
**When to use**: Design decisions, code review, technical leadership  
**Inputs**: Architecture questions, context files  
**Outputs**: Design document, delegates to Neo  
**Example**: "Should we split ProvisioningService?"

### Neo - Implement/Refactor
**When to use**: Write code, fix bugs, implement features  
**Inputs**: Architecture from Morpheus, files to modify  
**Outputs**: Code changes, test results, delegates to Trin  
**Example**: "Implement the split ProvisioningService refactor"

### Trin - Quality Assurance
**When to use**: Verify tests pass, check coverage, quality gates  
**Inputs**: Implementation from Neo, test requirements  
**Outputs**: Test report, approval/rejection, delegates to Oracle  
**Example**: "Run full test suite, verify coverage >= 90%"

### Oracle - Documentation
**When to use**: Write/update documentation, research, knowledge synthesis  
**Inputs**: All previous work, audience (developers/AI/architects)  
**Outputs**: Updated documentation, knowledge base entries  
**Example**: "Document the new ProvisioningService APIs"

### Watch & Auto-Delegate
**When to use**: Enable automatic agent chaining  
**Configuration**: Runs in background, detects delegations, auto-invokes  
**Output**: Fully automated workflow  
**Example**: Start once, run Morpheus, rest is automatic

---

## Technical Details

### Task Structure (`.vscode/tasks.json`)

```json
{
  "label": "Agent: Morpheus - Architecture Review",
  "type": "shell",
  "command": "powershell",
  "args": [
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", "${workspaceFolder}/scripts/run-agent.ps1",
    "-Agent", "morpheus",
    "-Task", "architecture-review"
  ],
  "presentation": {
    "echo": true,
    "reveal": "always",
    "focus": true,
    "panel": "dedicated"
  }
}
```

### Orchestrator Script (`scripts/run-agent.ps1`)

**Key Functions**:
- `Load-Context()` - Read agent's state from context.md
- `Post-ToChat()` - Append message to CHAT.md with timestamp
- `Update-Context()` - Save agent's work to context.md
- `Write-TaskRequest()` - Create task_request.json
- `Wait-For-Completion()` - Pause and wait for human/agent to complete

**Parameters**:
- `-Agent` (morpheus|neo|trin|oracle) - Which persona to run
- `-Task` (architecture-review|implement|quality-gate|document-feature) - Task type

**Exit States**:
- Delegation: Writes next_delegation.json and optionally invokes next agent
- No delegation: Returns to editor

### Watcher Script (`scripts/watch-delegations.ps1`)

**Key Functions**:
- `Monitor-Directories()` - Watch all persona .docs folders
- `Detect-Delegation()` - Check for next_delegation.json
- `Invoke-NextAgent()` - Auto-run next agent via run-agent.ps1
- `Post-Delegation()` - Log to CHAT.md

**Parameters**:
- `-CheckIntervalSeconds` (default 3) - How often to check for delegations
- `-AutoDelegate` (default true) - Whether to auto-invoke next agent

**Behavior**:
- Checks every N seconds (configurable)
- Detects any persona's delegation file
- Automatically runs next agent
- Cleans up delegation file to prevent re-triggering
- Continues until stopped

---

## Integration with Development Workflow

### Before Committing
```
Ctrl+Shift+B → Morpheus (review code architecture implications)
→ (delegates to Neo if changes needed)
→ (Neo runs tests with Trin)
→ (Trin delegates to Oracle)
→ (Oracle updates docs)
→ All done, commit with confidence!
```

### Sprint Planning
```
Morpheus: Review sprint requirements, design solutions
→ Neo: Implement features
→ Trin: Verify quality and test coverage
→ Oracle: Document for team
```

### Bug Investigation
```
Morpheus: Analyze bug root cause, design fix
→ Neo: Implement the fix
→ Trin: Verify fix doesn't break anything
→ Oracle: Document bug and solution in LESSONS.md
```

---

## File Locations (Quick Reference)

| File | Purpose | Type |
|------|---------|------|
| `.vscode/tasks.json` | VS Code task definitions | Configuration |
| `scripts/run-agent.ps1` | Single agent orchestration | Script |
| `scripts/watch-delegations.ps1` | Auto-delegation watcher | Script |
| `agents/CHAT.md` | Shared activity log | State (append-only) |
| `agents/[persona].docs/context.md` | Agent work state | State (persistent) |
| `agents/[persona].docs/task_request.json` | Task input | State (read by agent) |
| `agents/[persona].docs/next_delegation.json` | Delegation signal | State (detected by watcher) |
| `.github/copilot-instructions.md` | Comprehensive guidance | Documentation |
| `AGENT_TASKS.md` | Detailed usage guide | Documentation |
| `AGENT_TASKS_QUICK_REF.md` | 1-page quick reference | Documentation |

---

## Troubleshooting

### Tasks Don't Appear in Command Palette
- Reload VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
- Verify `.vscode/tasks.json` exists and is syntactically valid

### Watcher Doesn't Auto-Delegate
- Verify watcher task is still running (check Terminal panel)
- Manually check if `next_delegation.json` exists:
  ```powershell
  Test-Path agents/morpheus.docs/next_delegation.json
  ```
- Check file permissions (should be readable/writable)

### Context Not Loading
- Verify `agents/[persona].docs/context.md` exists
- Check file format (should be valid Markdown)
- Script will create empty context if missing

### PowerShell Execution Error
- Check execution policy: `Get-ExecutionPolicy`
- Set to Bypass: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser`
- Or run VS Code as Administrator

---

## Next Steps / Future Enhancements

**Ready Now**:
✅ Run first agent task: `Ctrl+Shift+B` → Morpheus  
✅ Test delegation chain manually  
✅ Enable watcher for automatic chaining  
✅ View activity log: `agents/CHAT.md`

**Could Add**:
🟡 Integration with additional personas (Mouse, Bob, Cypher)  
🟡 VS Code UI showing real-time delegation progress  
🟡 Custom command palette entries for common workflows  
🟡 Integration with git for automatic branch creation  
🟡 Slack/email notifications when delegations complete  

**Out of Scope (For Now)**:
❌ GUI for agent orchestration (keep file-based for simplicity)  
❌ Real-time agent execution tracking (state files are sufficient)  
❌ Multi-workspace support (single workspace per session)

---

## Documentation Map

- **Quick Start** → `AGENT_TASKS_QUICK_REF.md` (1 page)
- **Detailed Guide** → `AGENT_TASKS.md` (comprehensive)
- **Architecture & Patterns** → `.github/copilot-instructions.md` (Section 7)
- **Persona Definitions** → `agents/[persona].docs/[Persona]_[ROLE]_AGENT.md`
- **Bob Protocol** → `agents/bob.docs/BOB_SYSTEM_PROTOCOL.md` (foundational)

---

## Success Criteria (All Met ✅)

✅ Agent tasks accessible from VS Code UI (`Ctrl+Shift+B`)  
✅ Persistent state across agent transitions  
✅ Automatic delegation detection and chaining  
✅ Human-readable activity log (`CHAT.md`)  
✅ Clear documentation for users and AI agents  
✅ PowerShell scripts validated (syntax checked)  
✅ Backward compatible with manual workflow  
✅ Integrated with existing Bob Protocol system  

---

**Status**: ✅ **Complete and Ready for Use**

**To Get Started**: Press `Ctrl+Shift+B` and select "Agent: Morpheus - Architecture Review"

**Questions?** See `AGENT_TASKS.md` or `.github/copilot-instructions.md`
