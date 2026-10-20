# Artifacts and Rubrics

What the agents are expected to produce, which of those have a template and a rubric, and how a
rubric is written and used. Maintained by Bob; reviewed whenever a persona, skill or template is
added.

## Why rubrics

A template tells an author what sections to fill in. It cannot tell a reviewer whether what was
written is any good. A rubric does that: a short set of criteria, each describing what weak,
acceptable and strong work looks like, so that a review is a judgement against something
written down rather than taste. Rubrics here guide a reviewer; nothing computes a score.

## Artifact inventory

| Artifact | Lives in | Author | Template | Rubric | Reviewed by, when |
|---|---|---|---|---|---|
| Sprint stories | `docs/sprints/USER_STORIES_SPRINT<N>.md` | Cypher | `_template_USER_STORIES.md` | **STORIES** | Smith, Gate 1 |
| SDLC | `docs/SDLC.md` | Tank | `_template_SDLC.md`, `.python.md`, `.javascript.md` | **SDLC** | Oracle, at groom when it changed |
| Lessons | `docs/LESSONS.md`, `agents/oracle/lessons.md` | Oracle | `_template_LESSON.md` | **LESSON** | Smith, at the close test |
| Architecture section / `docs/ARCH.md` | sprint stories document; `docs/ARCH.md` | Morpheus | `_template_ARCH.md` | **ARCH** | Smith, Gate 2 |
| Domain Model | `docs/DOMAIN.md`, `docs/domain/` | Cypher / Morpheus | `_template_DOMAIN.md` | **DOMAIN** | Smith / Morpheus, planning |
| Decisions | `docs/DECISIONS.md`, `docs/decisions/` | Oracle / Morpheus | `_template_DECISION.md` | **DECISION** | Oracle, at groom (or Smith, Gate 2) |
| Task board, sprint log | `task.md`, `agents/mouse/sprint_log.md` | Mouse | `_template_task.md` | **PLAN** | Morpheus, Step 3a (plan review) |
| Research finding | persona folder | any | `_template_finding.md` | **FINDING** | Oracle, at groom (or Morpheus, spike review) |
| Quality & UAT Strategy | `docs/TEST_STRATEGY.md` | Trin | `_template_TEST_STRATEGY.md` | **STRATEGY** | Morpheus / Smith, setup & groom |
| Acceptance Test Plan (UAT) | `docs/sprints/UAT_PLAN_SPRINT<N>.md` | Trin | `_template_UAT_PLAN.md` | **UAT** | Smith, at close (or Morpheus, review) |
| Work summary | `agents/<persona>/<Task>_Summary_<timestamp>.md` | any | none | none | — |
| Gate verdicts, UAT results, code reviews | `agents/CHAT.md` | Smith, Trin, Morpheus | none (chat) | none | — |
| Sprint chat report | `agents/chat_archive/CHAT_<SPRINT>*.md` | Oracle, via `bobp chat-report` | generated | none | — |
| Persona instructions | `agents/<persona>/SKILL.md`, `agents/skills/<name>/SKILL.md` | Bob | inline in Bob's instructions | none yet | — |
| Persona state | `agents/<persona>/state.md` | each persona | `_template_state.md` | none — see below | — |
| Chat messages | `agents/CHAT.md` | all | `_template_CHAT.md` | none — see below | — |
| TLDR blocks | top of `.py` / `.md` files | Oracle | `_template_tldr.md` | none — see below | — |

**Deliberately without a rubric:** persona state, chat messages and TLDR blocks. They go wrong in
mechanical ways — too long, stale, a missing section, the wrong format — and a check that can be
run (a length limit, a required-heading test) catches those better than a reviewer's judgement.

## Loop Effectiveness Rubrics

While artifact rubrics evaluate what was written into a static deliverable, **Loop Effectiveness Rubrics** evaluate the dynamic health, discipline, and execution quality of an autonomous multi-persona loop. They are evaluated by designated leads/advocates (Morpheus, Smith, Tank, Oracle) at loop completion or during `*judge <loop>` evaluations:

| Loop | Trigger | Rubric Code | Focus / Invariant | Evaluated by, when |
|---|---|---|---|---|
| Epic Planning | `*plan epic` | **LOOP_EPIC** | Problem framing, appetite, domain model, de-risking | Smith, Gate 1 & Gate 2 / `*judge epic` |
| Story Planning | `*plan story` | **LOOP_STORY** | Vertical slicing, INVEST criteria, ADRs, test strategy | Smith, Gate 1 & Gate 2 / `*judge story` |
| Sprint Container | `*plan sprint` | **LOOP_SPRINT** | SDLC gate, work-loop decomposition, gate enforcement, retro | Morpheus / Smith / `*judge sprint` |
| Conductor | `*bloop` | **LOOP_BLOOP** | Handoff ergonomics, state compliance, anti-loop, capture | Bob / Smith / `*judge bloop` |
| Feature Impl | `*impl` | **LOOP_IMPL** | Test-first TDD, verification rigour, modularity, regression | Morpheus, Step 3 / `*judge impl` |
| Defect Fix | `*fix` | **LOOP_FIX** | Reproduce & diagnose first, surgical fix, zero regression | Morpheus, Step 3 / `*judge fix` |
| Tech Debt | `*refactor` | **LOOP_REFACTOR** | Two-Hats rule, baseline green, 100% test parity | Morpheus, Step 5 / `*judge refactor` |
| Research Spike | `*spike` | **LOOP_SPIKE** | Timeboxing, disposable sandbox, empirical findings | Morpheus / Oracle / `*judge spike` |
| UAT | `*uat` | **LOOP_UAT** | Real-world execution, scenario coverage, UX audit | Smith / Cypher / `*judge uat` |
| Deploy | `*deploy` | **LOOP_DEPLOY** | Pipeline as code, pre-flight, smoke verification, rollback | Tank / Trin / `*judge deploy` |

## Rubric Quality Standards

Bob Protocol rubrics are held to formal assessment design standards grounded in Dr. Susan Brookhart's
framework (*How to Create and Use Rubrics for Formative Assessment and Grading*) and IEEE/ABET
engineering peer-review principles:

1. **Criterion Independence (Orthogonality):** Each criterion measures a single, distinct dimension
   of quality. A failure in one criterion must never automatically cause a failure in another.
2. **Observable Descriptors with Concrete Tells:** Descriptors paint a verifiable picture of what the
   reviewer observes in the text (e.g. "contains 'should' or 'properly'", "lacks timeout/retry
   specifications", "no single source of truth cited"), avoiding subjective adjectives ("good",
   "clean", "thorough").
3. **Formative Actionability (Weak = Actionable Fix):** Weak does not mean unpolished; it means the
   document fails its downstream reader (an implementer is blocked, a tester cannot write assertions,
   an on-call cannot trace failure). The Weak descriptor tells the author exactly what to fix.
4. **Parallel Developmental Progression:** Descriptors progress across columns evaluating the same
   underlying attribute: Weak (fails downstream reader) $\rightarrow$ Acceptable (enables safe execution)
   $\rightarrow$ Strong (exemplary, anticipates edge cases, provides copy-pasteable reference examples).
5. **Cognitive Ergonomics (The 4–6 Rule):** Exactly 4 to 6 criteria per rubric. More than that causes
   cognitive fatigue, leading reviewers to skim or rubber-stamp gates.

## Rubric format

A rubric is the last thing in a template, between two marker lines so it can be removed cleanly:

```markdown
<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — <NAME>

Reviewed by <who> at <step>. Verdict line: `rubric <NAME>: CODE=L CODE=L ...`

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `CODE` | The question this criterion asks | What you would see | What you would see | What you would see |
<!-- RUBRIC-END -->
```

Rules for writing one:

- **Four to six criteria.** More than that and reviewers stop reading them.
- **Each criterion asks one question** about the document's usefulness to its reader — not
  whether a section exists (the template already ensures that).
- **Describe each level by what a reviewer can observe**, with a concrete tell where possible
  ("an acceptance criterion contains 'should' or 'properly'"), not by adjectives.
- **Codes are short and unique within the rubric**, so a verdict fits on one line.
- **Weak means the document fails its reader on that point**, not that it could be nicer.

## Applying a rubric

1. **The author self-checks** before handing off, and fixes anything they would call Weak.
2. **An independent reviewer** — never the author — applies it at the step named in the rubric.
3. **The reviewer reports a verdict line** in their chat message, one level per criterion:

   ```
   rubric STORIES: OUT=S TEST=A SCOPE=A FAIL=W SIZE=A DESIGN=A
   ```

4. **Verdict rule:** every criterion Acceptable or better → pass. Any Weak → reject, naming the
   criterion and the fix. Strong is recognition, never a requirement.
5. **A rejection says why.** For each Weak, one sentence quoting or pointing at the offending
   text and one saying what would make it Acceptable. If that does not fit in the chat message
   (512 characters), put the detail in a file in the reviewer's folder and cite it.
6. **A criterion that does not apply** is reported as `CODE=n/a` with a reason; it does not count
   as Weak.

Disagreement between author and reviewer about a level goes to the user, not back and forth —
the usual two-attempt limit on fix loops applies.

## Adding a rubric to another template

1. Confirm the artifact has an independent reviewer and an existing step where review happens.
   If it has neither, a rubric will not be used — fix that first or do not add one.
2. Write the appendix in the format above. Draw criteria from how the artifact has actually
   failed its readers in the past, not from general principles.
3. Calibrate: apply it to at least three existing examples of differing quality. If everything
   passes, or two reviewers would plausibly disagree on a level, reword the criterion.
4. Name the rubric in the reviewer's and the author's instructions.
5. Add the row to the inventory above.

## Keeping rubrics out of finished documents

A rubric belongs to the template. Authors delete the block between the markers when they
instantiate a template. Oracle's groom checks that no file outside `agents/templates/` has a line
beginning `<!-- RUBRIC-START` (`grep -rn '^<!-- RUBRIC-START' --include='*.md' .`). Mentioning
the marker in prose is fine; carrying the block is not.
