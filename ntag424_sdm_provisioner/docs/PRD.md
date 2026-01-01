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

**Document Status**: Draft - Awaiting Team Review  
**Next Steps**: Team review and feedback collection

