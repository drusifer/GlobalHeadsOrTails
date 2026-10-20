# BobProtocol Documentation Index

**Last Updated:** 2026-10-19

## Generic Declarative Art Generator & Pack Catalogs

- [Generic Art Generator Guide](oracle.docs/art_generator_guide.md)
- [Art Generator Architecture Specification](morpheus.docs/arch_art_generator.md)
- [Art Generator Refactor Sprint Plan](cypher.docs/art_generator_sprint.md)
- [Rangers Target Roster & Artwork Guide](../tools/RANGERS_STICKER_TARGETS.md)
- [Sticker Pack Catalogs & Manifests](../game_server/src/game_server/sticker_catalog/)
- [Generic Art Generator Engine](../tools/art_generator.py)

## Collectables & Game Server

- [Feature guide and validation commands](../docs/COLLECTABLES.md)
- [Accepted requirements, PRD §16](../docs/PRD.md)
- [Sprint stories and architecture](cypher.docs/collectables_sprint.md)
- [Entropy-weighted awards stories and architecture](cypher.docs/entropy_stickers_sprint.md)
- [Smith faction catalog and UX criteria](smith.docs/collectables_catalog.md)

## Quick Access

Type `*help` for complete command reference with examples.

---

## Primary Documentation

### Getting Started
- **[STARTUP.md](../STARTUP.md)** - LLM startup instructions
- **[README.md](../README.md)** - Project overview and team reference
- **[SHORTHAND_GUIDE.md](../SHORTHAND_GUIDE.md)** - Complete trigger/command reference
- **[HELP.md](bob/HELP.md)** - Quick reference for all 8 personas and commands

### Tools
- **[tools/](tools/)** - Agent tooling scripts (`chat.py`, `mkf.py`, `setup_agent_links.py`)

---

## Persona Documentation

### Active Personas (8)

| Persona | Role | SKILL.md | Prefix |
|---------|------|----------|--------|
| Bob | Prompt Engineering Expert | [bob/SKILL.md](bob/SKILL.md) | `*new` / `*reprompt` / `*learn` |
| Cypher | Product Manager | [cypher/SKILL.md](cypher/SKILL.md) | `*pm` |
| Morpheus | Tech Lead / Architect | [morpheus/SKILL.md](morpheus/SKILL.md) | `*lead` |
| Neo | Senior Software Engineer | [neo/SKILL.md](neo/SKILL.md) | `*swe` |
| Oracle | Knowledge Officer | [oracle/SKILL.md](oracle/SKILL.md) | `*ora` |
| Trin | QA / Guardian | [trin/SKILL.md](trin/SKILL.md) | `*qa` |
| Mouse | Scrum Master | [mouse/SKILL.md](mouse/SKILL.md) | `*sm` |
| Smith | Expert User & UX Advocate | [smith/SKILL.md](smith/SKILL.md) | `*user` |

---

## Team Communication

- **[CHAT.md](CHAT.md)** - Team communication log (append-only)
- Each persona maintains state in their `<name>/` folder:
  - `context.md` - Working memory
  - `current_task.md` - Active work
  - `next_steps.md` - Resume plan

---

## Template Files

Located in `agents/templates/`:

- `_template_ARCH.md` - Architecture decision record
- `_template_CHAT.md` - CHAT.md message format
- `_template_context.md` - Agent context.md
- `_template_current_task.md` - Agent current_task.md
- `_template_finding.md` - Research finding
- `_template_LESSON.md` - Lesson learned
- `_template_next_steps.md` - Agent next_steps.md
- `_template_tldr.md` - TLDR block formats

---

## Tools Directory

**Location:** `agents/tools/`

- `chat.py` - Post messages to CHAT.md
- `mkf.py` - Build output filter (routes make output)
- `setup_agent_links.py` - Create `.claude/skills/` symlinks (run once on setup)

---

## Project Knowledge Base (`docs/`)

| File | Purpose |
|------|---------|
| `docs/DECISIONS.md` | Architecture decisions log (12 entries; latest workspace component reorg & cleanup) |
| `sdm_provisioner/ARCH.md` | System architecture — provisioner TUI service layer |
| `docs/LESSONS.md` | Lessons learned |
| `docs/PRD.md` | Product Requirements Document (§16 collectables and weighted awards current) |
| `docs/ROADMAP.md` | Feature roadmap |
| `docs/ISO Compliant NDEF Reference.md` | NDEF/NXP reference specification |
| `task.md` | Sprint log (current + recent sprints) |

## Morpheus Architecture Docs

| File | Status |
|------|--------|
| `morpheus/arch_flipoff.md` | Active — Flip-Off challenge design |
| `morpheus/arch_custom_messages.md` | Active — Custom coin messages |
| `morpheus/arch_flipoff_sse.md` | **SUPERSEDED** — SSE design (replaced by polling 2026-04-22) |

---

## Archived Documentation

Files prefixed with `.archive_` are historical and no longer active:
- `.archive_COMMANDS.md` - (Consolidated into HELP.md)
- `.archive_state_management_fix.md` - (Implemented in protocol)

Root-level VS Code era docs (2025-12) archived to `docs_archive/`.

---

## Documentation Standards

### File Naming
- Persona definitions: `[PersonaName]_[ROLE]_AGENT.md`
- State files: `context.md`, `current_task.md`, `next_steps.md`
- MCP tools: `[toolname]_mcp.md`
- Templates: `_template_*.md`
- Archived: `.archive_*.md`

### Structure
- All persona docs in `agents/[persona]/`
- All MCP tool docs in `agents/tools/`
- Team communication in `agents/CHAT.md`
- Primary references in `agents/bob/`

### Maintenance
- Update `*help` when adding commands
- Update tool docs when changing MCPs
- Archive outdated docs with `.archive_` prefix
- Keep HELP.md, BOB_SYSTEM_PROTOCOL.md, and START_HERE.md in sync

---

## Quick Command Reference

```bash
*help                          # Show complete help
*chat                          # Activate Bob System
*prompt <desc>                 # Create agent (Bob)
*swe impl <task>              # Implement (Neo)
*qa test <scope>              # Test (Trin)
*ora ask <question>           # Query knowledge (Oracle)
*lead plan <epic>             # Plan (Morpheus)
*pm doc <type>                # Create PRD (Cypher)
*sm status                    # Sprint status (Mouse)
```

---

**For Help:** Type `*help` or read `agents/bob/HELP.md`

- [Quota block and exact missing player IDs](neo/rangers_art_blocker.json)
