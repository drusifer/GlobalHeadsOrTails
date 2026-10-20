<!--
Architecture Decision Record (ADR) template. Based on the Markdown Architectural Decision Records (MADR) standard.
Owned by Oracle (recording) and Morpheus (deciding) — see agents/oracle/SKILL.md and agents/morpheus/SKILL.md.
Instantiated in `docs/DECISIONS.md` or `docs/decisions/ADR-{NNNN}-{title}.md`.
Delete this comment AND the review rubric at the end (everything from RUBRIC-START to
RUBRIC-END): the rubric belongs to the template, not to the document.
Oracle reviews this at groom (or Smith at Gate 2) using the DECISION rubric.
-->
# ADR-{NNNN}: {Short Title of Decision}

*   **Status**: {Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-{YYYY}}
*   **Deciders**: {Morpheus, Cypher, Smith, etc.}
*   **Date**: {YYYY-MM-DD}
*   **Consulted**: {Oracle, Trin, Tank, etc.}
*   **Related Stories / Spikes**: `{STORY-ID or Spike Link}`

---

## 1. Context and Problem Statement

{What is the context and architectural challenge being addressed? What forces are pushing us in certain directions (functional, non-functional, business, UX constraints)?}

## 2. Decision Drivers

* {Driver 1: e.g., Must maintain sub-50ms query response time}
* {Driver 2: e.g., Must avoid introducing external C-extensions to preserve portability}
* {Driver 3: e.g., Must comply with docs/SDLC.md build and packaging constraints}

## 3. Considered Options

1. **Option 1:** `{Name and brief summary}`
2. **Option 2:** `{Name and brief summary}`
3. **Option 3 (Status Quo):** `{Rely on existing mechanism}`

## 4. Decision Outcome & Justification

* **Chosen Option:** **{Option X}**
* **Justification:** {Why this option was chosen over alternatives. Cite empirical data, benchmarks from research spikes, or specific driver alignment.}

### Consequences
* **Positive Impact (Gains):**
  * {Advantage 1: e.g. Zero-dependency CLI operation}
  * {Advantage 2: e.g. Immediate consistency for local cache}
* **Negative Impact (Costs / Accepted Debt):**
  * {Consequence 1: e.g. Slightly higher initial index time}
  * {Mitigation 1: e.g. Background async indexing scheduled in Phase 2}

## 5. Pros and Cons of Evaluated Options

### Option 1: {Option 1 Name}
* **Good, because** {positive argument}
* **Bad, because** {negative argument / violation of driver}

### Option 2: {Option 2 Name}
* **Good, because** {positive argument}
* **Bad, because** {negative argument / violation of driver}

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — DECISION

Self-checked by author upon recording; reviewed by Oracle at groom (or Smith at Gate 2).
Verdict line: `rubric DECISION: WHY=_ OPTS=_ CONS=_ STATE=_` (W, A or S).
Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `WHY` | Does it state the context, problem, and decision drivers? | Jumps straight to the solution without explaining the problem or names only vague drivers ("make it better"). | States architectural context, problem statement, and concrete decision drivers (forces, constraints, requirements). | Distinguishes between hard technical constraints (must-have) and soft preferences (nice-to-have). |
| `OPTS` | Were genuine alternative options evaluated? | Presents only the chosen option as if no alternatives existed ("only one way to do it"). | Details at least two viable options (including "do nothing" if applicable) with balanced pros and cons. | Explains why rejected options were discarded with concrete technical evidence or benchmark references. |
| `CONS` | Are trade-offs, consequences, and technical debt acknowledged? | Claims the choice has only benefits and zero drawbacks, costs, or risks. | Documents both positive outcomes (what is gained) and negative consequences (what is lost, technical debt accepted). | Provides specific mitigation strategies or scheduled review points for all negative consequences and risks. |
| `STATE` | Is the lifecycle state and relationship to other decisions clear? | Status is missing, ambiguous, or contradicts other decision records without marking them superseded. | Has a clear status (Proposed, Accepted, Deprecated, Superseded) and date; links to any decision it replaces. | Includes links to related user stories, research spikes, or architecture diagrams affected by the decision. |
<!-- RUBRIC-END -->
