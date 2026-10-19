<!--
Research finding and technical spike template. Owned by all agents — see agents/templates/ARTIFACTS.md.
Used for documenting research spikes, performance investigations, bug root-cause discoveries,
and tool/library evaluations.
Delete this comment AND the review rubric at the end (everything from RUBRIC-START to
RUBRIC-END): the rubric belongs to the template, not to the document.
Oracle reviews this at groom (or Morpheus during architecture/spike reviews) using the FINDING rubric.
-->
# Research Spike / Finding: {Short Descriptive Title}

*   **Date**: {YYYY-MM-DD}
*   **Author**: {AgentName / Persona}
*   **Tags**: `#{Category}` `#{Component}` `#{Persona}`
*   **Status**: {Completed | Abandoned | Converted to Story/ADR}

---

## 1. Objective & Hypothesis

* **Primary Question:** {What specific, falsifiable question were we trying to answer?}
* **Hypothesis:** *If we {approach / condition}, then {expected outcome}, which resolves {risk / issue}.*
* **Timebox / Effort:** {e.g. 2 hours / 1 day / exploratory spike}

## 2. Context & Investigation Setup

* **Background:** {What triggered this investigation? Bug, performance bottleneck, or new technology evaluation?}
* **Test Environment:** {OS, runtime version, hardware, specific branch/commit}
* **Tools Used:** {Profiling tools, test harnesses, via, benchmark scripts}

## 3. Observable Evidence & Findings

{Concrete logs, terminal commands run, benchmark figures, or code traces that prove the finding. No speculation.}

```bash
# Reproduction command:
{command run}
```

```text
# Observed output / logs / metrics:
{exact output or trace snippet}
```

## 4. Trade-offs & Evaluated Options

| Approach Explored | Pros | Cons | Verdict |
|---|---|---|---|
| **Option A:** {e.g. In-memory cache} | {High speed, zero deps} | {Memory overhead on large sets} | {Recommended / Viable} |
| **Option B:** {e.g. Disk-backed SQLite} | {Persistent, low RAM} | {Higher I/O latency} | {Rejected due to X} |

## 5. Decision & Downstream Action Items

* **Answer to Research Question:** {Direct 1-2 sentence answer based on evidence}
* **Recommendation:** {Proceed with Option X | Abandon approach | Pivot}
* **Spike Code Cleanup:** {Confirm: All temporary PoC / spike code is discarded or kept strictly in throwaway scratch branches — not merged to production directly.}
* **Follow-up Actions:**
  * [ ] Create downstream User Story / Task: `{ID or description}`
  * [ ] Record Architecture Decision Record: `{ADR-ID if architectural choice locked}`

## 6. References & Reproduction

* **Affected Files:** `{path/to/relevant/file}`
* **Specification / Documentation:** `{URL, standard section, or external issue link}`
* **Reproduction Steps:** {Exact steps for another engineer to reproduce the finding}

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — FINDING

Self-checked by author upon recording; reviewed by Oracle at groom (or Morpheus during technical spike review).
Verdict line: `rubric FINDING: HYPO=_ EVID=_ TRADE=_ ACTN=_ REPR=_` (W, A or S).
Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `HYPO` | Does it address a specific, falsifiable question or spike objective? | Broad or narrative topic ("investigated auth") without a clear question, hypothesis, or measurable goal. | States a focused research question and the expected outcome or hypothesis being tested. | Quantifies the target threshold or pass/fail criterion (e.g. "whether library X handles >10k req/s under 50ms latency"). |
| `EVID` | Is the discovery backed by verifiable, reproducible data? | Claims an outcome or limitation without evidence, reproduction commands, logs, or code snippets ("it didn't work"). | Includes concrete evidence: exact commands run, log outputs, benchmark figures, or specific spec/file citations. | Provides a minimal reproduction snippet or test case that any team member can run immediately to verify the behavior. |
| `TRADE` | Were viable alternatives compared objectively? *(Report n/a for pure bug triage)* | Evaluates only one approach in isolation or dismisses alternatives without documented reasons. | Compares at least two viable approaches in a tradeoffs matrix outlining concrete pros and cons. | Scores options against explicit project constraints (runtime footprint, dependency health, maintenance burden, licensing). |
| `ACTN` | Does it deliver an unambiguous decision and next step? | Concludes with "more research needed" or observations without a decision; leaves spike prototype code in production path. | Delivers a clear decision (proceed, pivot, or abandon) and lists actionable follow-up items (stories or ADRs). | Explicitly confirms temporary spike/PoC code is discarded or isolated, with links to drafted user stories or ADRs. |
| `REPR` | Can another engineer locate the affected components and environment? | Omits file paths, hardware details, library versions, or environment configuration needed to reproduce the finding. | Names the exact files, versions, and environment conditions where the finding was observed. | Documents exact environment configuration (OS, runtime flags, hardware pins) and links related specs or commits. |
<!-- RUBRIC-END -->