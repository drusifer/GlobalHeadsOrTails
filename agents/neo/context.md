# Agent Local Context — Neo

> ## Recent Decisions
> - Added `main()` CLI entrypoint with `--check` flag to `tag_validator.api.app` to match `pyproject.toml` `[project.scripts]` declaration.
> - Updated `Config` in `tag_validator.config` to evaluate `os.getenv` dynamically via `default_factory`.
>
> ## Key Findings
> - 29/29 `tag_validator_service` unit tests pass; `ruff check` clean.
>
> ## Important Notes
> - Handing off container packaging (`Dockerfile`, `.dockerignore`, `Makefile` `export-image`) to Tank per Neo/Tank boundary rules.
>
> ---
> *Last updated: 2026-10-20T15:04:30-04:00*
