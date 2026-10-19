# Lesson Template

<!--
Copy the entry below into `agents/oracle/lessons.md` (a standing rule agents must follow) or
`docs/LESSONS.md` (an engineering lesson from a sprint) — see the PLACE criterion in the rubric.
Do not copy the rubric at the end.
-->

## [YYYY-MM-DD] {Short Descriptive Title}

> **Tags:** #{Category} #{Component} #{AgentName}

### Context
{Briefly describe the situation, task, or error that led to this lesson. Example: "While debugging the NTAG 424 CMAC calculation..."}

### The Issue
{What went wrong? What was the blocker? Example: "We assumed standard zero-padding, but the hardware requires ISO 9797-1 padding."}

### The Solution
{How was it resolved? Example: "Implemented a custom padding function in crypto.py."}

### The Rule (The "Lesson")
{The explicit instruction for future agents. This is the most important part. Example: "ALWAYS use ISO 9797-1 padding for all CMAC operations. Never use zero padding."}

### References
- **Commit:** {Commit Hash or "N/A"}
- **Files:** `{path/to/affected_file.py}`

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — LESSON

Self-checked by Oracle when recording; reviewed by Smith at the sprint-close test for every
lesson added that sprint. Verdict line (one per lesson): `rubric LESSON: WHEN=_ WHAT=_ RULE=_
CAUSE=_ PLACE=_` (W, A or S). Any W rejects, naming the criterion and the fix.
See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `WHEN` | Would a future reader recognise the situation it applies to? | It only makes sense to someone who was there, or names no trigger. | It states the situation in terms a reader will meet again ("when swapping an implementation behind a stable contract"). | The trigger is in the title, so a reader scanning headings finds it. |
| `WHAT` | Does it say concretely what happened? | "We had problems with X" — no file, command, message or outcome. | It names what was done, what went wrong and how it showed up. | It includes the exact error, command or number, and where to find the evidence. |
| `RULE` | Does it tell the reader what to do differently? | It ends in an observation or a moral ("be careful with...") rather than an instruction. | It gives an action a reader can take the next time the situation arises. | The action is specific enough to verify afterwards that it was followed. |
| `CAUSE` | Is it about the cause rather than the symptom? | The rule would have prevented this one incident but not the next one like it. | It identifies why the problem happened and the rule addresses that. | It notes a wrong diagnosis that was tried first, so the reader does not repeat it. |
| `PLACE` | Is it in the right file, and still true? | It duplicates an existing lesson, sits in the wrong file, or refers to things that no longer exist without saying so. | It is new, in the right file, and names things that exist; anything it replaces is marked superseded. | It links the related lessons or decisions. |
<!-- RUBRIC-END -->

