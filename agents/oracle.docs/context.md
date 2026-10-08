# Oracle Context

## Recent Decisions

### Collectables sprint — 2026-10-06
- Recorded coin-owned collection/atomic reward-and-wager persistence in project DECISIONS.md §6 and PRD §16.
- Feature guide: ntag424_sdm_provisioner/docs/COLLECTABLES.md; art workflow: tools/STICKER_ART.md; indexed in agents/DOCUMENTATION_INDEX.md.
- Existing tracked app.db receives migrations on module import during tests. Restore only the session-generated DB delta after the final checks; do not ship local runtime contents.

### Groom Pass — 2026-04-22
Complete doc groom executed. See current_task.md for full list.

## Key Findings
- **Root clutter (2025-12 era)**: 9 VS Code integration docs archived to `docs_archive/`
- **NDEF reference**: was at root, moved to `ntag424_sdm_provisioner/docs/`
- **SSE arch doc**: `agents/morpheus.docs/arch_flipoff_sse.md` — marked SUPERSEDED (SSE replaced by polling 2026-04-22)
- **DECISIONS.md**: Added §5 SSE→Polling decision
- **task.md**: Updated to reflect §14 complete + SSE refactor complete
- **DOCUMENTATION_INDEX.md**: Added project knowledge base table + arch docs status table

## Important Notes
- Root now has only 3 files: `AGENTS.md`, `START_HERE.md`, `task.md` (all intentional)
- `AGENTS.md` at root = duplicate of `agents/AGENTS.md` — intentional (different AI indexing)
- `docs_archive/` at root contains stale 2025-12 VS Code integration docs
- `ntag424_sdm_provisioner/docs_archive/` contains older provisioner session/investigation docs

---
*Last updated: 2026-04-22*
