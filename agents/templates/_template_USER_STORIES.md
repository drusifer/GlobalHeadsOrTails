<!--
Sprint stories template. Owned by Cypher — see agents/cypher/SKILL.md and the sprint skill.
Copy to docs/sprints/USER_STORIES_SPRINT<N>.md and replace every {placeholder}.
{KEY} is the project's short story-ID key (for example STORY-FING-31 in a project called Fingerling).
Delete this comment AND the review rubric at the end (everything from RUBRIC-START to
RUBRIC-END): the rubric belongs to the template, not to the document.
Morpheus appends the architecture section after Smith approves the stories.
-->
# Sprint {N} User Stories: {Short Title}

*   **Total Points**: {sum} (Tier {1|2})
*   **Branch**: `sprint-{N}`
*   **Source**: {who asked, when, and where it is recorded}
*   **Status**: Draft — awaiting Smith Gate 1

## Goal

{Two to four sentences: what will be true for a user or the owner when this sprint is done, and
why it matters now. No implementation.}

## Assumptions made for the owner

{Anything decided on the owner's behalf because they did not say. Each one a sentence the owner
can confirm or overturn.} / None — every choice here was the owner's.

---

## STORY-{KEY}-{id}: {Outcome in a few words}
**Points:** {n}{ · **Owner:** {persona, if not Neo}}

**As a** {who benefits},
**I want** {what they will be able to do},
**so that** {why it matters to them}.

### Acceptance Criteria
1. {One observable behaviour, stated so that a tester could say yes or no.}
2. {What the user sees when something is wrong: bad input, missing file, refused action.}
3. {...}

{Repeat the story block for each story.}

---

## Out of Scope
- {Something a reader might reasonably expect to be included, and is not.}

## Open Questions
1. {A question, who can answer it, and what is assumed until they do.} / None.

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — STORIES

Self-checked by Cypher before handoff; reviewed by Smith at Gate 1.
Verdict line: `rubric STORIES: OUT=_ TEST=_ FAIL=_ SCOPE=_ SIZE=_ DESIGN=_` (W, A or S).
Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `OUT` | Does each story say who benefits and what they can do afterwards? | A story describes work to be done ("refactor X", "add module Y") or names no one who benefits. | Every story has a real beneficiary and an outcome they would recognise. | The goal and the stories read as one argument: a reader could explain why each story is needed. |
| `TEST` | Could a tester answer yes or no to every acceptance criterion? | A criterion uses "should", "properly", "robust", "user-friendly" or bundles several behaviours so that partial success is undefined. | Each criterion is one observable behaviour with a definite pass condition. | Criteria carry concrete values or examples (an input, the exact message, a count) that can be used directly as test cases. |
| `FAIL` | Do the criteria say what the user sees when things go wrong? Report `n/a` for a story that takes no input and cannot be refused. | Only the happy path is specified for a story that takes input or can be refused. | Each story that can fail has a criterion for its most likely failure. | Failure criteria say what the user is told and what state is left behind (nothing written, original intact). |
| `SCOPE` | Is it clear what is not being done, and what was assumed? | No out-of-scope section, or assumptions are buried inside criteria where the owner would not see them. | Out-of-scope lists what a reader might expect and will not get; assumptions and open questions are stated separately. | Each assumption says what happens if it is wrong, and each open question names who can answer it. |
| `SIZE` | Can each story be delivered and verified on its own? | A story depends on another without saying so, has no points, or is large enough to hide several stories. | Stories are pointed, independently verifiable, and their total matches the stated tier. | Stories are ordered so that each one leaves the product usable, and dependencies are stated. |
| `DESIGN` | Do the criteria leave the design to the architecture step? | Criteria prescribe internals — a function signature, a class, a data structure, a library — that the user could not observe and nobody asked for. | Criteria describe behaviour; any named technology is something the user or owner explicitly asked for. | Where a constraint is genuinely required, the criterion says why, so the architect can meet the intent. |
<!-- RUBRIC-END -->
