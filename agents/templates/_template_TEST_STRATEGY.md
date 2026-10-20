<!--
High-level Quality & UAT Strategy template.
Owned by Trin (QA Guardian / Lead SDET) — see agents/trin/SKILL.md.
Instantiated as `docs/TEST_STRATEGY.md` (or `docs/UAT_STRATEGY.md`).
Delete this comment AND the review rubric at the end (everything from RUBRIC-START to
RUBRIC-END): the rubric belongs to the template, not to the document.
Morpheus and Smith review this using the STRATEGY rubric.
-->
# Quality & UAT Strategy: {Project Name}

*   **Lead SDET / QA Guardian**: Trin
*   **Status**: {Draft | Active | Under Revision}
*   **Last Updated**: {YYYY-MM-DD}
*   **Target Environments**: `{Local developer venv, CI pipeline, Staging container}`

---

## 1. Quality Vision & Testing Principles

{Describe the core testing philosophies governing this codebase. Focus on fast feedback, deterministic suites, and regression prevention.}

* **Shift-Left Quality:** Verification begins during story refinement and phase implementation, not as a post-sprint freeze.
* **Deterministic & Fast Feedback:** Unit tests must be fast, isolated, and flaky-free. Tests run through `bobp make test`.
* **Reality Over Mocks (MANDATORY):** Mocks only validate assumptions, not reality. Any code wrapping or parsing an external CLI, binary, or API must be executed against the *real* tool at least once under unprivileged/safe conditions to avoid mock-drift regressions.
* **Simplicity & Maintainability:** Prefer clean, well-factored code with clear test seams over complex mocking frameworks.

---

## 2. Testing Levels & The Quality Pyramid

| Level | Focus | Primary Owner | Execution Method | Target Proportion |
|---|---|---|---|---|
| **Unit Tests** | Function/class logic in isolation, pure domain rules, boundary edges | Neo (*swe) | `bobp make test-unit` | ~70% |
| **Integration Tests** | Adapter boundaries, persistence, multi-component interaction | Neo & Trin | `bobp make test-integration` | ~20% |
| **UAT / Scenarios** | End-to-end user journeys, real CLI/API workflows, acceptance criteria | Trin (*qa) & Smith (*user) | Scenario-based scripts / CLI runs | ~10% |

---

## 3. Segregation of Quality Responsibilities

| Role | Responsibilities | Does NOT Do |
|---|---|---|
| **Trin** (*qa*) | Owns `tests/`, test suite architecture, functional correctness, automated gates, regression prevention, bug reproduction. | Write application features or redefine user requirements. |
| **Smith** (*user*) | Evaluates usability, HCI heuristics, user mental model alignment, CLI help accuracy, error message clarity. | Evaluate internal code architecture or write test suites. |
| **Neo** (*swe*) | Practices TDD, writes unit tests alongside features, fixes reported bugs. | Pass code directly to review without Trin's UAT gate passing. |
| **Tank** (*devops*) | Wires quality gates into CI/CD pipelines, verifies environment parity and build tooling (`docs/SDLC.md`). | Define test assertion logic. |

---

## 4. Automated Quality Gates

Every code change must pass automated gates before proceeding to human/persona review.

| Gate | Target Command | Pass Condition | Failure Action |
|---|---|---|---|
| **Automated Tests** | `bobp make test` | 100% passing tests; exit code 0 | Blocks phase handoff; Neo fixes |
| **Code Style** | `bobp make lint-style` | Zero style violations | Auto-format or fix before commit |
| **Type Check** | `bobp make type-check` | Zero type errors | Static typing corrected by Neo |
| **Complexity** | `bobp make complexity` | Grade B or better on all functions | Refactor complex function |
| **Dead Code** | `bobp make dead-code` | No unreferenced dead code | Remove or document exceptions |

---

## 5. Test Environment & Fixture Management

* **Isolation:** Tests must never depend on state left by a previous test. All test files, databases, or mocks must be scoped per test or test module.
* **Scratch & Cleanup:** File operations must write to isolated temporary directories (`build/test_scratch/` or pytest `tmp_path`) and clean up upon completion.
* **Non-Destructive Execution:** Test scripts must never perform destructive actions on production or user home directories.

---

## 6. Defect Classification & Triage Protocol

### Severity Levels
* 🔴 **Blocker:** Prevents critical workflow, corrupts state, or causes fatal crash with zero workaround. *Action: Halts sprint phase; immediate fix.*
* 🟡 **Major:** Significant feature malfunction, but a viable temporary workaround exists. *Action: Must be fixed before sprint close.*
* 🟢 **Minor:** Cosmetic issue, slight output formatting defect, or minor UX friction. *Action: Logged as backlog task.*

### Triage Routing
* **Correctness Bug (Functional defect):** Filed to **Trin** $\rightarrow$ Trin creates minimal reproduction (`*qa repro`) $\rightarrow$ Assigned to **Neo** for fix.
* **Usability Defect (HCI / UX issue):** Filed by **Smith** (`*user bug`) $\rightarrow$ Triaged by **Trin** $\rightarrow$ Correctness assigned to Neo; UX verified by Smith.
* **Anti-Loop Guard:** If a bug fix fails twice, invoke Anti-Loop Protocol (Oracle consult + user escalation).

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — STRATEGY

Self-checked by Trin upon creation/update; reviewed by Morpheus and Smith during project setup or sprint groom.
Verdict line: `rubric STRATEGY: PYRAMID=_ REALITY=_ GATES=_ TRIAGE=_ ROLES=_` (W, A or S).
Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `PYRAMID` | Does it define test levels and distribution with clear boundaries? | Lacks clear test levels or advocates heavy, slow end-to-end tests for simple unit logic. | Distributes testing across unit, integration, and UAT levels with clear scopes for each. | Specifies concrete proportion targets, execution commands, and isolation rules for each level. |
| `REALITY` | Does it enforce real-binary testing over unvalidated mocks? | Allows external CLI wrappers, network tools, or binaries to be verified solely by hand-written mock strings. | Mandates that code interacting with external tools or binaries must execute against the real binary at least once. | Cites historical failure modes or concrete verification rules ensuring CLI flags and precision match real tools. |
| `GATES` | Are quality gates deterministic and tied to automated commands? | Gates are subjective ("ensure code is good") without automated targets or definite pass criteria. | Every gate specifies an exact command (e.g. `bobp make test`, `bobp make lint`) and a clear pass condition. | Maps gates directly to CI/CD pipeline triggers and specifies explicit failure recovery steps. |
| `TRIAGE` | Does it establish clear defect severity and triage routing? | Lacks severity definitions, leaves triage responsibilities ambiguous, or allows bugs to bypass tracking. | Defines severity classes (Blocker, Major, Minor) and specifies routing between Trin, Smith, and Neo. | Integrates anti-loop protocols, reproduction standards, and strict segregation between functional and UX defects. |
| `ROLES` | Are quality responsibilities clearly divided between roles? | Blurs duties (e.g. QA writing application code, or SWE verifying own acceptance criteria). | Clearly segregates Trin (correctness/gates), Smith (usability/HCI), and Neo (unit tests/TDD). | Specifies exact hand-off contracts, verification artifacts, and escalation boundaries across all team roles. |
<!-- RUBRIC-END -->
