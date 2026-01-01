# QA Agent Commands

## Core Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `*qa test` | Run the full test suite or a specific scope. | `*qa test [scope]` |
| `*qa verify` | Create a test plan for a new feature, consulting the Oracle. | `*qa verify <feature>` |
| `*qa report` | Summarize the current health of the codebase. | `*qa report` |
| `*qa repro` | Create a minimal test case to reproduce a reported bug. | `*qa repro <issue>` |
| `*qa review` | Review code changes for smells, testability, and spec compliance. | `*qa review <change>` |

## Scopes for `*qa test`

- `all`: Run all tests (default).
- `crypto`: Run tests in `test_crypto_components.py`.
- `auth`: Run authentication related tests.
- `changekey`: Run ChangeKey related tests.
- `format`: Run Format PICC related tests.

## Protocol

1.  **Regression Prevention**: Always run `*qa test` before declaring a feature done.
2.  **Oracle Verification**: Use `*or ask` to confirm expected behavior for new test cases.
