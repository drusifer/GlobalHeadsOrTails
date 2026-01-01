# Product Roadmap
## NTAG424 SDM Provisioner TUI

**Last Updated**: 2025-11-28  
**Owner**: Morpheus (Tech Lead)  
**Purpose**: High-level roadmap for sprint planning

---

## Current Sprint: Service Layer Extraction (40% Complete)

**Sprint Goal**: Eliminate code duplication between CLI and TUI by extracting business logic into reusable Services.

**Status**: In Progress
- ✅ TagDiagnosticsService implemented with tests
- ⚠️ TUI integration pending (TagStatusScreen, ReadTagScreen)
- ❌ TagMaintenanceService not started

**Blockers**:
1. Neo status unclear (stopped per state file)
2. TUI integration needs completion
3. TagMaintenanceService design needed

---

## Sprint 2: Complete Service Layer & TUI Integration

**Sprint Goal**: Complete service layer extraction and TUI integration. All TUI screens use services.

### User Stories

**US-1.3: Complete TUI Integration** (Priority: High)
- Refactor TagStatusScreen to use TagDiagnosticsService
- Refactor ReadTagScreen to use TagDiagnosticsService
- Remove deprecated TagStatusCommand and ReadTagCommand
- **Acceptance**: All TUI screens use services, no command pattern

**US-2: Tag Maintenance Service** (Priority: High)
- Design TagMaintenanceService interface (Morpheus)
- Implement TagMaintenanceService (Neo)
- Create ResetTagScreen (Neo)
- Wire ResetTagScreen to service
- **Acceptance**: Factory reset works via TUI

**US-3: BaseService Pattern** (Priority: Medium)
- Design BaseService base class (Morpheus)
- Refactor existing services to inherit from BaseService
- **Acceptance**: All services follow BaseService pattern

**US-4: Error Recovery & Diagnostics** (Priority: Medium)
- Add detailed error diagnostics to services
- Implement error recovery strategies
- Add recovery UI to TUI screens
- **Acceptance**: Users see clear error messages with recovery options

### Definition of Done
- All services have unit tests (>80% coverage)
- All TUI screens use services (no command pattern)
- All tests pass (pytest green)
- Code review approved
- QA verification complete

**Estimated Duration**: 1-2 weeks

---

## Sprint 3: Key Management & Security Enhancements

**Sprint Goal**: Implement secure key management per PRD Section 4.4.

### User Stories

**US-5: Key Encryption** (Priority: High - PRD Requirement)
- Implement encryption at rest for CSV key storage
- Add key encryption/decryption utilities
- Update CsvKeyManager to use encryption
- **Acceptance**: Keys stored encrypted, no plaintext keys in CSV

**US-6: Key Recovery** (Priority: Medium - PRD Feedback)
- Add `probe_keys()` method to TagDiagnosticsService
- Implement key recovery UI
- Support multiple key candidate attempts
- **Acceptance**: Users can recover keys for provisioned tags

**US-7: Key Management UI** (Priority: Low)
- Add key management screen to TUI
- Display key status and metadata
- Support key backup/restore
- **Acceptance**: Users can manage keys via TUI

### Definition of Done
- Key encryption implemented and tested
- Key recovery functional
- All security requirements met (PRD Section 5.3)
- 100% crypto test coverage maintained

**Estimated Duration**: 1-2 weeks

---

## Sprint 4: UX Enhancements & Polish

**Sprint Goal**: Improve user experience and meet PRD usability requirements.

### User Stories

**US-8: Tag Type Detection** (Priority: Medium - PRD Feedback)
- Detect tag manufacturer (NXP vs. Seritag)
- Display hardware version
- Show SDM compatibility status
- Recommend provisioning path based on tag type
- **Acceptance**: Users know their tag type and compatibility

**US-9: Enhanced Error Messages** (Priority: Medium - PRD Feedback)
- Display error codes (e.g., 0x91AE)
- Suggest possible causes
- Provide recovery steps
- Log detailed error context
- **Acceptance**: Users understand errors and know how to fix them

**US-10: Progress Indicators** (Priority: Low)
- Enhanced progress feedback during long operations
- Estimated time remaining
- Step-by-step progress display
- **Acceptance**: Users see clear progress during provisioning

**US-11: Keyboard Shortcuts** (Priority: Low - PRD Section 7.3)
- Add keyboard shortcuts for power users
- Navigation shortcuts
- Action shortcuts
- **Acceptance**: Power users can navigate without mouse

### Definition of Done
- All UX enhancements implemented
- User testing feedback incorporated
- Documentation updated

**Estimated Duration**: 1 week

---

## Sprint 5: Performance & Reliability

**Sprint Goal**: Meet PRD performance and reliability targets.

### User Stories

**US-12: Performance Optimization** (Priority: Medium)
- Optimize provisioning workflow (< 2 minutes target)
- Optimize diagnostics (< 5 seconds target)
- Profile and optimize bottlenecks
- **Acceptance**: All operations meet PRD performance targets

**US-13: Reliability Improvements** (Priority: High)
- Implement retry mechanisms (3 retries, 1-second delay)
- Add partial state recovery
- Improve error handling
- **Acceptance**: 99%+ success rate for provisioning

**US-14: Tag Removal Handling** (Priority: Medium)
- Graceful handling of tag removal during operations
- Clear error messages
- Recovery options
- **Acceptance**: Users can recover from tag removal

### Definition of Done
- Performance targets met (PRD Section 7.1)
- Reliability targets met (PRD Section 7.2)
- All error scenarios handled gracefully

**Estimated Duration**: 1-2 weeks

---

## Future Sprints (Post-MVP)

### Sprint 6+: Advanced Features
- Batch provisioning UI (currently CLI only)
- Advanced key management features
- Tag type auto-detection improvements
- Enhanced diagnostics and analytics

### Out of Scope (Per PRD Section 8)
- Web API interface
- Mobile app
- Cloud key management integration
- Tag emulation/simulation mode

---

## Dependencies & Blockers

### Current Blockers
1. **Neo Status**: Currently stopped (per state file) - needs resolution
2. **TUI Integration**: TagStatusScreen/ReadTagScreen still use command pattern
3. **TagMaintenanceService Design**: Waiting on Morpheus design

### Cross-Sprint Dependencies
- Sprint 2 → Sprint 3: Service layer must be complete before key management enhancements
- Sprint 3 → Sprint 4: Security must be solid before UX polish
- Sprint 4 → Sprint 5: UX must be stable before performance optimization

---

## Success Metrics (Per PRD Section 11)

### MVP Success Criteria
- [ ] Users can provision tags via TUI
- [ ] Users can check tag status
- [ ] Users can reset tags
- [ ] All operations have >80% test coverage
- [ ] Zero hardcoded secrets
- [ ] Documentation complete

### Full Success Criteria
- [ ] < 2 minute provisioning time
- [ ] < 1% error rate
- [ ] 100% crypto test coverage
- [ ] Users can operate without NXP docs
- [ ] Production-ready for game coin manufacturing

---

## Risk Mitigation

### High-Risk Items
1. **Key Encryption**: Complex requirement, may need external library
   - **Mitigation**: Research encryption libraries early, prototype in Sprint 2
2. **Performance Targets**: May be hardware-dependent
   - **Mitigation**: Profile early, optimize incrementally
3. **Neo Availability**: Current status unclear
   - **Mitigation**: Resolve status, reassign if needed

---

**Roadmap Status**: Draft - Awaiting Mouse sprint planning  
**Next Action**: Mouse to break down Sprint 2 into tasks

