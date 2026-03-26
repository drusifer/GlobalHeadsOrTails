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
**Owner**: Cypher

### 13.1 Overview

A Flip Off is a peer-to-peer challenge between two NFC coins, decided by Shannon entropy over a fixed number of future flips. The challenger initiates via a validated NFC tap, selects an opponent from the leaderboard, and chooses the battle size. The next N real flips from each coin are collected; the coin with higher entropy (closer to 1.0 bits/bit) wins.

---

### 13.2 User Story

**As a coin owner**, I want to tap my coin on the leaderboard page, select a rival coin, choose a battle size, and let the next N flips from each coin decide the winner by Shannon entropy — so there's a competitive, fair, physics-driven challenge.

---

### 13.3 Acceptance Criteria

#### Challenge Creation
- [ ] On the leaderboard page, each coin row has a "Challenge" button
- [ ] Tapping "Challenge" shows a modal: "Tap your coin to initiate" — the user must perform a **real, CMAC-validated NFC tap** to confirm they own a registered coin
- [ ] A challenger may **not** challenge themselves (their own coin_name is excluded from the target list)
- [ ] After validation, user selects opponent coin from leaderboard (excluding their own)
- [ ] User selects battle size: **10, 25, 50, or 100 flips**
- [ ] Challenge is persisted to the database with status `pending`
- [ ] Challenger and challenged coin owners see an active challenge banner on the results page

#### Flip Collection
- [ ] Only **real, CMAC-validated flips** (not test flips) count toward challenge progress
- [ ] The system collects the next N flips **after challenge creation timestamp** from each coin
- [ ] Flips before the challenge creation timestamp do not count
- [ ] Progress is visible: e.g. "Challenger: 7/25 flips | Rival: 12/25 flips"

#### Winner Determination
- [ ] When both coins reach N flips, the challenge status changes to `complete`
- [ ] Winner is the coin with **higher Shannon entropy** over their N challenge flips
- [ ] In the event of a tie (entropy equal to 4 decimal places), the result is a **draw**
- [ ] Winner, loser, both entropy scores, and flip counts are recorded in the database
- [ ] The result is shown on the leaderboard and on both coins' result pages

#### Data & Integrity
- [ ] Challenges are stored in a `flip_off_challenges` table (see §13.6)
- [ ] Each challenge references challenger `coin_name` and challenged `coin_name`
- [ ] A coin may only have **one active challenge at a time** (per coin_name)
- [ ] Expired challenges (no activity for 30 days) are auto-marked `expired`

---

### 13.4 User Flow

```
1. User visits leaderboard page
2. User clicks "Challenge" on a rival coin row
3. Modal: "Tap your coin to start the challenge"
4. User taps their NFC coin → CMAC validated → challenger coin_name confirmed
5. Modal: "Select battle size: 10 / 25 / 50 / 100 flips"
6. User selects size → challenge record created (status=pending)
7. Both coins accumulate real flips post-creation
8. Progress bar updates on each page load
9. When both reach N → winner declared by entropy comparison
10. Result displayed on leaderboard and per-coin result pages
```

---

### 13.5 Shannon Entropy Scoring

- Entropy is calculated over the N challenge flips for each coin using the existing `calculate_entropy()` function in `crypto_primitives.py`
- Sequence: challenger's N flip outcomes encoded as bits (HEADS=1, TAILS=0)
- Higher entropy (max 1.0 bits/bit for a perfectly random coin) = winner
- Both scores displayed on the result card with 4 decimal places

---

### 13.6 Database Schema (new table)

```sql
CREATE TABLE flip_off_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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
    completed_at DATETIME
);
```

---

### 13.7 UI Changes

| Location | Change |
|---|---|
| Leaderboard table | Add "Challenge" button per row (disabled if coin has active challenge) |
| Result page (coin flip outcome) | Show active challenge banner + progress if coin is in a challenge |
| Result page | Show challenge result card when `status=complete` |
| Leaderboard | Show trophy icon next to winner of most recent completed challenge |

---

### 13.8 Technical Notes

- Challenge initiation reuses the existing NFC tap → CMAC validation flow (no new hardware path)
- After CMAC validation on the index route, check if the validated coin has an active challenge; if so, count the flip toward it
- Flip collection is passive — no separate endpoint needed; integrate into the existing `update_state()` + challenge progress update in one transaction
- Entropy calculation reuses `calculate_entropy()` from `crypto_primitives.py`
- New service method: `FlipOffService` (or methods on `SqliteGameStateManager`) to manage challenge lifecycle

---

### 13.9 Out of Scope (MVP)

- Push notifications when a challenge completes
- Multi-coin tournaments (bracket play)
- Wagering or scoring system
- Challenge invitations via QR code or link

---

### 13.10 Definition of Done

- [ ] `flip_off_challenges` table created (migration safe)
- [ ] Challenge creation flow: validated tap → coin selection → size selection → DB record
- [ ] Flip counting passively increments challenge progress on each validated flip
- [ ] Entropy comparison triggers on both reaching N flips; winner recorded
- [ ] Leaderboard shows Challenge button; disabled for coins with active challenge
- [ ] Result page shows active challenge progress banner
- [ ] Result page shows completed challenge result card
- [ ] Unit tests: challenge creation, flip counting, entropy winner logic, tie handling
- [ ] Code review approved by Morpheus
- [ ] QA sign-off by Trin

---

**Document Status**: Active
**Last Updated**: 2026-03-26
**Next Steps**: Smith review → Morpheus architecture → implementation

