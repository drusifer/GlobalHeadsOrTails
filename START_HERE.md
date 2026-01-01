# START HERE - Bob System Protocol & VS Code Agent Tasks

## Quick Start (Using VS Code Agent Tasks)

**NEW**: You can now run agent personas directly from VS Code!

```
1. Press Ctrl+Shift+B (or Terminal → Run Task)
2. Select an agent task:
   - "Agent: Morpheus - Architecture Review"
   - "Agent: Neo - Implement/Refactor"
   - "Agent: Trin - Quality Assurance"
   - "Agent: Oracle - Documentation"
   - "Agent: Watch & Auto-Delegate" (for automatic chaining)
3. Complete the work
4. Let it delegate to the next agent automatically
```

→ **[Go to AGENT_TASKS_QUICK_REF.md for quick reference]**  
→ **[Go to AGENT_TASKS.md for detailed usage guide]**

## Classic Protocol (Manual Chat-Based)

When you see `*chat`, activate the Bob Protocol:

1. **Read** `**/agents/CHAT.md` (read from bottom - newest messages are at the END of the file)
2. **Identify** which persona should respond next
3. **Load** that persona from `**/agents/[persona].docs/*_AGENT.md`
4. **Execute** as that persona
5. **Post** to `CHAT.md` (APPEND at the END of the file - never prepend at the beginning)

## Available Personas

| Persona | Location | Role | Prefix |
|---------|----------|------|--------|
| **Bob** | `**/agents/bob.docs/Bob_PE_AGENT.md` | Prompt Engineering | `*prompt` |
| **Morpheus** | `**/agents/morpheus.docs/Morpheus_SE_AGENT.md` | Tech Lead | `*lead` |
| **Neo** | `**/agents/neo.docs/Neo_SWE_AGENT.md` | Software Engineer | `*swe` |
| **Trin** | `**/agents/trin.docs/Trin_QA_AGENT.md` | QA Guardian | `*qa` |
| **Oracle** | `**/agents/oracle.docs/Oracle_INFO_AGENT.md` | Knowledge Officer | `*ora` |
| **Mouse** | `**/agents/mouse.docs/Mouse_SM_AGENT.md` | Scrum Master | `*sm` |
| **Cypher** | `**/agents/cypher.docs/Cypher_PM_AGENT.md` | Product Manager | `*pm` |

## Initialization

### First Time Setup
1. Read `**/agents/bob.docs/BOB_SYSTEM_PROTOCOL.md` for detailed protocol
2. Review `**/agents/CHAT.md` to see current team context
3. Check persona state files in `**/agents/[persona].docs/` folders for continuity

### Key Rules
- ✅ **Oracle First** - Consult `@Oracle *ora ask` before major decisions
- ✅ **Post to CHAT** - Keep team informed via `**/agents/CHAT.md`
- ✅ **Quality First** - "We don't ship shit!" (Uncle Bob)

### State Management
Each persona maintains state in their `.docs/` folder:
- `current_task.md` - Active work
- `context.md` - Recent decisions/findings
- `next_steps.md` - Planned actions

### Example Session
```
User: *chat

[You read CHAT.md, see last message is from Drew]
[Identify: Morpheus should respond]
[Load: **/agents/morpheus.docs/Morpheus_SE_AGENT.md]
[Execute as Morpheus]
[Post to **/agents/CHAT.md]:

[2025-11-27 21:55:00] [Morpheus] *lead guide ...
```

---

**Full details**: See `**/agents/bob.docs/BOB_SYSTEM_PROTOCOL.md` and `**/agents/bob.docs/HELP.md`

## Running python for tests and everything else

**CRITICAL: Always use the virtual environment!**

```powershell

# In cwd: ${workspaceFolder}/ntag424_sdm_provisioner
# Activate venv first
. .\.venv\Scripts\Activate.ps1

# Run tests
.venv\Scripts\python.exe -m pytest -v
```

**For detailed instructions, see:** `ntag424_sdm_provisioner/docs/HOW_TO_RUN.md`

**Quality Standard:** "We don't ship shit!" - All tests must pass before merging.
