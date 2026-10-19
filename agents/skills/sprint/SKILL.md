---
name: sprint
description: Sprint planning and execution container loop. Orchestrates SDLC verification, breaks stories into an ordered sequence of typed Work Loops in task.md, executes them, and manages sprint close.
triggers: ["*plan sprint", "/sprint", "*sprint close", "*sprint retro", "*sprint launch"]
requires: ["bob-protocol", "bloop", "chat", "make", "prep-clear", "epic", "story", "impl", "fix", "refactor", "spike", "uat", "deploy"]
---

Sprint planning and execution container loop: orchestrates the sprint cadence from SDLC gate through work-loop execution to launch.

TLDR:
    Literature: Ken Schwaber & Jeff Sutherland (*The Scrum Guide*).
    Hierarchy: Third Planning Loop, consuming deliverables from Epic (`*plan epic`) and Story (`*plan story`) loops.
    Composition: Compiles stories into an ordered pipeline of typed Work Loops (*impl, *fix, *refactor, *spike, *uat, *deploy) in `task.md`.
    Between work loops: Runs *prep-clear if context > 60% before /clear.
    Sprint Close: Tank SDLC check → Oracle groom & report → Smith acceptance → Team retro → Cypher launch.

# Sprint — Planning & Cadence Container Loop

## Overview

In the Bob Protocol SDLC hierarchy, the `sprint` loop serves as the **Execution Container**. It takes ready stories from the `story` planning loop, verifies SDLC governance ([docs/SDLC.md](file:///home/drusifer/Projects/bob_protocol/docs/SDLC.md)), structures `task.md` as an ordered sequence of typed **Work Loops**, manages context budgeting (`prep-clear`), and coordinates sprint close.

---

## Sprint Stages

```
Stage 0: SDLC Gate         → docs/SDLC.md verified by Tank (Blocker)
Stage 1: Sprint Planning   → Mouse structures task.md as typed Work Loops; Morpheus reviews
Stage 2: Work-Loop Execution → Sequential execution of Work Loops (*impl, *fix, *refactor, *spike, *uat, *deploy)
Stage 3: Sprint Close      → Tank SDLC check → Oracle groom → Smith UAT → Retro → Cypher launch
```


---

## Stage 0: SDLC Gate (blocker)

Before any story is written, check that `docs/SDLC.md` exists. It is Tank's definition of how
this project is built, tested, changed and released (see the `build-env` skill) — the source of
truth for change management. Every later step assumes it, and where this skill's generic steps
differ from what the SDLC says for this repository, follow the SDLC.

- **Present** → proceed to Stage 1.
- **Missing** → stop. Do not plan. Ask Tank to create it and wait for Tank's confirmation:

```bash
bobp chat "Sprint blocked: docs/SDLC.md is missing. @Tank *devops sdlc" --persona <Name> --cmd blocked --to Tank
```

This only checks that the document exists. Whether the project still matches it is checked at
close (Step 6a).

### Source control follows the SDLC

How a sprint uses git is defined by the project's `docs/SDLC.md` (change-management section),
not by this skill. Read it before the first change and apply it at three points:

- **Start** — if the SDLC calls for a sprint branch, create it before Cypher writes stories.
- **During** — commit as the SDLC says (who, how often, message convention), normally as each
  phase passes Morpheus's review. Mouse posts a phase marker to CHAT.md at the start of each
  phase: `bobp chat "<phase description>" --persona Mouse --cmd "phase <N>"`.
- **Close** — after Cypher's launch, integrate, version and tag as the SDLC says. Push only if
  the SDLC explicitly gives agents that right.

If the SDLC is silent on source control, do not commit; ask the user.

---

## Stage 1: Sprint Planning

### Step 1 — Cypher: Stories + Acceptance Criteria
```
Cypher *pm plan sprint
```
- Write the stories from `agents/templates/_template_USER_STORIES.md` (delete its rubric block)
- Define user stories with clear acceptance criteria
- Scope the sprint: what's in, what's out
- Self-check against the template's STORIES rubric before handing off
- Hand off to Smith for user review gate

**Handoff:**
```bash
bobp chat "Stories ready for user review. @Smith *user review <sprint>" --persona Cypher --cmd "pm handoff" --to Smith
```

### Gate 1 — Smith: User Story Review
```
Smith *user review <stories>
```
- Evaluate stories against HCI principles and user value
- Apply the STORIES rubric and report its verdict line (`rubric STORIES: OUT=A TEST=S ...`); any Weak rejects, naming the criterion and the fix — see `agents/templates/ARTIFACTS.md`
- Must post explicit approve or reject

```bash
# Approve → proceed to Morpheus
bobp chat "*user approve. Stories approved. @Morpheus *lead arch sprint" --persona Smith --cmd "user approve" --to Morpheus

# Reject → back to Cypher
bobp chat "*user reject REASON: <reason> | FIX: <fix>. @Cypher revise stories." --persona Smith --cmd "user reject" --to Cypher
```

### Step 2 — Morpheus: Architecture
```
Morpheus *lead arch sprint
```
- Write the architecture from `agents/templates/_template_ARCH.md` (delete its rubric block)
- Self-check against the template's ARCH rubric before handing off
- **Build-environment check:** read `docs/SDLC.md`. If the design adds a language, a new
  third-party dependency mechanism, a different package manager, a runtime version change, or a
  new standard make target, say so explicitly in the handoff — Mouse schedules it as a Tank
  Phase 0. Adding an ordinary dependency through the process the SDLC already describes is not a
  mechanism change.
- Record decisions via `@Oracle *ora record decision`
- Hand off to Smith for architecture review gate

**Handoff:**
```bash
bobp chat "Architecture complete. @Smith *user feedback <arch summary>" --persona Morpheus --cmd "lead handoff" --to Smith
```

### Gate 2 — Smith: Architecture Review
```
Smith *user feedback <arch>
```
- Evaluate architecture for UX impact (flag naming, output formats, breaking changes)
- Apply the ARCH rubric and report its verdict line (`rubric ARCH: BOUND=A FLOW=A FAIL=A USER=S DECS=A FEAS=A`); any Weak rejects, naming the criterion and the fix — see `agents/templates/ARTIFACTS.md`
- Must post explicit approve or reject

```bash
# Approve → proceed to Mouse
bobp chat "*user approve. Architecture approved. @Mouse *sm plan sprint" --persona Smith --cmd "user approve" --to Mouse

# Reject → back to Morpheus
bobp chat "*user reject REASON: <reason> | FIX: <fix>. @Morpheus revise arch." --persona Smith --cmd "user reject" --to Morpheus
```

### Step 3 — Mouse: Phase Breakdown
```
Mouse *sm plan sprint
```
- Write sprint tasks to root `task.md` using `agents/templates/_template_task.md` (delete rubric block)
- Break sprint into phases of **1-3 tasks each** (no larger — context overflow risk)
- If Morpheus flagged a build-environment change, make it **Phase 0**, assigned to Tank
  (`*devops bootstrap` or `*devops sdlc`), before any Neo phase — Neo cannot build on an
  environment that does not exist yet. Deploy tasks, by contrast, stay last.
- Always include the close-out task "Tank `*devops sdlc-check`"
- Self-check against the template's PLAN rubric before handing off
- Record phases in `agents/mouse/sprint_log.md`
- Hand off to Morpheus for plan review

**Handoff:**
```bash
bobp chat "Sprint planned. Phases ready for review. @Morpheus *lead review sprint plan" --persona Mouse --cmd "sm handoff" --to Morpheus
```

### Step 3a — Morpheus: Sprint Plan Review
```
Morpheus *lead review sprint plan
```
- Verify phase breakdown aligns with architecture decisions
- Apply the PLAN rubric and report its verdict line (`rubric PLAN: SIZE=A GATE=A VERIF=A ALIGN=A OWNER=A`); any Weak rejects, naming criterion and fix — see `agents/templates/ARTIFACTS.md`
- Approve or request adjustment to Mouse

**Handoff (approved):**
```bash
bobp chat "Sprint plan approved. Phase 1 ready. @Neo *swe impl phase-1" --persona Morpheus --cmd "lead handoff" --to Neo
```

---

## Stage 2: Phase Bloop

Repeat for each phase until all phases complete.

### Step 4 — Neo: Implementation
```
Neo *swe impl <phase N>
```
- TDD: write tests first, then implement
- Keep implementation scoped to this phase only

**Handoff:**
```bash
bobp chat "Phase N impl complete. @Trin *qa uat phase-N" --persona Neo --cmd "swe handoff" --to Trin
```

### Step 5 — Trin: UAT
```
Trin *qa uat <phase N>
```
- Run tests, verify all acceptance criteria for this phase using `agents/templates/_template_UAT_PLAN.md` (self-checked against the **UAT rubric**)
- Consult Oracle for expected behavior before asserting

**Handoff (pass):**
```bash
bobp chat "UAT phase N passed. @Morpheus *lead review phase-N" --persona Trin --cmd "qa handoff" --to Morpheus
```

**Handoff (fail):**
```bash
bobp chat "UAT phase N FAILED. @Neo *swe fix <issues>" --persona Trin --cmd "qa reject" --to Neo
```

### Step 6 — Morpheus: Code Review
```
Morpheus *lead review <phase N>
```
- Review for architectural correctness, code quality, maintainability

**Handoff (pass — more phases):**
```bash
bobp chat "Phase N review passed. @Neo *swe impl phase-N+1" --persona Morpheus --cmd "lead handoff" --to Neo
```

**Handoff (pass — last phase):**
```bash
bobp chat "All phases reviewed. @Tank *devops sdlc-check" --persona Morpheus --cmd "lead handoff" --to Tank
```

**Handoff (fail):**
```bash
bobp chat "Phase N review FAILED. Issues: <issues>. @Neo *swe fix <issues>" --persona Morpheus --cmd "lead reject" --to Neo
```

**Fix loop rule:** If Neo fails to fix after one retry → Anti-Loop Protocol applies (Oracle consult + user escalation required).

---

## Stage 3: Sprint Close

### Step 6a — Tank: SDLC Conformance Check
```
Tank *devops sdlc-check
```
- Rebuild from clean and confirm the project still matches `docs/SDLC.md` (full checklist in the
  `build-env` skill): manifest matches imports, documented targets exist, no installs or
  instructions that bypass `make`
- Conforms → update the "Last verified" line. Legitimate mechanism change → update the SDLC
- Runs before Oracle so any SDLC correction is included in the documentation pass

**Handoff (conforms):**
```bash
bobp chat "SDLC check passed. @Oracle *ora groom" --persona Tank --cmd "devops handoff" --to Oracle
```

**Handoff (regression):**
```bash
bobp chat "SDLC check FAILED: <drift>. @Neo *swe fix <issue>" --persona Tank --cmd "devops reject" --to Neo
```
→ fix → Tank re-checks. The sprint does not close on a failed check.

### Step 7 — Oracle: Groom
```
Oracle *ora groom
```
- Update docs, record decisions, archive sprint artifacts
- If `docs/SDLC.md` changed this sprint, apply the SDLC rubric and report its verdict line; any Weak goes back to Tank before the handoff
- If any research spikes or findings were added, apply the FINDING rubric (`agents/templates/_template_finding.md`) and report its verdict line
- If any decision records were added, apply the DECISION rubric (`agents/templates/_template_DECISION.md`) and report its verdict line
- Write new lessons from the lesson template, self-checked against the LESSON rubric
- Ensure CHAT.md is archived if over 50-100 messages (rolling `*ora archive`)
- **Per-phase report:** `bobp chat-report` splits the archived diagram into one section per phase when Mouse has posted `*phase <N>*` markers (sprint summary first, then each phase's description and its own diagram). Run it after Cypher's launch if the SDLC says so, so the report covers the whole sprint.
- **Sprint-close chat report:** write a short summary of the sprint's CHAT.md conversation, then run
  `bobp chat-report --moniker <SPRINT_MONIKER> --summary "<summary>"` (`*ora report <SPRINT_MONIKER>`).
  This archives CHAT.md + CHAT.diagram.md to `agents/chat_archive/CHAT_<SPRINT_MONIKER>.md`/`.diagram.md`
  and resets CHAT.md for the next sprint — all file I/O is handled by the command; Oracle supplies only
  the summary text. Run `bobp chat-report --combine` afterward if a consolidated `CHAT_FULL.md` is needed.

**Handoff:**
```bash
bobp chat "Docs groomed. @Smith *user test <sprint>" --persona Oracle --cmd "ora handoff" --to Smith
```

### Step 8 — Smith: End-to-End User Testing
```
Smith *user test <sprint>
Smith *user feedback
```
- Test all delivered features from the user's perspective against the sprint UAT plan (`docs/sprints/UAT_PLAN_SPRINT<N>.md`)
- Apply the UAT rubric (`agents/templates/_template_UAT_PLAN.md`) and report its verdict line (`rubric UAT: COVER=A STEPS=A FAIL=A DATA=A EVID=A`)
- Apply the LESSON rubric to each lesson Oracle added this sprint and report a verdict line per lesson; any Weak goes back to Oracle
- Apply HCI heuristics — flag rough edges, inconsistencies, confusing interfaces

**Handoff (pass):**
```bash
bobp chat "User testing passed. @all *sprint retro" --persona Smith --cmd "user approve" --to all
```

**Handoff (bug found):**
```bash
bobp chat "*user bug CMD: <cmd> | EXPECTED: <x> | ACTUAL: <y> | UX ISSUE: <z>. @Trin triage." --persona Smith --cmd "user bug" --to Trin
```
→ Trin triages → fix loop → re-test before retro

### Step 9 — All Personas: Sprint Retrospective
```
*sprint retro
```
Each persona posts their domain retrospective to CHAT.md:

| Persona | Retrospective focus |
|---------|-------------------|
| Neo | Code quality, tech debt, implementation friction |
| Trin | Test coverage, regressions caught, test suite health |
| Morpheus | Architecture decisions made, anything to revisit |
| Oracle | Documentation gaps, decisions not recorded |
| Mouse | Phase sizing, blockers, velocity |
| Cypher | Story quality, acceptance criteria accuracy |
| Smith | UX issues, HCI gaps, user feedback themes |

Output feeds Cypher's backlog before launch.

```bash
# Each persona posts:
bobp chat "<persona> retro: <findings>. Backlog items: <items>" --persona <Name> --cmd retro --to Cypher
```

### Step 10 — Cypher: Launch
```
Cypher *pm launch <sprint>
```
- Announce release
- Add retro feedback to backlog
- Update changelog
- Close sprint

**Handoff:**
```bash
bobp chat "*pm launch <sprint>. Sprint complete." --persona Cypher --cmd "pm launch" --to all
```

**Sprint is complete** when Cypher posts `*pm launch`.

---

## Quick Reference

| Step | Persona | Command | Gate |
|------|---------|---------|------|
| 0 | (starter) | check `docs/SDLC.md` exists | Missing → `@Tank *devops sdlc`, blocked until written |
| 1 | Cypher | `*pm plan sprint` | → Smith `*user review` |
| 1a | Smith | `*user approve` / `*user reject` | Must approve to proceed |
| 2 | Morpheus | `*lead arch sprint` | → Smith `*user feedback` |
| 2a | Smith | `*user approve` / `*user reject` | Must approve to proceed |
| 3 | Mouse | `*sm plan sprint` | → Morpheus `*lead review sprint plan` |
| 3a | Morpheus | `*lead review sprint plan` | Approve to start phase Bloop |
| 4 | Neo | `*swe impl <phase N>` | → Trin UAT |
| 5 | Trin | `*qa uat <phase N>` | → Morpheus review |
| 6 | Morpheus | `*lead review <phase N>` | Pass → next phase or Tank |
| 6a | Tank | `*devops sdlc-check` | Pass → Oracle; regression → fix Bloop |
| 7 | Oracle | `*ora groom` | → Smith testing |
| 8 | Smith | `*user test` + `*user feedback` | Pass → retro; bug → fix Bloop |
| 9 | All | `*sprint retro` | Feed backlog to Cypher |
| 10 | Cypher | `*pm launch <sprint>` | Sprint complete |

---

## Rules

- **Short phases**: 1-3 tasks each. Large phases cause context overflow.
- **No skipping gates**: Smith's gates after steps 1 and 2 are mandatory. Never auto-proceed.
- **SDLC bookends**: no planning without `docs/SDLC.md` (Stage 0); no close without Tank's `*devops sdlc-check` (Step 6a). Only Tank edits the SDLC.
- **Fix Bloop scope**: Fix Bloop targets the failing phase only — never restart the full sprint.
- **State saves**: Every persona saves state before every handoff (see bob-protocol State Management).
- **Chat first**: Post the handoff `bobp chat` call BEFORE switching. The next persona reads CHAT.md on entry.
- **Retro is required**: Step 9 is not optional. Retro output is the input to the next sprint's backlog.

---

## Loop Effectiveness Rubric (`LOOP_SPRINT`)

Reviewed by Morpheus (at Step 3a Plan Review) or Smith/Oracle (at Sprint Close) or during `*judge sprint`.  
Verdict line in `agents/CHAT.md`: `rubric LOOP_SPRINT: SDLC=L DECOMP=L GATES=L CADENCE=L RETRO=L`

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `SDLC` | **SDLC Governance** | Proceeded without `docs/SDLC.md`; ignored project build rules, linters, or git workflow conventions; skipped close audit. | Stage 0 SDLC gate verified before planning; drift check executed at sprint close by Tank. | 100% adherence to documented SDLC tooling and quality gates; proactive updates proposed to SDLC if tooling evolved. |
| `DECOMP` | **Work-Loop Decomposition** | Task board contains vague, unstructured notes or giant multi-day lumps; tasks do not specify work-loop type (`*impl`, `*fix`, etc.). | Mouse structured `task.md` into phased tasks, each explicitly mapped to a typed Work Loop with clear dependencies. | Bounded phases (1-3 tasks each); typed loops assigned to specialist personas; clear acceptance references; passes PLAN rubric. |
| `GATES` | **Gate & Rubric Enforcement** | Gates rubber-stamped without rubric verdicts; Weak findings ignored; handoffs proceeded despite unapproved gates. | Smith and Morpheus posted explicit rubric verdict lines (`rubric STORIES:...`); rejections required fixes before approval. | Thorough, formative critique on every gate; concrete tells identified; clean progression from rejection to revision to approval. |
| `CADENCE` | **Cadence & Context Budget** | Personas hopped erratically across tasks; context bloated past 70-80% without checkpoints; unlogged handoffs. | Sequential execution of task board; state files updated; `*prep-clear` run before clearing when context exceeded 60%. | Smooth, rhythmic handoffs in CHAT.md; zero lost context across clear boundaries; anti-loop guard protected against thrashing. |
| `RETRO` | **Knowledge & Retro Harvest** | Sprint ended without retro; lessons lost; CHAT.md ungroomed; changelog unmaintained. | Tank verified SDLC; Oracle groomed docs and archived chat; team held retrospective feeding backlog; Cypher launched. | Rich engineering lessons logged in `docs/LESSONS.md`; meaningful retrospective insights; comprehensive release notes published. |
