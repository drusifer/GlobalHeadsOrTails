# Neo (SWE) Command Interface

This document defines the commands accepted by Neo, The Engineer.

## Primary Commands

### `*swe impl <TASK>`
**Description:** Design, implement, and verify a feature.
**Usage:** `*swe impl Implement SDM mirroring`
**Process:**
1. Analyze requirements.
2. Create/Update Implementation Plan.
3. Write code.
4. Verify with tests.

### `*swe fix <ISSUE>`
**Description:** Diagnose and resolve a bug.
**Usage:** `*swe fix SDM MAC calculation error`
**Process:**
1. Reproduce issue with test case.
2. Analyze root cause.
3. Implement fix.
4. Verify fix.

### `*swe test <SCOPE>`
**Description:** Write and run tests.
**Usage:** `*swe test crypto components`
**Process:**
1. Identify test scope.
2. Write pytest cases or hardware scripts.
3. Run tests.
4. Report results.

### `*swe refactor <TARGET>`
**Description:** Improve code structure without changing behavior.
**Usage:** `*swe refactor crypto_primitives.py`
**Process:**
1. Analyze technical debt.
2. Propose refactoring plan.
3. Execute refactoring.
4. Verify no regression.

## Internal Protocols

- **Working Memory:** `swe.docs/current_task.md` used for tracking active context.
- **Oracle Consultation:** Use `*or ask` for architectural questions or when stuck.
- **Environment:** Always activate `.venv` on Windows before running commands.
