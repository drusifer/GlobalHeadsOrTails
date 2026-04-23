# Product Requirements Document (PRD)
## NTAG424 SDM Provisioner TUI

**Version**: 1.0  
**Last Updated**: 2025-11-28  
**Owner**: Cypher (Product Manager)

---

## 1. Executive Summary

### Vision
Build a production-ready, user-friendly TUI (Text User Interface) application for provisioning NTAG424 DNA NFC tags with Secure Dynamic Messaging (SDM) capabilities. The application enables game developers and operations teams to efficiently provision physical game coins with authenticated NFC tags.

### Problem Statement
Current provisioning workflows require deep technical knowledge of NXP specifications, manual command-line operations, and error-prone key management. This creates a barrier to entry for non-technical users and slows down production workflows.

### Solution
A unified TUI application that abstracts away complexity while maintaining full control for power users. The application provides:
- Visual tag status checking
- One-click provisioning workflows
- Comprehensive diagnostics
- Secure key management
- Error recovery and retry mechanisms

---

## 2. Target Users

### Persona 1: Dev Dave (Developer)
- **Role**: Game developer integrating NFC tags
- **Technical Level**: Intermediate (Python knowledge, but confused by NXP datasheets)
- **Goals**: Quickly provision test tags, verify SDM configuration, debug issues
- **Pain Points**: Complex command-line tools, unclear error messages, manual key management
- **Success Criteria**: Can provision a tag in < 2 minutes without reading NXP docs

### Persona 2: Ops Olivia (Operations)
- **Role**: Production line operator
- **Technical Level**: Basic (can follow instructions, minimal technical knowledge)
- **Goals**: Provision hundreds of tags reliably, handle errors gracefully
- **Pain Points**: Batch operations, error recovery, key management at scale
- **Success Criteria**: Can provision 100 tags with < 1% error rate

### Persona 3: Sec Sam (Security Engineer)
- **Role**: Security auditor and key manager
- **Technical Level**: Advanced (cryptography expert)
- **Goals**: Verify cryptographic correctness, audit key management, ensure compliance
- **Pain Points**: Need to verify crypto implementation, audit key storage, ensure no hardcoded secrets
- **Success Criteria**: Can verify all crypto operations match NXP spec, keys are properly secured

---

## 3. Product Goals

### Primary Goals
1. **Usability**: Enable non-technical users to provision tags successfully
2. **Reliability**: 99%+ success rate for provisioning operations
3. **Security**: Zero hardcoded secrets, secure key management, cryptographic verification
4. **Maintainability**: Clean architecture, testable code, comprehensive documentation

### Success Metrics
- **Time to Provision**: < 2 minutes per tag (from tap to verified)
- **Error Rate**: < 1% provisioning failures
- **Test Coverage**: 80%+ code coverage, 100% on crypto operations
- **User Satisfaction**: Users can provision tags without consulting NXP documentation

---

## 4. Core Features

### 4.1 Tag Provisioning
**User Story**: As Dev Dave, I want to provision a tag with SDM configuration so that it serves authenticated URLs.

**Acceptance Criteria**:
- [ ] Application detects tag when tapped
- [ ] Application shows current tag status (Factory/Provisioned)
- [ ] Application updates all 5 keys (with clear warnings for Key 0 rotation)
- [ ] Application configures SDM on NDEF file (File 0x02)
- [ ] Application writes NDEF message with base URL
- [ ] Application verifies provisioning success
- [ ] Application displays success/failure with clear error messages
- [ ] Application supports retry on failure

**Technical Requirements**:
- Uses `ProvisioningService` (service layer pattern)
- Progress callbacks for UI feedback
- Error recovery (retry failed operations)
- Key rotation warnings (especially for Master Key)

### 4.2 Tag Diagnostics
**User Story**: As Dev Dave, I want to check tag status and read NDEF content so that I can verify tag state before/after operations.

**Acceptance Criteria**:
- [ ] Application displays tag UID
- [ ] Application shows tag status (Factory/Provisioned/Unknown)
- [ ] Application displays chip version information
- [ ] Application shows key versions for all 5 keys
- [ ] Application reads and displays NDEF content
- [ ] Application shows file settings (SDM configuration)
- [ ] Application displays CC file information
- [ ] All operations complete in < 5 seconds

**Technical Requirements**:
- Uses `TagDiagnosticsService` (service layer pattern)
- Non-destructive operations (no state changes)
- Fast response times (< 5s for full diagnostics)

### 4.3 Tag Maintenance
**User Story**: As Ops Olivia, I want to reset tags to factory state so that I can reprovision them if needed.

**Acceptance Criteria**:
- [ ] Application provides factory reset option
- [ ] Application warns user before reset (destructive operation)
- [ ] Application resets all keys to factory defaults
- [ ] Application resets file settings to factory state
- [ ] Application verifies reset success
- [ ] Application supports format operation (alternative to reset)

**Technical Requirements**:
- Uses `TagMaintenanceService` (service layer pattern)
- Clear warnings for destructive operations
- Verification after reset

### 4.4 Key Management
**User Story**: As Sec Sam, I want secure key storage so that keys are never exposed or hardcoded.

**Acceptance Criteria**:
- [ ] Keys stored in encrypted CSV (or secure key store)
- [ ] No keys hardcoded in source code
- [ ] Key derivation from UID supported
- [ ] Key backup/restore functionality
- [ ] Key rotation support
- [ ] Audit trail for key operations

**Technical Requirements**:
- Uses `CsvKeyManager` (or secure alternative)
- Environment variable support for local dev
- Key encryption at rest
- No secrets in version control

---

## 5. Technical Architecture

### 5.1 Service Layer Pattern
**Requirement**: All business logic must be in service classes, not in UI code.

**Services**:
- `ProvisioningService`: Tag provisioning logic
- `TagDiagnosticsService`: Status checking and diagnostics
- `TagMaintenanceService`: Reset and format operations

**Benefits**:
- Testable (services can be unit tested without UI)
- Reusable (services can be used by CLI, TUI, or API)
- Maintainable (single source of truth for business logic)

### 5.2 Hardware Abstraction
**Requirement**: UI must not depend on specific hardware (pyscard, ACR122U, etc.).

**Implementation**:
- Use `CardConnection` abstraction
- Services inject `CardConnection` (dependency injection)
- Hardware-specific code in HAL layer only

### 5.3 Security Requirements
**Requirement**: "We Don't Ship Shit" - Security is non-negotiable.

**Standards**:
- 100% test coverage on crypto operations
- All crypto verified against NXP spec vectors
- No hardcoded secrets
- Secure key storage
- Cryptographic verification of all operations

### 5.4 Error Handling
**Requirement**: Graceful error handling with clear user messages.

**Standards**:
- All errors caught and displayed clearly
- Retry mechanisms for transient failures
- Recovery strategies for interrupted operations
- Detailed logging for debugging

---

## 6. Quality Standards

### 6.1 Testing
**Requirement**: Comprehensive test coverage with focus on quality over quantity.

**Standards**:
- **Unit Tests**: 80%+ code coverage
- **Crypto Tests**: 100% coverage (non-negotiable)
- **Integration Tests**: Key workflows (provisioning, diagnostics)
- **No Dumb Tests**: Tests must verify actual logic, not library functions

**Test Strategy**:
- Incremental unit tests (test small units in isolation)
- Mock hardware for unit tests
- Simulator for integration tests
- Real hardware for acceptance tests

### 6.2 Code Quality
**Requirement**: Clean, maintainable, well-documented code.

**Standards**:
- PEP-8 compliance
- Type hints on all functions
- Docstrings for all public methods
- No code duplication (DRY principle)
- SOLID principles followed

### 6.3 Documentation
**Requirement**: Comprehensive documentation for users and developers.

**Deliverables**:
- User guide (HOW_TO_RUN.md)
- API documentation
- Architecture documentation (ARCH.md)
- Decision log (DECISIONS.md)
- Lessons learned (LESSONS.md)

---

## 7. Non-Functional Requirements

### 7.1 Performance
- Tag operations complete in < 10 seconds
- UI remains responsive during operations (async/threading)
- Diagnostics complete in < 5 seconds

### 7.2 Reliability
- 99%+ success rate for provisioning
- Graceful handling of tag removal during operations
- Automatic retry for transient failures

### 7.3 Usability
- Clear, intuitive UI
- Progress indicators for long operations
- Helpful error messages
- Keyboard shortcuts for power users

### 7.4 Compatibility
- Windows 10+ support (primary)
- Linux support (secondary)
- ACR122U reader support (primary)
- Generic PC/SC reader support (secondary)

---

## 8. Out of Scope (Phase 1)

### Not Included
- Batch provisioning UI (CLI only for now)
- Web API interface
- Mobile app
- Advanced key management UI
- Tag emulation/simulation mode
- Multi-tag operations

### Future Considerations
- Batch provisioning TUI
- Web dashboard
- Advanced analytics
- Cloud key management integration

---

## 9. Definition of Done

A feature is "Done" when:
- [ ] All acceptance criteria met
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Code review approved by Morpheus
- [ ] QA verification by Trin
- [ ] Documentation updated
- [ ] No regressions introduced
- [ ] User can complete the workflow without consulting NXP docs

---

## 10. Risks and Mitigations

### Risk 1: Key Management Security
- **Risk**: Keys exposed or compromised
- **Mitigation**: Secure storage, encryption at rest, audit trail

### Risk 2: Provisioning Failures
- **Risk**: Tags left in inconsistent state
- **Mitigation**: Transaction-like operations, rollback on failure, recovery strategies

### Risk 3: Hardware Compatibility
- **Risk**: Works on one reader but not another
- **Mitigation**: Hardware abstraction layer, comprehensive testing on multiple readers

### Risk 4: User Error
- **Risk**: Users accidentally reset tags or lose keys
- **Mitigation**: Clear warnings, confirmation dialogs, backup/restore functionality

---

## 11. Success Criteria

### MVP Success
- [ ] Users can provision tags via TUI
- [ ] Users can check tag status
- [ ] Users can reset tags
- [ ] All operations have >80% test coverage
- [ ] Zero hardcoded secrets
- [ ] Documentation complete

### Full Success
- [ ] < 2 minute provisioning time
- [ ] < 1% error rate
- [ ] 100% crypto test coverage
- [ ] Users can operate without NXP docs
- [ ] Production-ready for game coin manufacturing

---

## 12. Dad Jokes Feature

**Added**: 2026-03-26
**Owner**: Cypher

### 12.1 Dad Jokes Catalog & Web Display

**User Story**: As a visitor to the Heads vs Tails results page, I want to see a randomly chosen Dad Joke each time I load the page, so the experience is fun and memorable.

**Scope**:
- A static in-code catalog of Dad Jokes (no external API dependency)
- One randomly selected joke displayed on the web page per visit
- No persistence or user interaction required for MVP

**Acceptance Criteria**:
- [ ] A catalog of at least 20 Dad Jokes exists in the codebase (static list, server-side)
- [ ] On each page load, one joke is selected at random from the catalog
- [ ] The selected joke is rendered on the `index.html` page in a visually distinct section
- [ ] The joke section is always visible, regardless of coin flip outcome (even on error states)
- [ ] No external API calls are made to fetch jokes
- [ ] Adding more jokes to the catalog requires no template changes (data-driven)

**Technical Notes**:
- Jokes catalog can be a Python list in the Flask app (or a separate module)
- Use `random.choice()` server-side to select the joke; pass to template via `render_template`
- Display area should be styled to fit the existing page aesthetic

**Definition of Done**:
- [ ] Jokes catalog defined in Python (≥20 jokes)
- [ ] Flask route passes `joke` variable to `index.html` template on all render paths
- [ ] Template renders joke in a styled section
- [ ] Unit test confirms a joke is always returned (not None/empty)
- [ ] Code review approved by Morpheus
- [ ] QA sign-off by Trin

---

---

## 13. Flip Off Challenge Feature

**Added**: 2026-03-26
**Updated**: 2026-03-26
**Owner**: Cypher

### 13.1 Overview

A Flip Off is a peer-to-peer challenge between two NFC coins, decided by Shannon entropy over a fixed number of future flips. The challenger taps their coin to load the page, selects an opponent from the Flip Offs section, and chooses a battle size. The next N real flips from each coin are collected; the coin with higher entropy wins. Challenges expire after 24 hours if not completed. Either participant may yield at any time, granting the opponent an immediate win. All battle state updates in real-time via SSE for all viewers.

---

### 13.2 User Stories

**US-1 — Start a challenge**
As a coin owner who has just tapped my coin, I want to select a rival coin and battle size from the Flip Offs section, so I can initiate a competition without leaving the page.

**US-2 — Track progress in real time**
As a participant or spectator, I want to see live progress bars and flip counts for all active battles update automatically, so I always know where each battle stands without refreshing.

**US-3 — See the result**
As a coin owner whose battle just ended, I want to see a result card showing who won and both entropy scores, so I know the outcome and understand why.

**US-4 — Yield**
As a participant in an active battle, I want to be able to surrender at any time, so I can concede gracefully rather than let a battle expire or drag on.

**US-5 — Expiry countdown**
As a participant, I want to see a live countdown to my battle's 24-hour deadline, so I know how much time I have left to complete my flips.

**US-6 — Leaderboard record**
As any user, I want to see each coin's flip-off win/loss/draw record on the leaderboard, so I can compare competitive history alongside randomness stats.

**US-7 — Recent results**
As any visitor, I want to see the last three completed flip-offs in the Flip Offs section without needing a coin, so I can follow the action even as a spectator.

---

### 13.3 Acceptance Criteria

#### Challenge Creation
- [x] Flip Offs section visible on the page to all visitors (no coin required)
- [x] Coin owners (page loaded via NFC tap) see a "+ Start Flip-Off" button when not in an active battle
- [x] Opponent list is sorted alphabetically and excludes the current coin
- [x] Opponent list shows flip count and entropy for each option
- [x] Battle sizes available: 10, 25, 50, 100 flips
- [x] A coin may not challenge itself
- [x] A coin may not have more than one active challenge at a time
- [x] Challenge creation stays on-page (JS fetch, no navigation)
- [x] New active battle appears for all viewers via SSE immediately after creation

#### Flip Collection
- [x] Only real CMAC-validated flips (not test taps) count toward challenge progress
- [x] Only flips recorded after challenge creation count (baseline scan ID)
- [x] Progress bars and flip counts update in real time via SSE for all viewers
- [x] Live flip indicator shows during active battles

#### End Conditions
- [x] **Win/Draw**: when both coins reach N flips, entropy is compared; higher entropy wins; equal entropy is a draw
- [x] **Yield**: either participant (challenger or challenged) may surrender at any time; opponent wins immediately
- [ ] **Expired**: challenges not completed within 24 hours are auto-marked expired; triggered lazily on each page load or flip
- [ ] End condition is stored as a typed field (`win` / `draw` / `yield` / `expired`) on the challenge record

#### Result Display
- [x] Completed result card shown to coin owners for their most recent completed battle
- [x] Result card hidden while coin is in an active battle; shown again when battle ends via SSE
- [x] Result card shows: winner name (or "Draw"), both coin names, both entropy scores
- [x] Fanfare overlay shown to participants only (not spectators) on battle completion
- [x] Fanfare distinguishes winner ("You Win!"), loser ("X Won"), and draw
- [ ] Fanfare distinguishes yield from entropy-decided outcome

#### Expiry Countdown
- [x] Each active battle shows a live countdown to its 24-hour expiry deadline
- [x] Countdown turns red inside the final hour
- [x] Countdown ticks every second

#### Recent Results
- [x] Last 3 completed battles shown in the Flip Offs section for all viewers
- [x] Results show winner (highlighted), loser (dimmed), both entropy scores, flip count
- [ ] Recent results update via SSE (currently only updates on expiry events; missing from flip/create/yield SSE payloads)

#### Leaderboard
- [x] W / L / D columns added to leaderboard table
- [x] Stats sourced from all completed challenges (any end condition)

#### Data & Integrity
- [x] `flip_off_challenges` table with baseline scan ID, status, entropy fields, completed_at
- [x] Challenges stored by coin_name (not UID)
- [ ] `end_condition` column added to `flip_off_challenges` (pending)
- [x] `get_latest_challenge` excludes expired challenges from result card
- [x] Unit tests: creation, duplicate guard, flip counting, entropy winner, draw, expiry

---

### 13.4 User Flow

```
1. User taps NFC coin → page loads with coin identity
2. Flip Offs section shows: recent results, any active battles, "+ Start Flip-Off" button
3. User expands form, selects opponent (alphabetical list) and battle size
4. JS POST to /challenge/create → SSE pushes new active battle to all viewers
5. Both coins accumulate real validated flips post-creation
6. Progress bars update in real time via SSE on each flip
7. Expiry countdown ticks live; turns red in final hour
8. Battle ends by:
   a. Both coins reach N flips → entropy compared → win or draw
   b. Either coin taps Yield → opponent wins immediately
   c. 24 hours elapse without completion → expired (lazy, on next request)
9. SSE push: active battles updated, result appears in recent results
10. Participants see result card; winner gets fanfare overlay
```

---

### 13.5 Shannon Entropy Scoring

- Entropy calculated over N challenge flips per coin using `calculate_entropy()` from `crypto_primitives.py`
- Encoding: HEADS=1, TAILS=0; bit string padded to nearest byte boundary
- Higher entropy (closer to 8.0 bits/byte) = more random coin = winner
- Both scores displayed on result card with 4 decimal places
- Tie: entropy equal to 4 decimal places → draw

---

### 13.6 Database Schema

```sql
CREATE TABLE flip_off_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    baseline_scan_id INTEGER NOT NULL DEFAULT 0,
    challenger_coin_name TEXT NOT NULL,
    challenged_coin_name TEXT NOT NULL,
    flip_count INTEGER NOT NULL CHECK(flip_count IN (10, 25, 50, 100)),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'in_progress', 'complete', 'expired')),
    challenger_flips_done INTEGER NOT NULL DEFAULT 0,
    challenged_flips_done INTEGER NOT NULL DEFAULT 0,
    challenger_entropy REAL,
    challenged_entropy REAL,
    winner_coin_name TEXT,
    completed_at DATETIME,
    end_condition TEXT CHECK(end_condition IN ('win', 'draw', 'yield', 'expired'))  -- pending migration
);
```

---

### 13.7 SSE Architecture

All flip-off UI state is delivered via SSE (`/api/stream/flips`). HTTP action endpoints return ACK only.

| SSE field | Content |
|---|---|
| `active_challenges` | All pending/in_progress challenges |
| `recent_completed` | Last 3 completed challenges |
| `just_completed` | Battles completed by this specific event (triggers fanfare/result card) |
| `latest_flip` | Most recent flip (drives live indicator during active battles) |

EventSource is always connected regardless of page state. All clients (participants and spectators) receive all flip-off events.

---

### 13.8 Out of Scope

- Push notifications when a challenge completes
- Multi-coin tournaments (bracket play)
- Wagering or scoring system
- Challenge invitations via QR code or link
- Spectator fanfare for battle completion

---

### 13.9 Exit Criteria

All items must be met before this feature is considered complete.

#### Must pass (blocking)
- [ ] All unit tests pass: `test_server_flip_off.py`, `test_server_flip_off_integration.py`
- [ ] `end_condition` column added; set correctly for win/draw/yield/expired
- [ ] `recent_completed` included in SSE payloads from `/api/flip`, `/challenge/create`, `/challenge/yield`
- [ ] Recent results section updates via SSE on every end condition (not only expiry)
- [ ] Expired challenges marked within one request cycle after 24h deadline
- [ ] Fanfare text distinguishes yield ("Opponent Yielded" / "You Yielded") from entropy win/loss
- [ ] QA sign-off by Trin

#### Already passing (regression guard)
- [x] Challenge creation stays on-page; no navigation away
- [x] Both challenger and challenged can yield
- [x] All active battles visible to all viewers (no coin required)
- [x] Countdown timer visible and ticks to zero
- [x] Countdown urgent state (red) inside final hour
- [x] Result card shows for coin's most recent completed battle
- [x] Result card hides when coin enters a new active battle
- [x] Fanfare shown to participants only
- [x] W/L/D columns on leaderboard
- [x] Opponent list alphabetically sorted
- [x] Live tap indicator only during active battles

---

**Document Status**: Active — implementation in progress
**Last Updated**: 2026-03-26
**Open items**: end_condition column, SSE payload standardization, renderRecentCompleted migration, yield fanfare text

---

## 14. Custom Coin Messages Feature

**Added**: 2026-04-22
**Owner**: Cypher
**Implemented by**: Neo

### 14.1 Overview

Coin owners can personalize the HEADS and TAILS outcome text displayed on the flip results page. Messages are stored per coin and shown in place of the default "HEADS" / "TAILS" text. Access to the customization form is gated on a valid, non-replayed NFC tap — proving physical possession of the coin.

---

### 14.2 User Stories

**US-1 — Set custom messages**
As a coin owner who has just tapped my coin, I want to set a custom message for HEADS and TAILS outcomes, so my coin has a unique personality on the results page.

**US-2 — See my custom messages on flip**
As a coin owner or spectator, I want to see the coin's custom outcome text when a flip lands, so the result feels personal and distinctive.

**US-3 — Form access controlled by tap validity**
As a system, I want the customization form to appear only when the NFC tap CMAC is cryptographically valid and not a replay, so only the physical coin holder can modify messages.

---

### 14.3 Acceptance Criteria

#### Form Display
- [x] Customization form is hidden by default on page load
- [x] A ✏️ icon appears above the params table, right-aligned, when the tap is valid
- [x] Clicking ✏️ expands the form above the params table; icon changes to ❌
- [x] Clicking ❌ collapses the form; icon reverts to ✏️
- [x] The ✏️/❌ icon is **not shown** when:
  - There is no NFC tap in the URL
  - The CMAC is invalid (crypto verification fails)
  - The counter is a replay (`ctr ≤ last_counter`)
  - The flip returns "Replay Detected" error

#### Message Constraints
- [x] Each message (heads and tails) is capped at **24 characters**
- [x] Character limit enforced in the HTML form (`maxlength="24"`) and server-side
- [x] Long custom outcome text wraps within the header rather than overflowing (`word-break: break-word`)

#### Save Authentication
- [x] Save request sends `uid`, `cmac`, and `ctr` from the tap URL (baked into hidden form fields at render time)
- [x] Server validates the CMAC cryptographically against the tag's SDM MAC key — no database lookup required
- [x] No "tap again" prompt — the tap that opened the page is sufficient for one save
- [x] Auth failure returns 401; generic error shown (no misleading "tap again" UX)

#### Persistence & Display
- [x] Messages stored in `coin_custom_messages` table (`coin_name`, `heads_message`, `tails_message`)
- [x] Custom messages displayed in place of "HEADS"/"TAILS" in the outcome scramble animation
- [x] Custom messages used in the live flip indicator during Flip Off battles
- [x] Empty message falls back to default "HEADS" / "TAILS"

---

### 14.4 Auth Model

Authentication is based on the NTAG424 CMAC from the tap URL — the same mechanism used by `/api/flip`. No session tokens or DB-stored state are involved.

**Index route gate** (`/`):
- `coin_name` (and thus the ✏️ button and form) is only set when:
  1. `uid`, `ctr`, and `cmac` are all present in the URL
  2. `ctr_int > last_counter` (not a replay)
  3. `validate_sdm_url(uid, ctr_int, cmac)["valid"]` returns True

**Save endpoint** (`POST /api/coin/messages`):
- Receives `uid`, `cmac`, `ctr` from form hidden fields
- Calls `key_manager.validate_sdm_url(uid, ctr_int, cmac)` directly
- Returns 401 if CMAC invalid; 400 if fields missing or message too long

---

### 14.5 Database Schema

```sql
CREATE TABLE IF NOT EXISTS coin_custom_messages (
    coin_name     TEXT PRIMARY KEY,
    heads_message TEXT NOT NULL DEFAULT '',
    tails_message TEXT NOT NULL DEFAULT ''
);
```

---

### 14.6 Out of Scope

- Per-tap message preview before saving
- Message history / undo
- Emoji or special character validation beyond length
- Admin override of coin messages

---

### 14.7 Definition of Done

- [x] Form hidden by default; revealed only on valid tap
- [x] ✏️/❌ toggle works correctly; form opens above params table
- [x] CMAC auth works without DB lookup
- [x] Replay detection gates the edit button
- [x] 24-char limit enforced client and server side
- [x] Long messages wrap in outcome display
- [x] Debug logging in save endpoint
- [ ] Unit tests for `set_coin_messages` (auth pass/fail, length validation)
- [ ] QA sign-off by Trin

---

## 15. Security: Secret Masking in Logs

**Added**: 2026-04-22
**Owner**: Cypher
**Implemented by**: Neo

### 15.1 Overview

AES-128 key material (stored keys, derived session keys, intermediate CMACs) was previously emitted in plaintext to application logs at INFO and DEBUG level. This is now masked using a shared utility.

### 15.2 Requirements

- [x] `log_utils.mask_key(key: str) -> str` utility created at package root — shows only first 4 and last 4 hex chars (`AABB...3344`)
- [x] Applied in `csv_key_manager.py`: PICC Master Key, App Read Key, SDM MAC Key, SDM MAC key bytes, Session Key, Full CMAC (16-byte), per-byte CMAC breakdown removed
- [x] Applied in `services/diagnostics_service.py`: Session key from validation result dict
- [x] Applied in `server/app.py`: `safe` dict built before logging validation result, masking `session_key` and `full_cmac` fields
- [x] `get_tag_keys` print statement no longer dumps full CSV row via `json.dumps` — logs only `coin_name` and `status`
- [x] `TagKeys.__str__` masks all three key fields (affects any debug log that calls `str(tag_keys)`)

### 15.3 Not Masked (intentionally public)

- UID (NFC tag identifier, present in every URL)
- Counter / CTR (increments publicly with each tap)
- SV2 / System Vector (derived from public UID + counter)
- CMAC message string (derived from public data)
- Truncated CMAC (8 bytes already present in the tap URL)
- `cmac_received` / `cmac_calculated` comparison (truncated, public)

