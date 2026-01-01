# Agent Command Glossary

**Purpose**: Maintain consistency across all agents. Common commands should behave identically. Agent-specific commands use unique prefixes to avoid conflicts.

**Last Updated**: 2025-11-21 by Ora

---

## Common Commands (All Agents)

### `*hist`
**Owner**: Oracle (Ora)  
**Purpose**: Show recent messages from all agent CHAT.md files  
**Behavior**: Scans all `*.docs/CHAT.md`, extracts 2-3 most recent messages, displays with relative timestamps (e.g., "4 min ago")  
**Used By**: All agents (read-only; Ora maintains)

### `*chat`
**Owner**: All agents  
**Purpose**: Check and respond to messages in team CHAT.md files  
**Behavior**: Scan all agent CHAT.md files for mentions/commands, respond in own CHAT.md  
**Pattern**: Messages appear chronologically, newest at top

### `*tell <agent_name> <INSTRUCTION>`
**Owner**: User (Drew)  
**Purpose**: Direct instruction from user to specific agent  
**Behavior**: User posts to specific agent's CHAT.md, agent checks and responds  
**Example**: `*tell neo fix the CMAC bug`

### `@<AgentName> <message>`
**Owner**: Any agent  
**Purpose**: Direct mention/message from one agent to another  
**Behavior**: Agents scan other CHAT.md files for @mentions directed at them  
**Example**: `@Neo can you implement this feature?`

---

## Oracle Protocol Commands (All Agents Can Use)

### `*or ask <QUESTION>`
**Owner**: Oracle (Ora)  
**Purpose**: Query the knowledge base for information  
**When**: Stuck in debugging loop (3+ failures), need architectural guidance, confirm specs  
**Response**: Oracle searches docs and provides answer with citations

### `*or record <TYPE> <CONTENT>`
**Owner**: Oracle (Ora)  
**Purpose**: Log decisions, lessons, risks, assumptions  
**Types**:
- `decision` → `DECISIONS.md`
- `lesson` → `LESSONS.md`
- `risk` → `OBJECTIVES.md`
- `assumption` → `ARCH.md` or `DECISIONS.md`

### `*or groom`
**Owner**: Oracle (Ora)  
**Purpose**: Audit and organize file structure  
**Actions**: Move files to proper directories, update README.md

### `*or distill <FILE_PATH>`
**Owner**: Oracle (Ora)  
**Purpose**: Break down large specs into atomic documents  
**Result**: Creates docs in `docs/specs/` with TL;DR and TOC

---

## Bob Commands (Prompt Engineering)

### `*prompt <DESC>`
**Owner**: User → Bob  
**Purpose**: Create a new agent prompt  
**Pattern**: Review → Summarize → Generate

### `*reprompt <INSTRUCTIONS>`
**Owner**: User → Bob  
**Purpose**: Update existing agent prompts  
**Scope**: Can affect multiple agents

### `*learn <LESSON>`
**Owner**: User → Bob  
**Purpose**: Shorthand for `*reprompt All agents must learn: <LESSON>`  
**Scope**: Global update to all agents

### `@Bob *prompt` / `@Bob *reprompt`
**Owner**: Any agent → Bob  
**Purpose**: Request capability updates from Bob

---

## SE (The Lead) Commands

**Prefix**: `*lead`

### `*lead story <USER_STORY>`
**Purpose**: Add/update user story in backlog  
**File**: `se.docs/BACKLOG.md`

### `*lead plan <EPIC>`
**Purpose**: Break down feature into tasks and assign  
**Delegates To**: `@SWE`, `@QA`

### `*lead guide <ISSUE>`
**Purpose**: Provide architectural guidance  
**Authority**: Tech Lead has veto power on design decisions

### `*lead refactor <TARGET>`
**Purpose**: Identify code smells, propose refactoring strategy  
**Patterns**: Extract Method, Replace Conditional with Polymorphism, etc.

### `*lead decide <CHOICE>`
**Purpose**: Make binding architectural decision  
**Must**: Record via `@Oracle *or record decision`

---

## SWE (Neo, The Engineer) Commands

**Prefix**: `*swe`

### `*swe impl <TASK>`
**Purpose**: Design, implement, and verify a feature  
**Pattern**: Plan → Code → Test → Verify

### `*swe fix <ISSUE>`
**Purpose**: Diagnose and resolve a bug  
**Pattern**: Reproduce → Analyze → Fix → Test

### `*swe test <SCOPE>`
**Purpose**: Write and run pytest or hardware tests  
**Pattern**: Write test → Run → Fix failures → Verify

### `*swe refactor <TARGET>`
**Purpose**: Improve code structure without changing behavior  
**Pattern**: Identify smells → Plan → Execute → Test

---

## QA (The Guardian) Commands

**Prefix**: `*qa`

### `*qa test <SCOPE>`
**Purpose**: Run test suite (e.g., `all`, `crypto`)  
**Authority**: Gatekeeper - if tests fail, feature is not done

### `*qa verify <FEATURE>`
**Purpose**: Create test plan for a feature  
**Must**: Consult Oracle for acceptance criteria via `*or ask`

### `*qa report`
**Purpose**: Summarize current health of codebase

### `*qa repro <ISSUE>`
**Purpose**: Create minimal test case to reproduce bug

---

## Agent Workspace Standards

All agents follow the **Global Agent Standards**:

1. **Working Memory**: Each agent maintains `[agent_name].docs/` directory
   - `CHAT.md` - Team communication (newest on top)
   - `COMMANDS.md` - Command reference (optional but recommended)
   - Agent-specific files (e.g., `current_task.md`, `BACKLOG.md`)

2. **Oracle Protocol**: Consult Oracle when stuck (3+ failures) or for architectural decisions

3. **Command Syntax**: `*[prefix] [verb] [args]` format

4. **Continuous Learning**: New `*learn` instructions supersede old ones

5. **Async Communication**: Check other agents' CHAT.md files regularly

---

## Current Agent Roster

| Agent | Prefix | Role | Workspace |
|-------|--------|------|-----------|
| **Ora** (Oracle) | `*or` | Chief Knowledge Officer | `oracle.docs/` |
| **Bob** | `*prompt`, `*learn` | Prompt Engineering Expert | `bob.docs/` |
| **SE** (The Lead) | `*lead` | Tech Lead / Architect | `se.docs/` |
| **Neo** (SWE) | `*swe` | Software Engineer | `swe.docs/` |
| **QA** (Guardian) | `*qa` | Lead SDET | `qa.docs/` |

---

## Consistency Notes

### ✅ Consistent (Good)
- All agents use `*chat` for reading team messages
- All agents use `*hist` (Oracle-maintained) for recent activity
- All agents can use `*or ask` / `*or record` (Oracle protocol)
- All agents follow `@AgentName` mention pattern

### ⚠️ To Monitor
- Ensure new commands don't conflict with existing prefixes
- Bob should be consulted when adding cross-agent commands
- Oracle should document any new global commands in this glossary

---

**Maintained by**: The Oracle (Ora)  
**Review Frequency**: After any `*learn` or agent prompt updates
