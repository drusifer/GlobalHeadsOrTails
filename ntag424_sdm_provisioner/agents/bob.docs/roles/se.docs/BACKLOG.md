# Product Backlog - SE (The Lead)

**Last Updated:** 2025-11-21

This file tracks user stories, epics, and features for the NTAG424 SDM Provisioner project.

---

## Active Sprint

### Current Focus
- Initial team onboarding and architectural assessment
- Review existing codebase architecture
- Identify technical debt and refactoring opportunities

---

## Epics

### Epic 1: Production-Ready Provisioning System ✅
**Status:** COMPLETED  
**Description:** Core provisioning functionality with type-safe commands, EV2 authentication, and key management.

**User Stories:**
- [x] As a developer, I can provision NTAG424 DNA tags with unique keys
- [x] As a developer, I have type-safe command execution preventing authentication errors
- [x] As a developer, I can manage keys with two-phase commit for safety
- [x] As a developer, I can reset tags to factory defaults

---

## Backlog (Prioritized)

### High Priority

**Story:** SDM File Settings Configuration  
**Status:** NEEDS_INVESTIGATION  
**Description:** As a developer, I want to configure SDM file settings without LENGTH_ERROR (917E)  
**Acceptance Criteria:**
- ChangeFileSettings command completes successfully
- SDM placeholders are replaced with actual dynamic values
- URL properly configured for NFC tap responses

**Technical Notes:**
- Current issue: ChangeFileSettings returns 917E (LENGTH_ERROR)
- Documented in README as "Known issue, under investigation"
- Doesn't block provisioning but prevents full SDM functionality

---

**Story:** Enhanced Type Coverage  
**Status:** PROPOSED  
**Description:** As a developer, I want comprehensive type hints across the entire codebase  
**Acceptance Criteria:**
- All public APIs have complete type annotations
- mypy passes with strict settings
- Type stubs for external dependencies where needed

**Technical Notes:**
- Neo mentioned type hints present but could be more comprehensive
- Would improve IDE support and catch errors at development time

---

### Medium Priority

**Story:** Improved Error Handling & Recovery  
**Status:** PROPOSED  
**Description:** As a developer, I want clear error messages and recovery strategies for common failures  
**Acceptance Criteria:**
- Authentication failures provide actionable guidance
- Rate limiting detected and communicated clearly
- Integrity errors traced to specific cause

---

**Story:** Performance Optimization  
**Status:** PROPOSED  
**Description:** As a user, I want faster tag provisioning for batch operations  
**Acceptance Criteria:**
- Provisioning time measured and benchmarked
- Bottlenecks identified and optimized
- Batch processing support for multiple tags

---

### Low Priority / Future Enhancements

**Story:** WebUI for Tag Management  
**Status:** IDEA  
**Description:** As a non-developer, I want a web interface to provision and manage tags  

**Story:** Multi-Reader Support  
**Status:** IDEA  
**Description:** As a user, I want to use multiple NFC readers simultaneously for parallel provisioning

---

## Parking Lot / Research Needed

- Cross-platform compatibility verification (Linux/Mac)
- Alternative authentication methods beyond EV2
- Integration with cloud key management systems
- Tag lifecycle management and decommissioning workflows

---

## Definition of Done

A user story is considered DONE when:
1. ✅ Implementation complete and code reviewed
2. ✅ Unit tests pass with adequate coverage
3. ✅ Integration tests pass (hardware validation if applicable)
4. ✅ Documentation updated (README, docstrings, comments)
5. ✅ Oracle has recorded any architectural decisions
6. ✅ No regressions in existing functionality
