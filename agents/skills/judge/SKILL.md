---
name: judge
description: Interactive loop to evaluate agent skill/tool/persona usage (e.g. *judge via, *judge make, *judge trin), catalog bugs/anti-patterns, and optimize agent prompt instructions.
triggers: ["*judge"]
requires: ["bob-protocol", "chat", "make"]
---

Full workflow for evaluating the effectiveness of a target skill, tool, or persona, ensuring correct usage, correctness, cataloging bugs, and updating agent prompts to minimize token usage and optimize efficiency.

TLDR:
    The loop runs: Trin (runs target scenarios / compiles session traces) → Smith (judges token waste, compliance, and catalogs bugs) → Neo (fixes code/script bugs) → Bob (updates prompts/skills) → Trin (verification run).
    Any defect, resource waste, or compliance failure must be cataloged and resolved, rather than accepted.

# Judge — Evaluation & Optimization Loop

```
Trin (Usage Run) → Smith (UX/Token/Compliance Review & Bug log) → Neo (Bug Fixes) → Bob (Prompt/Skill Updates) → Trin (Verification Run)
```

---

## Target-Specific Contexts

When executing `*judge <target>`, the loop evaluates the specified target (e.g., `via`, `make`, `trin`):
- **`via`**: Focuses on database queries, query efficiency (avoiding fallback file reads/grep), qualified matches, result counts, and CLI parser reliability.
- **`make`**: Focuses on use of Makefile targets, avoidance of raw commands, captured logs, and verbosity flags.
- **`trin`** (or other personas): Focuses on adherence to persona role, handoff instructions, State Management Protocol compliance, and coordination clarity.
- **Workflow Loops (`impl`, `fix`, `refactor`, `spike`, `uat`, `deploy`, `epic`, `story`, `sprint`, `bloop`)**: Evaluates loop execution against the canonical Loop Effectiveness Rubrics (`LOOP_<TARGET>`) defined in each loop's `SKILL.md` and indexed in `agents/templates/ARTIFACTS.md`.
- **Other tools/skills**: Focuses on correct parameter passing, error handling, avoidance of failure loops, and optimal token utilization.

---

## Step 1 — Trin: Usage Run & Trace Compilation
```
Trin *qa judge <target>
```
- **Required tool — `bobp make judge-trace [DATE=YYYY-MM-DD] [FORMAT=html|md]`**: this runs `bobp trace-annotate`, which parses the **real Claude Code JSONL session transcripts** (`~/.claude/projects/<slug>/*.jsonl`) for the given date and programmatically flags anti-patterns (`AP-SKILL-RELOAD`, `AP-MAKE-BYPASS`, `AP-RAW-VENV`, `AP-MAKE-PIPE`, `AP-VIA-GREP`, `AP-VIA-READ`, `AP-DUP-READ`) via `agents/tools/trace_rules.json`. This is ground truth — actual tool-call events, not a prose summary. Output defaults to `agents/trin/judge_tool_trace.{html,md}`.
- **Do not hand-reconstruct a trace from `agents/CHAT.md` instead.** CHAT.md only contains what personas chose to summarize about their own work — it cannot show tool-call-level behavior (redundant invocations, piping, raw venv calls, via-bypasses) and produces a systematically over-optimistic trace. `bobp make judge-trace` is the only source of truth for tool/skill-use judging; CHAT.md and persona `state.md` files remain the source of truth for *process/protocol* adherence (chain sequencing, gate compliance, handoffs) — the two are complementary, not interchangeable.
- **Manual review is still required after running the tool**: read the raw flags before scoring — the rule regexes are heuristics and can both over-flag (e.g. a `make <target> | tail` where the invocation wasn't actually via `bobp make`, so there's no build.out capture to be redundant with) and under-flag. Note any flag you're overriding and why in the trace report, per-flag, not as a blanket dismissal.
- Trin writes the analysis (raw counts + manual-review verdict per flag type + any additional scenario coverage the tool can't see) to `agents/trin/judge_<target>_trace.md`.
- **Trin's constraints**: Ensure that the target is exercised in realistic conditions representing typical developer/agent workflow.
- **Live vs. completed sessions**: `bobp make judge-trace` scores the JSONL transcript as it exists *right now*. If the `*judge` loop is run inside the same live session it's evaluating, every subsequent step of the loop (reading the trace, editing files, re-running the tool) appends more tool calls to that same transcript — the call/flag counts will keep growing across iterations, and a fresh Smith TES score at each iteration is not comparing like-for-like. Prefer running `*judge` on a session that has already ended. If run mid-session anyway, treat iteration 1's score as the baseline for defect-finding only, verify specific fixes by checking whether the specific previously-flagged entries are now absent (not by chasing a fresh 90+ on an ever-growing trace), and defer a real numeric re-score to the next `*judge` invocation on a completed session.

### Handoff:
```bash
bobp chat "[target] run complete. @Smith *user feedback judge <target>" --persona Trin --cmd "qa handoff" --to Smith
```

---

## Step 2 — Smith: Trace Evaluation & Scoring
```
Smith *user feedback judge <target>
```
- Smith reviews the execution trace to evaluate usability, correctness, and token efficiency.
- **Trace Effectiveness Score (TES) Rubric (Max: 100 points)**:
  - **Start at 100 points.**
  - **Correctness & Success**: Deduct **-5 points** for each scenario or action where the target failed to accomplish the goal or returned incorrect results.
  - **Resource Waste (Tokens / Commands)**:
    - Deduct **-5 points** for each redundant or fallback tool call (e.g., using `grep` or file reads when `via` queries or a simple `make` target could have succeeded, or invoking the same tool/command multiple times unnecessarily).
    - Deduct **-3 points** for each command returning overly verbose outputs due to lack of limits or poor formatting.
    - Deduct **-2 points** for failing to use standard project automation (e.g., executing raw pytest or shell commands instead of using the designated `make` target).
  - **Protocol & Persona Adherence**:
    - Deduct **-5 points** for any violation of the State Management Protocol (missing context files, incorrect summarizing, improper handoffs).
  - **Efficiency/Design Bonuses**:
    - Add **+2 points** (up to **+10 points** maximum) for highly efficient, precise usage patterns or elegant scripting.
- **Bug/Defect Cataloging**: If any command crashes, returns incorrect results, violates constraints, or behaves unexpectedly, Smith logs the details in `agents/smith/bugs.md` (or `bugs_<target>.md`).
- **Decision & Loop Control**:
  - Record the final score in `agents/smith/trace_eval.md` (or `trace_eval_[target].md`).
  - **Target Score**: **90 points** or higher is considered optimal.
  - **Branching**:
    - **If TES >= 90** and no bugs/anti-patterns remain: Hand off to Trin to finalize and exit.
    - **If TES < 90** or bugs/anti-patterns remain:
      - If code/script bugs exist: Hand off to Neo (`*swe fix judge <target>`).
      - If prompts/skills are sub-optimal but code is correct: Hand off to Bob (`*prompt update judge <target>`).

### Handoff (Bugs Found or TES < 90 with code/script issues):
```bash
bobp chat "Score: [TES]. Bugs cataloged in bugs.md. @Neo *swe fix judge <target>" --persona Smith --cmd "user feedback" --to Neo
```

### Handoff (No Bugs but TES < 90 with usage/query/prompt issues):
```bash
bobp chat "Score: [TES]. Sub-optimal patterns. @Bob *prompt update judge <target>" --persona Smith --cmd "user feedback" --to Bob
```

### Handoff (TES >= 90 & No Bugs):
```bash
bobp chat "Optimal score [TES] reached! No bugs. @Trin *qa done" --persona Smith --cmd "user feedback" --to Trin
```

---

## Step 3 — Neo: Bug Fixes & Test Verification
```
Neo *swe fix judge <target>
```
- Neo resolves the bugs or structural issues cataloged in `agents/smith/bugs.md` (or target bug file).
- Neo ensures any scripts, Makefiles, or codebase modules behave correctly.
- Neo runs the project tests (`bobp make test`) to ensure a completely green baseline.

### Handoff:
```bash
bobp chat "Bugs resolved and test suite verified green. @Bob *prompt update judge <target>" --persona Neo --cmd "swe handoff" --to Bob
```

---

## Step 4 — Bob: Prompt Tuning & Skill Optimization
```
Bob *prompt update judge <target>
```
- Bob extracts the optimal usage patterns identified by Smith and updates:
  - The universal customization skill guidelines under `agents/skills/<target>/SKILL.md` (or the relevant skill/persona file).
  - Specialist persona instructions (`agents/<persona>/SKILL.md`) to guide future agent interactions and prevent identified anti-patterns.
- Bob registers the updated skills/rules configurations.

### Handoff:
```bash
bobp chat "Agent prompts and target skill updated. @Trin *qa verify judge <target>" --persona Bob --cmd "prompt update" --to Trin
```

---

## Step 5 — Trin: Re-run & Loop Verification
```
Trin *qa verify judge <target>
```
- Trin re-executes the target scenarios/actions using the updated skills and prompts.
- Generates a new session trace report.
- **If verifying inside the same live session** (see the live-vs-completed note in Step 1): confirm the specific previously-cataloged bug entries are gone from the new trace and that no real detections were lost — do not require a fresh TES >= 90 on the now-larger trace before closing the loop.
- **Handoff to Smith for Re-scoring (Looping)**: Hand off to Smith to re-evaluate the new session trace. The loop continues (**Trin -> Smith -> [Neo ->] Bob -> Trin**) until Smith issues a `TES >= 90` verdict (or after 5 consecutive iterations without score improvement).

### Handoff (Trigger Next Scoring Iteration):
```bash
bobp chat "New run complete and trace generated. @Smith *user feedback judge <target>" --persona Trin --cmd "qa verify" --to Smith
```

### Handoff (Loop Complete - TES >= 90):
```bash
bobp chat "Verification complete. Optimal score reached and loop closed successfully." --persona Trin --cmd "qa done" --to all
```
