<!--
Sprint Acceptance Test Plan (UAT) template.
Owned by Trin (QA Guardian / Lead SDET) — see agents/trin/SKILL.md and the sprint skill.
Instantiated as `docs/sprints/UAT_PLAN_SPRINT<N>.md` (or in `agents/trin/` during phase UAT).
Delete this comment AND the review rubric at the end (everything from RUBRIC-START to
RUBRIC-END): the rubric belongs to the template, not to the document.
Reviewed by Smith at sprint close (or Morpheus at phase review) using the UAT rubric.
-->
# Sprint {N} Acceptance Test Plan (UAT): {Feature / Sprint Title}

*   **Sprint**: `{SPRINT_N}`
*   **Author**: Trin (*qa)
*   **Date**: {YYYY-MM-DD}
*   **Branch**: `sprint-{N}`
*   **Status**: {Draft | In Progress | Passed | Failed}

---

## 1. Scope of Acceptance Testing

* **User Stories Covered:** `{STORY-KEY-01, STORY-KEY-02, ...}`
* **In-Scope Workflows:** {List primary user workflows to be verified}
* **Out-of-Scope:** {Any deferred items, underlying unit logic covered by automated tests, or future features}

---

## 2. Preconditions & Test Environment Setup

* **Environment:** `{e.g. Local Python 3.13 venv, clean Git working directory}`
* **Fixtures & Test Data:** `{Files, directories, or sample configs required}`
* **Environment Verification Command:**
  ```bash
  bobp make install && bobp make test
  ```

---

## 3. Scenario-Driven Acceptance Test Cases

Each test case maps directly to a user story acceptance criterion.

### Test Case `UAT-{STORY_ID}-01`: {Scenario Title}
* **User Story:** `{STORY-KEY-ID}`
* **User Persona:** `{Target User, e.g. Developer, Sysadmin, First-time user}`
* **Pre-conditions:** {System state or test file required before starting}
* **Execution Steps:**
  ```bash
  # Step 1: Run target command
  {exact command with flags}
  ```
* **Expected Result:**
  * Output: `{exact expected stdout/stderr text or pattern}`
  * Exit Code: `0`
  * State Mutation: `{Files created, modified, or confirmed untouched}`
* **Actual Execution Result:** `[ ] Pass | [ ] Fail | [ ] Blocked`
* **Evidence / Output Snippet:**
  ```text
  {actual command output snippet from test execution}
  ```

### Test Case `UAT-{STORY_ID}-02`: {Scenario Title}
* **User Story:** `{STORY-KEY-ID}`
* **User Persona:** `{Target User}`
* **Pre-conditions:** `{Pre-conditions}`
* **Execution Steps:**
  ```bash
  {command}
  ```
* **Expected Result:** `{Expected result and exit code}`
* **Actual Execution Result:** `[ ] Pass | [ ] Fail | [ ] Blocked`
* **Evidence:** `{Snippet}`

---

## 4. Negative & Error Handling Test Cases

Deliberately tests bad inputs, edge cases, and unexpected system states.

### Test Case `UAT-ERR-01`: {Invalid Input or Missing File}
* **Input / Trigger:** `{Malformed argument, missing file path, invalid flag combination}`
* **Execution Command:**
  ```bash
  {command with bad argument}
  ```
* **Expected System Behavior:**
  * Exit Code: `Non-zero (e.g. 1 or 2)`
  * Error Message: `{Clear, constructive error message telling user what is wrong and how to fix}`
  * Blast Radius: `{Zero corrupted files; clean exit}`
* **Actual Result:** `[ ] Pass | [ ] Fail`

---

## 5. Defect Summary & Gate Outcome

| Defect ID | Severity | Description | Assignee | Status |
|---|---|---|---|---|
| `{DEF-01}` | `{Blocker | Major | Minor}` | `{Short description}` | `{Neo / Smith}` | `{Resolved | Open}` |

* **Final UAT Verdict:** **{PASSED | FAILED}**
* **Summary:** {1-2 sentences summarizing execution results, passing counts, and handoff readiness}

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — UAT

Self-checked by Trin upon execution; reviewed by Smith at sprint close (or Morpheus at phase code review).
Verdict line: `rubric UAT: COVER=_ STEPS=_ FAIL=_ DATA=_ EVID=_` (W, A or S).
Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `COVER` | Does it cover all user story acceptance criteria without gaps? | Omits an acceptance criterion, or tests generic functionality unrelated to the sprint stories. | Every acceptance criterion from the sprint stories maps directly to at least one test scenario. | Scenarios are grouped by user story ID and explicitly cross-reference the story points and goals. |
| `STEPS` | Are execution steps and assertions copy-pasteable and deterministic? | Steps are vague narrative ("try using the tool") or lack expected exit codes and output strings. | Every scenario provides exact commands to run and explicit pass/fail conditions (exit code, output). | Commands include full argument strings and expected output regex/templates suitable for automated replay. |
| `FAIL` | Does it verify failure paths, bad input, and error messages? | Tests only the happy path; ignores invalid flags, missing files, or refused operations. | Includes explicit negative test scenarios verifying error exit codes and user-facing messages. | Asserts that failure leaves system state unmodified (no partial writes or corrupted files) and error suggests fix. |
| `DATA` | Are preconditions and test fixtures clearly defined? | Assumes prior test state without stating how to set it up, or writes destructively to global paths. | Specifies all required test fixtures, input files, environment variables, and setup commands. | Includes self-contained setup and teardown commands using isolated scratch directories (`tmp_path`). |
| `EVID` | Does it record verifiable execution evidence and pass/fail verdicts? | Claims "passed" without execution output, timestamps, or recording what actually occurred. | Every scenario records an explicit Pass/Fail verdict with an actual output snippet or exit code. | Includes complete session logs, timestamps, and commit hashes verifying the exact test run. |
<!-- RUBRIC-END -->
