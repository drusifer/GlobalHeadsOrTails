<!--
Sprint task board template. Owned by Mouse — see agents/mouse/SKILL.md and the sprint skill.
Instantiated as root `task.md` (the single source of truth for sprint execution).
Delete this comment AND the review rubric at the end (everything from RUBRIC-START to
RUBRIC-END): the rubric belongs to the template, not to the document.
Morpheus reviews this at Step 3a using the PLAN rubric.
-->
# Sprint {N} Task Board: {Short Title}

*   **Goal**: {Two sentences summarizing the primary sprint delivery}
*   **Tier**: {Tier 1 (Major) | Tier 2 (Minor/Fast-track)}
*   **Total Points**: {sum}
*   **Branch**: `sprint-{N}`
*   **Status**: Planning — awaiting Morpheus Step 3a Review

---

## Stage 0: SDLC Gate (Blocker)

- [ ] **Task 0.1:** Verify `docs/SDLC.md` exists and is current. (*Owner: Mouse | Verification: `test -f docs/SDLC.md`*)

---

## Sprint Execution Phases

<!-- Phase 0 is REQUIRED if Morpheus flagged a build-environment change (new language, package manager,
     dependency mechanism, or runtime change). Otherwise omit Phase 0. -->
### Phase 0: Build Environment (Conditional)
- [ ] **Task 0.2:** Bootstrap build environment & update `docs/SDLC.md`. (*Owner: Tank | Verification: `bobp make install && bobp make test`*)

### Phase 1: {First Vertical Slice / Component}
*Phase goal: {One sentence on what this phase delivers}*
- [ ] **Task 1.1:** {Write tests & implement core interface/logic}. (*Owner: Neo | Verification: `bobp make test`*)
- [ ] **Task 1.2:** {Run UAT & verify phase acceptance criteria}. (*Owner: Trin | Verification: `bobp make test && bobp make lint`*)
- [ ] **Task 1.3:** {Code review & architectural compliance check}. (*Owner: Morpheus | Verification: Code review inspection*)

### Phase 2: {Second Vertical Slice / Integration}
*Phase goal: {One sentence on what this phase delivers}*
- [ ] **Task 2.1:** {Implementation task}. (*Owner: Neo | Verification: `{exact verification command}`*)
- [ ] **Task 2.2:** {UAT verification}. (*Owner: Trin | Verification: `{exact test command}`*)
- [ ] **Task 2.3:** {Review & handoff}. (*Owner: Morpheus | Verification: Code review inspection*)

---

## Stage 3: Sprint Closeout

- [ ] **Task C.1:** SDLC conformance check. (*Owner: Tank | Verification: `bobp make distclean && bobp make install && bobp make test`*)
- [ ] **Task C.2:** Document grooming, lesson archiving, and chat report. (*Owner: Oracle | Verification: `bobp chat-report --moniker SPRINT_{N}`*)
- [ ] **Task C.3:** End-to-end user usability testing & lesson review. (*Owner: Smith | Verification: `bobp chat "*user approve"`*)
- [ ] **Task C.4:** Sprint retrospective & backlog grooming. (*Owner: All personas | Verification: Retros posted in CHAT.md*)
- [ ] **Task C.5:** Sprint launch & release announcement. (*Owner: Cypher | Verification: `bobp chat "*pm launch"`*)

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — PLAN

Self-checked by Mouse before handoff; reviewed by Morpheus at Step 3a (Sprint Plan Review).
Verdict line: `rubric PLAN: SIZE=_ GATE=_ VERIF=_ ALIGN=_ OWNER=_` (W, A or S).
Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `SIZE` | Are tasks partitioned into small, bounded phases? | A phase contains more than 3 tasks, or individual tasks are large enough to hide multi-day work without checkpoints. | Every phase contains 1–3 tasks; each task represents a focused, incremental increment. | Tasks are sequenced so each phase completes an independently verifiable vertical slice. |
| `GATE` | Are environmental bookends and conformance checks scheduled? | Omits Stage 0 SDLC verification, omits Tank's closeout `sdlc-check`, or schedules build-env changes mid-sprint instead of Phase 0. | Phase 0 is assigned to Tank if Morpheus flagged build-env changes; sprint ends with Tank's `*devops sdlc-check` task. | Explicitly verifies `docs/SDLC.md` exists before story breakdown and maps each phase to its SDLC change class. |
| `VERIF` | Does every task specify an observable verification command? | Verification is subjective ("ensure it works properly") or relies on unscripted manual inspection. | Each task specifies an exact command (e.g. `bobp make test`, `via query ...`) or concrete inspection step. | Specifies expected output strings, exit codes, or test file names directly in the task description. |
| `ALIGN` | Do tasks implement the approved stories and architecture without creep? | Tasks introduce libraries, patterns, or features not in approved stories/arch, or skips an approved story. | Every task traces back to an approved user story and architectural decision; scope matches stated tier. | Traces every task by ID directly to its parent user story and architectural component. |
| `OWNER` | Is every task assigned to the correct specialist persona? | Tasks are unassigned, assign multiple personas to one task, or violate persona boundaries (e.g. Neo writing PM stories). | Every task has exactly one assigned persona matching their domain (Neo for SWE, Trin for UAT, Tank for DevOps). | Hand-off prerequisites and expectations between roles (e.g. Neo $\rightarrow$ Trin) are stated on phase boundaries. |
<!-- RUBRIC-END -->
