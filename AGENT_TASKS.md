# Using Agent Tasks in VS Code

This guide explains how to use the integrated agent personas in VS Code for multi-agent agentic workflows.

## Quick Start

### 1. Open Task Menu

Press **`Ctrl+Shift+B`** (or Terminal → Run Task) to see all available agent tasks:

```
Agent: Morpheus - Architecture Review
Agent: Neo - Implement/Refactor
Agent: Trin - Quality Assurance
Agent: Oracle - Documentation
Agent: Watch & Auto-Delegate
Agent: Show Status
```

### 2. Run First Task

Select **`Agent: Morpheus - Architecture Review`**

The task will:
1. Load background context from `agents/morpheus.docs/context.md`
2. Display the current task/architecture context
3. Wait for you (or an AI agent) to complete the work
4. Ask if there's a next agent to delegate to

### 3. Enter Delegation

When prompted "Delegate to next agent?", you can:

- **Option A (Manual)**: Say "yes" and specify next agent (e.g., "neo")
  - Writes `agents/morpheus.docs/next_delegation.json`
  - Posts update to `agents/CHAT.md`
  - Manually run next agent task

- **Option B (Automatic)**: Have the watcher running in background
  - Watcher detects delegation file
  - Auto-invokes next agent immediately
  - No manual task switching needed

## Detailed Workflow

### Manual Workflow (No Watcher)

```
Step 1: Run Morpheus task
├─ Ctrl+Shift+B → "Agent: Morpheus - Architecture Review"
├─ Enter architecture decision
├─ Create agents/morpheus.docs/next_delegation.json
└─ Manually run next task

Step 2: Run Neo task
├─ Ctrl+Shift+B → "Agent: Neo - Implement/Refactor"
├─ Neo reads Morpheus's context.md
├─ Write code based on architecture decision
├─ Create agents/neo.docs/next_delegation.json
└─ Manually run next task

Step 3: Run Trin task
├─ Ctrl+Shift+B → "Agent: Trin - Quality Assurance"
├─ Trin reads Neo's implementation
├─ Run tests, verify code quality
├─ Create agents/trin.docs/next_delegation.json
└─ Manually run next task

Step 4: Run Oracle task
├─ Ctrl+Shift+B → "Agent: Oracle - Documentation"
├─ Oracle reads all previous work
├─ Generate/update documentation
└─ Done!
```

### Automatic Workflow (With Watcher)

```
Step 0: Start watcher (once, at project startup)
└─ Ctrl+Shift+B → "Agent: Watch & Auto-Delegate"
   └─ Runs in background, monitoring all agents for delegations

Step 1: Run Morpheus task
├─ Ctrl+Shift+B → "Agent: Morpheus - Architecture Review"
├─ Enter architecture decision
├─ Create agents/morpheus.docs/next_delegation.json
└─ Return to editor (don't need to do anything)

Step 2: Watcher auto-invokes Neo
├─ Detects next_delegation.json in morpheus.docs
├─ Auto-runs Neo task with delegation context
├─ Neo implements changes
└─ Creates neo.docs/next_delegation.json

Step 3: Watcher auto-invokes Trin
├─ Detects next_delegation.json in neo.docs
├─ Auto-runs Trin task with delegation context
├─ Trin runs tests and QA
└─ Creates trin.docs/next_delegation.json

Step 4: Watcher auto-invokes Oracle
├─ Detects next_delegation.json in trin.docs
├─ Auto-runs Oracle task with delegation context
├─ Oracle documents the work
└─ Done! Full chain completed automatically

Step 5: Stop watcher
└─ Kill the watcher terminal when chain completes
```

## File-Based Communication

Agents communicate through **state files in the filesystem**:

### Morpheus's State Files
```
agents/morpheus.docs/
├── context.md                          # Current state of architecture work
├── task_request.json                   # Input (what to review?)
├── next_delegation.json                # Output (delegate to whom?)
├── execution.log                       # Execution history
└── ...other work files...
```

### Typical Flow

1. **Task Request** (input):
```json
{
  "task": "architecture-review",
  "subject": "ProvisioningService refactor",
  "context_files": ["src/services/provisioning_service.py"],
  "constraints": ["preserve EV2 session semantics"]
}
```

2. **Context Update** (Morpheus works):
```markdown
# Architecture Review - ProvisioningService

## Analysis
Current implementation has X and Y issues.

## Decision
Split into provision_keys() and provision_url()

## Rationale
...detailed explanation...

## Next Delegation
→ Neo: Implement the split
```

3. **Delegation** (output):
```json
{
  "delegate_to": "neo",
  "task": "implement",
  "subject": "Split ProvisioningService",
  "context": "See agents/morpheus.docs/context.md for architecture decision"
}
```

4. **Chat Log** (transparency):
```
[2025-12-06 10:15:23] [MORPHEUS] ✓ Architecture review complete
[2025-12-06 10:15:24] [MORPHEUS] → Delegating to Neo for implementation
[2025-12-06 10:15:25] [NEO] Starting implementation (context loaded)
[2025-12-06 10:22:17] [NEO] ✓ Implementation complete (all tests pass)
[2025-12-06 10:22:18] [NEO] → Delegating to Trin for QA
```

## Task Reference

### Agent: Morpheus - Architecture Review
**Persona**: Tech Lead / Architect  
**Purpose**: Design decisions, code review, technical mentoring  
**Inputs**: 
- Architecture questions or code to review
- Context files (ARCH.md, source code)
- Constraints and blockers

**Outputs**:
- Architecture decision
- Rationale and alternatives considered
- Next delegation (usually to Neo for implementation)

**Example Use Cases**:
- "Should we split ProvisioningService?"
- "Review this refactor for SOLID principles"
- "Design the authentication flow"

### Agent: Neo - Implement/Refactor
**Persona**: Software Engineer  
**Purpose**: Write code, fix bugs, implement features  
**Inputs**:
- Implementation objectives (from Morpheus)
- Architecture decisions
- Files to modify

**Outputs**:
- Code changes (committed or shown)
- Test results (pass/fail)
- Next delegation (usually to Trin for QA)

**Example Use Cases**:
- "Split ProvisioningService into two methods"
- "Fix the 917E error in ChangeFileSettings"
- "Add type hints to crypto_primitives.py"

### Agent: Trin - Quality Assurance
**Persona**: QA Engineer  
**Purpose**: Test verification, quality gates, coverage checks  
**Inputs**:
- Implementation from Neo
- Files to test
- Acceptance criteria

**Outputs**:
- Test results (passed/failed)
- Coverage report
- Quality gate approval/rejection
- Next delegation (usually to Oracle for documentation)

**Example Use Cases**:
- "Verify that all tests pass"
- "Check code coverage >= 90%"
- "Run linting (ruff check src/)"

### Agent: Oracle - Documentation
**Persona**: Knowledge Officer / Technical Writer  
**Purpose**: Documentation, research, knowledge synthesis  
**Inputs**:
- Implementation from Neo
- Test results from Trin
- Audience (AI agents, developers, architects)

**Outputs**:
- Generated documentation
- Updated ARCH.md, README.md
- Knowledge base entries
- Cross-references

**Example Use Cases**:
- "Document the new ProvisioningService APIs"
- "Update ARCH.md to reflect new design"
- "Create SYMBOL_INDEX.md for new module"

### Agent: Watch & Auto-Delegate
**Persona**: Automation System  
**Purpose**: Monitor delegations and auto-invoke next agent  
**Configuration**:
- Check interval: 3 seconds (configurable)
- Auto-invoke: Enabled (can disable with `-AutoDelegate $false`)
- Monitoring: All persona directories

**How It Works**:
1. Runs continuously in background
2. Monitors `agents/[persona].docs/next_delegation.json`
3. When delegation appears, auto-invokes next agent
4. Posts updates to CHAT.md
5. Cleans up delegation files

**Usage**:
```
# Start watcher at project startup
Ctrl+Shift+B → "Agent: Watch & Auto-Delegate"

# Then run tasks normally - watcher handles delegations automatically
```

### Agent: Show Status
**Persona**: Reporting System  
**Purpose**: Display recent activity and chat log  
**Output**: Last 20 lines of agents/CHAT.md  

**Usage**: Quick way to see what agents have been doing

## Common Workflows

### Architecture Review → Implementation → Testing → Documentation

```
1. Ctrl+Shift+B → Morpheus (review architecture)
   ↓ (writes next_delegation.json)
2. Auto-invoke Neo (if watcher running) OR manually run Neo
   ↓ (writes next_delegation.json)
3. Auto-invoke Trin OR manually run Trin
   ↓ (writes next_delegation.json)
4. Auto-invoke Oracle OR manually run Oracle
   ↓
5. Done! Full workflow complete
```

### Bug Investigation → Fix → Verification

```
1. Ctrl+Shift+B → Morpheus (analyze bug, design fix)
   → "Implement fix in crypto_primitives.py"
2. Ctrl+Shift+B → Neo (implement the fix)
   → "Verify fix doesn't break tests"
3. Ctrl+Shift+B → Trin (run full test suite)
   → If passing, "Update LESSONS.md with findings"
4. Ctrl+Shift+B → Oracle (document the bug and fix)
```

## Troubleshooting

### Task doesn't appear in Command Palette
- Make sure `.vscode/tasks.json` exists
- VS Code might need to reload (Ctrl+Shift+P → Developer: Reload Window)

### Watcher doesn't detect delegation
- Check that `next_delegation.json` was actually written to the right directory
- Verify watcher task is still running (check Terminal panel)
- Manually copy next_delegation.json to trigger test (for debugging)

### Context file isn't loading
- Check `agents/[persona].docs/context.md` exists
- If missing, script will create empty one
- Make sure file has readable YAML/Markdown format

### Next agent doesn't auto-invoke
- Verify `scripts/run-agent.ps1` exists in workspace
- Check PowerShell execution policy: `Get-ExecutionPolicy` should allow script execution
- Manual option: Run next agent task explicitly

## Advanced Usage

### Custom Task Inputs

You can manually create `task_request.json` before running a task:

```json
{
  "task": "implement",
  "objective": "Fix the 917E error",
  "requirements": [
    "Use ChangeFileSettingsAuth (authenticated command)",
    "Verify with acceptance tests",
    "Update DECISIONS.md"
  ],
  "files_to_modify": [
    "src/commands/change_file_settings.py",
    "acceptance_tests/test_*.py"
  ]
}
```

Then run the Neo task - it will use your custom request.

### Inspection & Debugging

**View agent's current context**:
```powershell
Get-Content agents/morpheus.docs/context.md
```

**View delegation chain history**:
```powershell
Get-Content agents/CHAT.md | Select-Object -Last 30
```

**Manually trigger next delegation**:
```powershell
# Simulate what watcher does
$delegation = Get-Content agents/morpheus.docs/next_delegation.json | ConvertFrom-Json
& scripts/run-agent.ps1 -Agent $delegation.delegate_to -Task $delegation.task
```

## Integration with Development

### Before Committing Code
1. Run Morpheus to review architecture implications
2. Run Neo to ensure code follows patterns
3. Run Trin to verify all tests pass
4. Run Oracle to update docs

### Weekly Codebase Review
1. Run Morpheus on ARCH.md (check if design still valid)
2. Run Neo on outstanding bugs or tech debt
3. Run Trin on full test suite
4. Run Oracle to update knowledge base

### Sprint Planning Integration
- Morpheus reviews features, designs solutions
- Neo implements features
- Trin verifies quality
- Oracle documents for team

## References

- **`.github/copilot-instructions.md`** - Complete persona definitions and tool schemas
- **`agents/CHAT.md`** - Central log of all agent activities
- **`agents/[persona].docs/context.md`** - Individual persona state files
- **`scripts/run-agent.ps1`** - Orchestrator script (runs individual tasks)
- **`scripts/watch-delegations.ps1`** - Watcher script (auto-chains tasks)

---

**Status**: ✅ Integrated and ready to use  
**First Time**: Press `Ctrl+Shift+B` and select "Agent: Morpheus - Architecture Review"  
**Questions**: See `.github/copilot-instructions.md` Section: "Agentic Personas as Tools"
