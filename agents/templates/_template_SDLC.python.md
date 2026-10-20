<!--
SDLC template — Python (pyproject.toml + .venv + pip). Owned by Tank — see
agents/skills/build-env/SKILL.md. Copy to docs/SDLC.md, replace every {placeholder}, and
correct any pre-filled line that is not true for this repo (e.g. uv/poetry instead of pip,
pytest instead of unittest). Delete this comment AND the review rubric at the end (RUBRIC-START to RUBRIC-END): the rubric
belongs to the template, not to the document.
-->
# {Project} — SDLC

How this project is built, tested, changed and released — the source of truth for change
management across the whole project. **Owned by Tank**; to change anything here,
ask `@Tank *devops sdlc <what and why>` — the mechanism and this document change together.

## 1. Toolchain

| | Python |
|---|---|
| Runtime version | {3.x} — `requires-python` in `pyproject.toml` |
| Manifest | `pyproject.toml` (PEP 621 `[project]`; tool config in `[tool.*]`) |
| Lockfile | None — plain pip has none; lower bounds are pinned in the manifest {or: `uv.lock` / `poetry.lock`, committed} |
| Package manager | stdlib `venv` + `pip` {or: uv / poetry} |
| Local environment | `.venv/` (gitignored, isolated from system site-packages) |

Other required tools: `make`, a system `python3` to create the venv{, others} .

## 2. Setup

From a clean checkout:

```sh
make install     # python3 -m venv .venv && pip install -e ".[dev]"
make test
```

Nothing is installed into the system Python. Never use `sudo pip` or `--break-system-packages`;
a target that needs root calls the venv interpreter by path (`sudo .venv/bin/python ...`).

## 3. Make targets

The Makefile is the only entry point; every recipe runs `.venv/bin/python` and stops with
"run 'make install' first" if `.venv` is missing.

| Target | Runs | Notes |
|---|---|---|
| `install` | `.venv/bin/python -m pip install -e ".[dev]"` | creates `.venv` if absent; idempotent |
| `test` | `.venv/bin/python -m {pytest / unittest discover -s tests}` | `ARGS="..."` passes through |
| `lint` | `{ruff check . / mypy ...}` | |
| `format` | `{ruff format .}` | |
| `build` | `.venv/bin/python -m build` | |
| `run` | `.venv/bin/{command}` | `ARGS="..."` |
| `clean` | removes `__pycache__`, `*.egg-info`{, `dist/`} | keeps `.venv` |
| `distclean` | `clean` + removes `.venv/` | |
| `help` | lists targets | |

Standard targets deliberately absent: {target — why} / None.

## 4. Dependencies

- **Add a runtime dependency:** add it to `[project] dependencies` in `pyproject.toml` with a
  lower bound, then `make install`.
- **Add a dev/test tool:** add it to `[project.optional-dependencies] dev`, then `make install`.
- **Optional features:** separate extras ({name} = {what needs it}); `dev` includes them.
- **Upgrade / remove:** edit the bound or delete the line, then `make distclean && make install`.
- **Commit afterwards:** `pyproject.toml`{ and the lockfile}.
- **Who:** Neo adds and bumps dependencies. A new package manager, language or Python version
  is a mechanism change — Tank's.
- `requirements.txt`: {absent / a pointer containing `-e .[dev]`} — never the source of truth.

## 5. Quality gates

| Gate | Target | Required before |
|---|---|---|
| Tests | `make test` | every handoff to Trin; sprint close |
| {Lint / types} | `make lint` | {when} |
| {Secret scan} | `make {gitleaks}` | {when} |

## 6. Change management

This document is the project's source of truth for how a change gets from request to done.
Where another document, skill or habit disagrees with it, this one wins — and the disagreement
is reported to Tank so one of them gets fixed.

### Change classes

| Class | Examples | Proposed by | Approved by | Must pass | Recorded in |
|---|---|---|---|---|---|
| Routine | feature, fix, refactor, docs, adding a dependency via section 4 | {anyone / Cypher story} | {Morpheus review} | section 5 gates | {task board, commit} |
| Mechanism | toolchain, manifest layout, make targets, gates, CI, this document | anyone, via `@Tank *devops sdlc` | Tank{ + user} | from-clean rebuild + section 5 | this file, `{decisions log}` |
| Release / deploy | version bump, publish, deploy | {who} | {who} | {gates} | {changelog / tag} |
| Emergency | hotfix outside a sprint | {who} | {who — may be after the fact} | `make test` at minimum | {where}, reviewed at next sprint close |

### Flow

1. **Request** — {where changes are requested and how they are sized/planned}.
2. **Branch** — {default branch; branch naming; or "work directly on the default branch"}.
3. **Implement** — through `make` targets only; tests accompany behaviour changes.
4. **Gate** — the section 5 gates pass locally before handoff.
5. **Review** — {who reviews what; what counts as approval}.
6. **Integrate** — {who commits/merges/pushes, and when; commit message convention}.
7. **Record** — {what is updated: task board, decisions log, changelog, user docs}.

### Rules

- {Who may commit, push, tag — e.g. agents commit only when the user asks.}
- {What must never be committed: secrets, the local environment, generated artifacts.}
- **Rollback:** {how a bad change is backed out}.
- **Changing this document:** only Tank edits it; every edit updates the Last verified line.

## 7. Versioning and release

- **Version lives in:** `[project] version` in `pyproject.toml`.
- **Bumped:** {when, by whom}
- **CLI entry points:** `[project.scripts]` — installed to `.venv/bin/` by `make install`.
- **Artifact:** {wheel/sdist via `make build`, published to ...} / None — not shipped.

## 8. CI / deploy

{Workflow file, triggers, deploy target} / None — everything runs locally.

CI must run `make install && make test`{ && make lint}, not raw tool commands.

## 9. Known deviations

{e.g. venv created with `--system-site-packages` because {package} is only available from the
OS package manager} / None.

## 10. Conformance check

Run by Tank at sprint close (`*devops sdlc-check`):

1. `make distclean && make install && make test` passes{, plus each gate in section 5}.
2. Every third-party import in the source tree is declared in `pyproject.toml`
   (`.venv/bin/pip list --not-required` shows nothing unexpected).
3. `.venv/pyvenv.cfg` still says `include-system-site-packages = false`{ / true, per section 9}.
4. Every target in section 3 exists and still does what the table says; new targets are listed.
5. No doc or script tells people to run bare `python3`/`pip` against the project.
6. `.venv/` and `*.egg-info/` are ignored; `requires-python` unchanged or deliberately bumped.
7. This sprint's changes followed section 6: right class, right approval, recorded where it says.
8. {Project-specific checks}

---
*Last verified: {YYYY-MM-DD} against {commit or sprint} by Tank.*

<!-- RUBRIC-START — for reviewers. Delete everything from here to RUBRIC-END when you turn this
     template into a real document. -->
## Appendix: Review rubric — SDLC

Self-checked by Tank on every create or update; reviewed by Oracle at groom in any sprint where
`docs/SDLC.md` changed. Verdict line: `rubric SDLC: TRUE=_ WHOLE=_ CLEAN=_ CLASS=_ CHECK=_ GAPS=_`
(W, A or S). Any W rejects, naming the criterion and the fix. See `agents/templates/ARTIFACTS.md`.

This rubric judges the document. Whether the project matches it is Tank's `*devops sdlc-check`.

| Code | Criterion | Weak (W) | Acceptable (A) | Strong (S) |
|---|---|---|---|---|
| `TRUE` | Does it describe what exists today? | A command, target or file it names does not exist, or planned work is written as if done. | Everything stated as present is present; anything not yet built is labelled as such. | It carries a dated "last verified" line saying what was actually run. |
| `WHOLE` | Can a newcomer find every part of the lifecycle? | A section is missing or left as a placeholder, so a reader cannot tell whether the topic was considered. | Every section is filled in, or says "None" with a reason. | Sections cross-reference each other where one depends on another (gates ↔ targets ↔ CI). |
| `CLEAN` | Could someone go from a fresh checkout to passing tests using only this? | Setup depends on a tool, step or prior state the document does not mention. | Prerequisites and exact commands are listed in order. | It also says what each prerequisite is for and how to tell the setup worked. |
| `CLASS` | Can a reader tell how *their* change must be handled? | Change classes overlap or leave common cases out, or "who approves" is a role nobody holds. | Any ordinary change falls into exactly one class with a named approver, gates and a place it is recorded. | The flow from request to record is written as steps a new contributor could follow unaided. |
| `CHECK` | Is the conformance check something that can be run? | Items are judgements ("docs are up to date") with no way to answer yes or no. | Each item is a command or an inspection with a definite pass condition. | Items say what a failure would look like and who fixes it. |
| `GAPS` | Does it admit what is missing or unverified? | A known gap is absent, or a deviation is listed without its reason. | Deviations from convention and unverified areas are listed with reasons. | Each gap says what would close it, and agreed-but-unbuilt changes are tracked until they land. |
<!-- RUBRIC-END -->
