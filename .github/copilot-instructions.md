# Copilot Instructions for NTAG424 SDM Provisioner

## Project Overview

**NTAG424 SDM Provisioner** is a production-ready Python service for provisioning NXP NTAG424 DNA NFC tags with Secure Dynamic Messaging (SDM) capabilities. It provides a service-oriented architecture with TUI/CLI interfaces and hardware-validated cryptographic operations.

**Key Facts:**
- Hardware-validated against real NTAG424 tags using ACR122U reader
- Service-layer architecture (ProvisioningService, TagDiagnosticsService, TagMaintenanceService)
- Type-safe command pattern with EV2 two-phase authentication
- TUI primary interface (Textual framework) with async WorkerManager
- Windows PowerShell environment with Python `.venv`

---

## Architecture Essentials

### Service Layer (Business Logic)
All business logic resides in UI-agnostic services in `src/ntag424_sdm_provisioner/services/`:
- **ProvisioningService** - Tag provisioning workflow (key changes, SDM config, NDEF writing)
- **TagDiagnosticsService** - Status queries (chip version, key versions, file settings, NDEF reading)
- **TagMaintenanceService** - Factory reset and tag formatting

Services use dependency injection (CardConnection, CsvKeyManager) and callbacks for progress. Services are **not UI-aware**—they report status via callbacks, making them reusable across TUI, CLI, and future APIs.

### Command Layer (APDU Operations)
Commands in `src/ntag424_sdm_provisioner/commands/` implement the command pattern:
- **ApduCommand** - Base for unauthenticated operations (SelectPiccApplication, GetChipVersion, ReadData)
- **AuthApduCommand** - Base for authenticated operations requiring CMAC (ChangeKey, ChangeFileSettingsAuth, WriteNdefMessageAuth)
- **AuthenticatedConnection** - Context manager that establishes EV2 session with CMAC validation

**Critical Pattern:**
```python
# Unauthenticated command
card.send(SelectPiccApplication())

# Authenticated session (two-phase protocol)
with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
    auth_conn.send(ChangeKey(0, new_key, None))  # Must use AuthApduCommand subclass
```

### HAL Layer
`src/ntag424_sdm_provisioner/hal.py` provides CardConnection interface abstracting hardware:
- `NTag424CardConnection` - Real hardware via pyscard
- Auto-chunking for large reads/writes
- Card initialization and state management

### Crypto Layer
`src/ntag424_sdm_provisioner/crypto/` implements NXP-verified primitives:
- CMAC (Cipher-based Message Authentication Code)
- AES encryption/decryption with SDM
- Session key derivation
- **All verified against NXP AN12196 specification**

---

## Project-Specific Conventions

### Virtual Environment (CRITICAL)
All Python execution MUST use the `.venv` environment:
```powershell
# Activate first (centralizes __pycache__)
. .\scripts\activate.ps1

# Or direct path execution
& .\.venv\Scripts\python.exe -m pytest tests/ -v
```
Failure to use `.venv` will cause import/dependency errors.

### Key Management & CSV Format
`src/ntag424_sdm_provisioner/csv_key_manager.py` manages tag keys:
- Stores keys in `tag_keys.csv` (workspace root and backups)
- Tracks key status: `pending` → `provisioned` (two-phase commit prevents data loss)
- Auto-backups created on state changes
- **Never edit CSV directly**—use CsvKeyManager API

### Authentication Workflow (EV2 Protocol)
Per SUCCESSFUL_PROVISION_FLOW.md, authentication is **stateful and session-based**:
1. SendCommand: first auth request (reads random number from tag)
2. ReceiveCommand: second auth phase (proves key knowledge via CMAC)
3. Session established—subsequent commands auto-include CMAC
4. Session invalidates after certain commands (e.g., ChangeKey with key_no=0)

**Gotcha:** After changing Key 0, you must establish a new session with the NEW key. Old session is invalid.

### SDM (Secure Dynamic Messaging)
SDM placeholders in NDEF URLs are replaced by the tag at runtime:
- `{UID}` → unique identifier (7 bytes for NTAG424)
- `{CMAC}` → message authentication code (4 bytes)
- `{CTR}` → monotonic counter (4 bytes)

Placeholder offsets are calculated via `calculate_sdm_offsets()` in `sdm_helpers.py`. ChangeFileSettings MUST use ChangeFileSettingsAuth (authenticated) or SDM placeholders won't be recognized by the tag (causes 917E LENGTH_ERROR).

### Type Safety
Commands are split into authenticated vs unauthenticated **to compile-time validate** that sensitive operations cannot accidentally be sent unencrypted:
- Never instantiate `ChangeFileSettings` directly—use `ChangeFileSettingsAuth`
- Never call `WriteNdefMessage` unencrypted—use `WriteNdefMessageAuth`
- See DECISIONS.md Decision #4 for the 917E bug and fix

---

## Testing & Quality

### Test Markers
```bash
pytest -m unit         # Unit tests (no hardware)
pytest -m integration  # Integration tests (simulator or hardware)
pytest -m hardware     # Real hardware required
pytest -m simulator    # Seritag EV2 simulator
```

### Linting
```powershell
# Quick feedback (TDD)
.\scripts\lint-quick.ps1

# Full QA gate (sprint acceptance)
.\scripts\lint-full.ps1 -SkipSlowTests
```

### Key Test Files
- `acceptance_tests/test_seritag_ev2_compliance.py` - EV2 protocol validation
- `acceptance_tests/test_production_auth.py` - Multi-session authentication
- Tests verify cryptographic output against NXP specifications

---

## Developer Workflow

### New Command Implementation
1. Create class extending `ApduCommand` or `AuthApduCommand` in `commands/`
2. Implement `body()` (returns APDU bytes) and optionally `parse_response()`
3. Add tests in `tests/`
4. Use command in service via `card.send(YourCommand())`

### New Service Implementation
1. Create service class in `services/`
2. Inject CardConnection and CsvKeyManager in constructor
3. Use callbacks for progress: `self.progress_callback("message")`
4. Wire service into TUI screen via WorkerManager

### Debugging
- Sequence logging enabled via `SEQUENCE_LOGGER_ENABLED=1` env var
- Logs APDU exchanges and responses (see `sequence_logger.py`)
- TUI debug mode: check `tui/tui_main.py` for logging configuration
- Real hardware simulation via Seritag simulator for testing without tags

---

## Agentic Personas as Tools (Multi-Agent Orchestration)

This project uses **Bob Protocol personas** that can be invoked as specialized tools by AI agents. Each persona has a specific role, input schema, output schema, and access patterns.

### The 4 Core Personas

**1. Morpheus (Tech Lead) - Architecture & Design**
```json
{
  "name": "morpheus-architect",
  "input": {
    "task": "architecture-review|design-decision|code-review|mentoring",
    "subject": "What to review (e.g., 'ProvisioningService refactor')",
    "context_files": ["ARCH.md", "src/services/..."],
    "constraints": ["must maintain service-layer separation", "cannot break EV2 auth"],
    "blockers": ["What's stopping progress"]
  },
  "output": {
    "decision": "string",
    "rationale": "Why this decision",
    "alternatives_considered": ["alt1", "alt2"],
    "risks": ["Potential issues"],
    "next_delegations": [{"delegate_to": "neo-engineer|oracle-knowledge|trin-qa", "task": "..."}]
  },
  "can_access": [
    "ARCH.md", "DECISIONS.md", "src/services/", "agents/morpheus.docs/",
    "commands: grep_search, read_file, list_code_usages"
  ]
}
```

**Use Morpheus when:**
- Making architectural decisions
- Reviewing design impact
- Validating SOLID principles
- Mentoring on patterns

**2. Neo (Software Engineer) - Implementation**
```json
{
  "name": "neo-engineer",
  "input": {
    "task": "implement|refactor|bugfix|test-fix",
    "objective": "What to implement (e.g., 'refactor ProvisioningService split')",
    "requirements": ["Requirement 1", "Requirement 2"],
    "files_to_modify": ["src/services/provisioning_service.py"],
    "test_requirements": ["pytest tests/ -v", "ruff check src/"]
  },
  "output": {
    "implementation_summary": "What was implemented",
    "files_changed": [{"path": "...", "changes": "What changed and why"}],
    "tests_passing": true,
    "blockers": ["Any blockers"],
    "next_delegations": [{"delegate_to": "trin-qa|morpheus-architect", "task": "..."}]
  },
  "can_access": [
    "src/ntag424_sdm_provisioner/", "tests/",
    "commands: read_file, replace_string_in_file, multi_replace_string_in_file, runTests, run_in_terminal"
  ]
}
```

**Use Neo when:**
- Implementing features
- Fixing bugs
- Refactoring code
- Writing tests

**3. Trin (QA) - Testing & Verification**
```json
{
  "name": "trin-qa",
  "input": {
    "task": "test-implementation|verify-fix|quality-gate|security-review",
    "implementation": "Summary of what was implemented",
    "files_to_test": ["src/services/provisioning_service.py"],
    "acceptance_criteria": ["All tests pass", "ruff check clean", "coverage >= 90%"]
  },
  "output": {
    "test_results": {
      "tests_passed": 28,
      "tests_failed": 0,
      "coverage_percent": 92,
      "status": "approved|blocked"
    },
    "quality_checks": ["Check1", "Check2"],
    "issues_found": ["Issue1"],
    "approval": true
  },
  "can_access": [
    "src/", "tests/", "agents/trin.docs/",
    "commands: runTests, run_in_terminal, read_file, grep_search"
  ]
}
```

**Use Trin when:**
- Verifying implementations
- Running test suites
- Quality gates (pre-merge checks)
- Security validation

**4. Oracle (Knowledge Officer) - Documentation & Research**
```json
{
  "name": "oracle-knowledge",
  "input": {
    "task": "document-feature|research-issue|update-arch|knowledge-synthesis",
    "subject": "What to document/research",
    "context_items": ["Related files and code to synthesize"],
    "audience": "ai-agents|developers|architects"
  },
  "output": {
    "documentation": "Generated docs",
    "files_updated": ["README.md", "docs/SYMBOL_INDEX.md", "ARCH.md"],
    "knowledge_synthesis": "Synthesized knowledge",
    "cross_references": ["Links to related docs"]
  },
  "can_access": [
    "**/*.md", "src/", "agents/oracle.docs/",
    "commands: read_file, create_file, replace_string_in_file, grep_search, semantic_search"
  ]
}
```

**Use Oracle when:**
- Documenting features
- Researching issues
- Updating architecture docs
- Creating knowledge base entries

### Persona Delegation Pattern

Personas invoke each other using structured delegation:

```
Step 1: Morpheus reviews architecture
├─ Input: {"task": "architecture-review", "subject": "ProvisioningService split", ...}
├─ Output: {"decision": "Approved", "next_delegations": [{"delegate_to": "neo-engineer", ...}]}
└─ Posts to: agents/CHAT.md + agents/morpheus.docs/context.md

Step 2: Neo implements the decision
├─ Input: {"task": "implement", "objective": "Split ProvisioningService...", ...}
├─ Output: {"implementation_summary": "Done", "tests_passing": true, "next_delegations": [{"delegate_to": "trin-qa"}]}
└─ Posts to: agents/CHAT.md + agents/neo.docs/context.md

Step 3: Trin verifies the implementation
├─ Input: {"task": "test-implementation", "files_to_test": [...], ...}
├─ Output: {"approval": true, "test_results": {...}, "next_delegations": [{"delegate_to": "oracle-knowledge"}]}
└─ Posts to: agents/CHAT.md + agents/trin.docs/context.md

Step 4: Oracle documents the new API
├─ Input: {"task": "document-feature", "subject": "New provision_keys() and provision_url() APIs", ...}
├─ Output: {"documentation": "...", "files_updated": ["README.md", "ARCH.md"]}
└─ Posts to: agents/CHAT.md + agents/oracle.docs/context.md
```

### State Management Across Delegations

Each persona maintains state in their `.docs/` folder:

```
agents/
├── CHAT.md                         # Delegation log (short summaries only)
├── morpheus.docs/
│   ├── context.md                  # Current architecture decisions
│   ├── design_log.md               # Design decisions in progress
│   └── review_checklist.md         # Code review standards
├── neo.docs/
│   ├── context.md                  # Implementation status
│   ├── blockers.md                 # Current blockers
│   └── code_changes.md             # Summary of changes made
├── trin.docs/
│   ├── context.md                  # Test/QA status
│   ├── test_results.md             # Detailed test reports
│   └── quality_gates.md            # QA standards
└── oracle.docs/
    ├── context.md                  # Knowledge base state
    ├── research_log.md             # Research findings
    └── doc_index.md                # Documentation inventory
```

**Key Rule**: When delegating to next persona, include link to previous persona's context file.

Example delegation:
```json
{
  "delegate_to": "neo-engineer",
  "task": "implement",
  "context": "See agents/morpheus.docs/context.md for architecture decision",
  "files_to_modify": ["src/services/provisioning_service.py"]
}
```

### Invocation Examples (for AI Agents)

**Example 1: Architecture Review → Implementation → QA → Documentation**
```
morpheus.invoke({
  task: "architecture-review",
  subject: "Should ProvisioningService support separate key provisioning?",
  context_files: ["src/services/provisioning_service.py", "ARCH.md"],
  constraints: ["must preserve EV2 session semantics"]
})
// Output indicates: "Yes, split into provision_keys() and provision_url()"
// Delegates to: neo-engineer

neo.invoke({
  task: "implement",
  objective: "Split ProvisioningService",
  requirements: morpheus.output.requirements,
  files_to_modify: ["src/services/provisioning_service.py"]
})
// Output: Implementation complete, tests passing
// Delegates to: trin-qa

trin.invoke({
  task: "test-implementation",
  implementation: neo.output.implementation_summary,
  files_to_test: neo.output.files_changed.map(f => f.path)
})
// Output: All tests pass, approved
// Delegates to: oracle-knowledge

oracle.invoke({
  task: "document-feature",
  subject: "New ProvisioningService two-phase API",
  context_items: [neo.output, morpheus.output],
  audience: "ai-agents"
})
// Output: Documentation complete
```

**Example 2: Direct Invocation (when you know what's needed)**
```
// Skip architecture review if decision already made
neo.invoke({
  task: "bugfix",
  objective: "Fix 917E LENGTH_ERROR in ChangeFileSettings",
  requirements: ["Use ChangeFileSettingsAuth (authenticated only)"],
  files_to_modify: ["src/commands/change_file_settings.py"]
})

trin.invoke({
  task: "quality-gate",
  implementation: neo.output.implementation_summary,
  acceptance_criteria: ["pytest tests/ -v", "ruff check src/", "coverage >= 90%"]
})
```

### Decision Tree for Persona Selection

```
User Request → Which Persona?

"Design new feature"
  → Morpheus (architecture) → Neo (implement) → Trin (test) → Oracle (document)

"Fix this bug"
  → Neo (quick fix) → Trin (test) → maybe Morpheus (if architectural impact)

"Why does this fail?"
  → Oracle (investigate) → Morpheus (design fix) → Neo (implement) → Trin (test)

"Review my code"
  → Morpheus (architecture check) → Trin (test coverage) → Oracle (document)

"Update documentation"
  → Oracle (always first for docs)
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/services/provisioning_service.py](../ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/services/provisioning_service.py) | Core provisioning logic; model for service design |
| [ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/commands/base.py](../ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/commands/base.py) | ApduCommand/AuthApduCommand base classes |
| [ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/hal.py](../ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/hal.py) | CardConnection interface and NTag424CardConnection |
| [ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/crypto/](../ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/crypto/) | Cryptographic primitives (CMAC, encryption) |
| [ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/constants.py](../ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/constants.py) | NTAG424-specific constants (SDMConfiguration, CommMode, etc.) |
| [ntag424_sdm_provisioner/ARCH.md](../ntag424_sdm_provisioner/ARCH.md) | Full architecture deep-dive |
| [ntag424_sdm_provisioner/DECISIONS.md](../ntag424_sdm_provisioner/DECISIONS.md) | Design decisions log (read for "why" context) |
| [ntag424_sdm_provisioner/docs/analysis/CHANGEKEY_SUCCESS.md](../ntag424_sdm_provisioner/docs/analysis/CHANGEKEY_SUCCESS.md) | Example of successful authentication and key change sequence |

---

## Integration with VS Code Tasks

The agentic personas are integrated into VS Code as **native tasks**, accessible via:
- **Command Palette**: `Ctrl+Shift+P` → "Run Task" → Select agent
- **Tasks Menu**: Terminal → Run Task
- **Keyboard**: `Ctrl+Shift+B` (build) or `Ctrl+Shift+T` (test)

### Available Agent Tasks

| Task | Persona | Purpose | Shortcut |
|------|---------|---------|----------|
| `Agent: Morpheus - Architecture Review` | Morpheus | Design decisions, code review | `Ctrl+Shift+B` |
| `Agent: Neo - Implement/Refactor` | Neo | Write code, fix bugs | `Ctrl+Shift+B` |
| `Agent: Trin - Quality Assurance` | Trin | Test, verify, quality gates | `Ctrl+Shift+T` |
| `Agent: Oracle - Documentation` | Oracle | Write docs, research | `Ctrl+Shift+B` |
| `Agent: Watch & Auto-Delegate` | Watcher | Auto-chain agent workflows | Background |
| `Agent: Show Status` | - | View recent CHAT.md entries | `Ctrl+Shift+T` |

### Workflow: Hybrid Multi-Agent Orchestration

```
Step 1: Invoke Initial Agent (VS Code Task)
└─ Run: "Agent: Morpheus - Architecture Review"
   └─ Loads agents/morpheus.docs/context.md
   └─ Task request written to agents/morpheus.docs/task_request.json
   └─ Morpheus reviews architecture, updates context.md
   └─ Writes agents/morpheus.docs/next_delegation.json

Step 2: Automatic Delegation (If Watcher Running)
└─ File watcher detects next_delegation.json
└─ Auto-invokes Neo with delegation context
└─ Neo reads morpheus's context via delegation message
└─ Neo implements changes, updates agents/neo.docs/context.md
└─ Neo writes next_delegation.json for Trin

Step 3: Chain Continues
└─ Trin runs QA, delegates to Oracle
└─ Oracle documents, chain complete
└─ All updates logged in agents/CHAT.md
```

### Manual vs Auto Delegation

**Without Watcher (Manual):**
```
1. Run: Agent: Morpheus - Architecture Review
2. Wait for completion
3. Run: Agent: Neo - Implement/Refactor (manually)
4. Run: Agent: Trin - Quality Assurance (manually)
5. Run: Agent: Oracle - Documentation (manually)
```

**With Watcher (Auto):**
```
1. Start: Agent: Watch & Auto-Delegate (background task)
2. Run: Agent: Morpheus - Architecture Review
3. Watcher detects delegation → auto-invokes Neo
4. Watcher detects delegation → auto-invokes Trin
5. Watcher detects delegation → auto-invokes Oracle
6. Stop watcher when complete
```

### State Files (Agent Communication)

Agents communicate through the file system:

```
agents/
├── CHAT.md                         # Shared delegation log
├── morpheus.docs/
│   ├── context.md                  # Architecture decisions
│   ├── task_request.json           # Input from previous agent
│   └── next_delegation.json        # Output to next agent
├── neo.docs/
│   ├── context.md                  # Implementation status
│   └── next_delegation.json
├── trin.docs/
│   ├── context.md                  # Test results
│   └── next_delegation.json
└── oracle.docs/
    └── context.md                  # Documentation status
```

Each agent:
1. **Reads** `task_request.json` (what to do)
2. **Reads** previous agent's `context.md` (background)
3. **Updates** its own `context.md` (work done)
4. **Writes** `next_delegation.json` (who's next)
5. **Posts** to `CHAT.md` (team visibility)

### Structuring Agent Input/Output

When invoking agents manually, provide structured requests:

**Morpheus Input** (`agents/morpheus.docs/task_request.json`):
```json
{
  "task": "architecture-review",
  "subject": "ProvisioningService refactor",
  "context_files": ["src/services/provisioning_service.py", "ARCH.md"],
  "constraints": ["preserve EV2 session semantics"],
  "blockers": []
}
```

**Morpheus Output** (`agents/morpheus.docs/context.md`):
```markdown
# Architecture Review - ProvisioningService

## Decision
Split provision_keys() from provision_url()

## Rationale
Allows separate provisioning workflows...

## Next Delegation
→ Neo: Implement the split
```

**Neo Input** (auto-provided by watcher):
```json
{
  "task": "implement",
  "objective": "Split ProvisioningService into provision_keys() and provision_url()",
  "context": "See agents/morpheus.docs/context.md for architecture decision"
}
```

---

## Code Quality Standards

**Drew's Engineering Principles (from AGENTS.md):**
- ✅ Write well-factored code optimized for maintainability
- ✅ Keep it DRY—use composition and abstraction to simplify and reuse
- ✅ Use explicit dependencies instead of singletons
- ✅ "We don't ship shit!"—all tests must pass before merging

**Common Patterns to Avoid:**
- Don't mix business logic and UI code
- Don't use unauthenticated commands for sensitive operations
- Don't manually edit tag_keys.csv (use CsvKeyManager)
- Don't forget to activate `.venv` before running commands
