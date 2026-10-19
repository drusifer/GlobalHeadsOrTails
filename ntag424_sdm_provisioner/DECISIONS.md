# Project Decisions Log

This document records key decisions made during the project lifecycle.

## Format
- **Context**: The problem or situation.
- **Decision**: The choice made.
- **Consequences**: The impact (pros/cons).
- **Status**: [Proposed | Accepted | Deprecated]
- **Date**: YYYY-MM-DD

---

## 1. Documentation Structure Reorganization
- **Context**: The project root was cluttered with loose markdown files, making navigation difficult and "source of truth" unclear.
- **Decision**: Adopt a strict directory structure:
    - `docs/specs/`: External specifications and datasheets.
    - `docs/analysis/`: Investigation notes, findings, and experiment logs.
    - `docs/status/`: Progress reports and session summaries.
    - `docs/archive/`: Deprecated or superseded documents.
    - Root: Only core knowledge base files (`MINDMAP.md`, `ARCH.md`, `LESSONS.md`, `DECISIONS.md`, `OBJECTIVES.md`, `README.md`).
- **Consequences**: Improved discoverability and organization. Requires updating links in `README.md`.
- **Status**: Accepted
- **Date**: 2025-11-21

## 2. SDM URL Template Fix & CI Standardization
- **Context**: 
    1. `SDMUrlTemplate` had a bug where `read_ctr_placeholder` was incorrectly named `ctr_placeholder`, causing TypeErrors.
    2. Test execution was inconsistent due to ambiguity between system Python and `.venv` Python.
- **Decision**: 
    - Rename parameter to `read_ctr_placeholder` in `SDMUrlTemplate` (verified by `test_sdm_url_template_fix.py`).
    - Enforce `.venv` activation as the **primary** workflow in `HOW_TO_RUN.md`.
- **Consequences**: 
    - Fixes runtime errors in URL generation.
    - Reduces "command not found" or dependency errors for developers.
- **Status**: Accepted
- **Date**: 2025-11-23

## 3. Service Layer Architecture (Per PRD)

- **Context**: PRD Section 5.1 requires all business logic to be in service classes, not UI code. Current architecture had tool-based pattern with business logic mixed in TUI commands.
- **Decision**: Adopt service-oriented architecture with three core services:
  - `ProvisioningService`: Tag provisioning logic
  - `TagDiagnosticsService`: Status checking and diagnostics
  - `TagMaintenanceService`: Reset and format operations
- **Implementation**:
  - Services are UI-agnostic (use callbacks for progress)
  - Services use dependency injection (CardConnection, KeyManager)
  - TUI screens delegate to WorkerManager, which runs services asynchronously
  - Services can be reused by CLI, TUI, or future API
- **Consequences**:
  - ✅ Eliminates code duplication between CLI and TUI
  - ✅ Services are testable with mocks (no hardware dependency)
  - ✅ Single source of truth for business logic
  - ✅ TUI screens contain only UI concerns
- **Status**: Accepted
- **Date**: 2025-11-28
- **Related**: PRD Section 5.1, ARCH.md updated

## 4. ChangeFileSettings Command Authentication Requirement
- **Context**: 
    Investigation of 917E (NTAG_LENGTH_ERROR) during SDM provisioning revealed that the ChangeFileSettings command was being sent unencrypted (plain APDU with LC=0x0D, 13 bytes) instead of encrypted with CMAC. This occurred because example code had a "backwards compatibility" fallback that used the plain `ChangeFileSettings` class instead of `ChangeFileSettingsAuth`.
- **Decision**: 
    Per NXP AN12196 specification and NTAG424 DNA datasheet, the ChangeFileSettings command MUST always be sent with authentication (encrypted payload + CMAC). The plain/unauthenticated version violates the NXP spec and causes the tag to reject the command with 917E LENGTH_ERROR.
    - Always use `ChangeFileSettingsAuth` (AuthApduCommand subclass)
    - Never use plain `ChangeFileSettings` for production code
    - Removed backwards-compat fallback in `22_provision_game_coin.py` line 780
- **Consequences**: 
    - ✅ Fixes 917E error that blocked SDM provisioning
    - ✅ Ensures compliance with NXP security requirements  
    - ✅ SDM placeholders (UID, CTR, CMAC) will now be dynamically replaced by the tag
    - ⚠️ Breaking change: Plain mode no longer supported (but was never spec-compliant anyway)
- **Status**: Accepted
- **Date**: 2025-11-23

## 5. Replace SSE with Two-Endpoint Polling
- **Context**:
    The server used Server-Sent Events (SSE) via `GET /api/stream/flips` to push real-time flip updates to browsers. This required `gevent` for async queue signalling, held persistent connections open (fragile through proxies), maintained an in-memory `_sse_listeners` list (lost on restart), and forced a timing race where `/api/flip` could only be called after the SSE `onopen` event fired.
- **Decision**:
    Replace SSE with a cheap two-endpoint poll protocol:
    - `GET /api/flips/since?ts=<ISO>` → `{"has_new": bool}` — single `SELECT 1 FROM scan_logs WHERE timestamp > ? LIMIT 1`
    - `GET /api/state?since=<ISO>` → full state payload (recent_flips, totals, active_challenges, recent_completed, latest_flip, just_completed, latest_timestamp)
    - Client polls every 3 seconds; full state fetch only fires when `has_new=true`
    - Fire `/api/flip` immediately on page load — no waiting for a stream connection
    - Remove `gevent` from server dependencies entirely
- **Consequences**:
    - ✅ Eliminates gevent dependency and monkey-patching complexity
    - ✅ Stateless server — no per-client queues, survives restarts
    - ✅ Works transparently through proxies, load balancers, nginx
    - ✅ Simplified client code — no EventSource race condition
    - ✅ Check endpoint is extremely cheap (indexed SQL, one row)
    - ⚠️ ~20 lightweight requests/min per open tab (acceptable for SQLite)
- **Status**: Accepted
- **Date**: 2026-04-22
- **Related**: `agents/morpheus.docs/context.md`, `tests/test_server_polling.py`

## 6. Coin-owned Collectables and Atomic Sticker Wagers
- **Context**: Random rewards and wagers must survive retries, concurrent taps and worker crashes without duplicate awards, lost stakes or counted-but-unrewarded flips.
- **Decision**: Retain coin identity and SQLite. Persist individual sticker copies and per-UID/counter award decisions. Commit the genuine scan, reward/evolution, challenge progress and terminal stake transfer in one `BEGIN IMMEDIATE` transaction. Exclude locked copies from automatic 3:1 evolution. Authenticate wager actions from the signed tap's resolved coin, and recheck yield authorization against the actual current wager inside its write transaction.
- **Consequences**: Existing databases migrate without resetting data. Each wager has fixed exact-copy terms, explicit opponent acceptance and exactly-once terminal settlement. Public collection reads poll independently because an offer/acceptance can happen without a new flip. The original polling completion overlay now deduplicates battle IDs.
- **Status**: Accepted
- **Date**: 2026-10-06
- **Related**: `docs/COLLECTABLES.md`, `docs/PRD.md` §16, `../agents/cypher.docs/collectables_sprint.md`.

## 7. Entropy-weighted sticker drops
- **Decision**: Use exact Heads/Tails counts pooled by coin name across both face UIDs. Drop chance is 0.5 * max(0.1, entropy/8 * p_weight), a 5%-50% range. Monobit p_weight is neutral before 100 actual flips; at 100 it becomes erfc(abs(heads-tails)/sqrt(2*n)). Do not reuse byte-padded leaderboard metrics.
- **Persistence**: Genuine scan, score snapshot, award, evolution and battle progression share one transaction. Test scans/awards also commit together; retry returns its stored decision before inserting a scan. Test history never contributes to real odds. Legacy ledger rows remain readable without new metadata.
- **UX**: Show current chance, early-history explanation and physical-flip guidance. Balance scores cannot prove randomness or guarantee a sticker.
- **Status**: Accepted, 2026-10-07; Smith gates and Morpheus code review approved.

## 8. Archive-safe multi-pack Rangers collection
- **Context**: Full historical player coverage and changing seasons must preserve old collections, wagers, evolution and award replay without per-UID ownership splits.
- **Decision**: Keep globally unique stable family IDs and coin-name inventory, with a validated immutable multi-pack registry and indexed family/form lookup. Only the active pack draws new awards. Rangers uses direct individual rarity weights 8/4/2/1; Twelve Clans retains its existing tier-first policy. Public polling sends pack headers plus owned-family metadata rather than the whole historical roster.
- **Artwork**: One unique original portrait per player, shared by three structural/text-labeled CSS treatments. Full 1,162 portraits/3,486 form references must validate before activation. Reuse the existing Recard-backed safe generator, validator and packer; retain resumable masters, per-ID locks and portable source audits. Generic NHL silhouettes are rejected. Candidate downloads do not verify likeness; disclose archival interpretations where no usable photo exists.
- **Consequences**: No ownership DB migration; historic awards and stakes remain readable. Stats stay Rangers-only, split by competition and role with historical nulls preserved. Old pack stays active until full-art/final-review gates pass.
- **Status**: Accepted, 2026-10-07; Smith story/architecture/actual 18-card sample and Morpheus reviews approved. Production BLOCKED by quota at478 masters/684 missing; reset2026-10-08 22:44:02 America/New_York. No image calls before reset; preserve valid masters and clear only confirmed stale locks.147 QA and isolated active-browser approvals cover preparation only; no release claim.
