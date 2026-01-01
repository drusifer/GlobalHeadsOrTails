# Linting & Code Quality Guide

This project uses a comprehensive suite of Python linters to ensure code quality, security, and maintainability.

## Quick Start

```bash
# Install all linting tools
pip install -e ".[dev]"

# Quick checks (fast feedback loop)
ruff check src/ --fix
ruff format src/

# Full quality gate (before committing)
ruff check src/
mypy src/
pylint src/
radon cc src/ -a -nc
vulture src/ --min-confidence 80
bandit -r src/ -ll
pytest tests/ --cov
```

## Linters Overview

### 1. **Ruff** - Fast All-in-One Linter & Formatter
**Purpose**: Fast Python linter combining dozens of tools (Flake8, isort, pyupgrade, etc.)

**What it detects**:
- Code errors and bugs (pyflakes)
- Style violations (pycodestyle)
- Security issues (bandit rules)
- Import sorting violations (isort)
- Cyclomatic complexity (mccabe)
- Code smells (pylint rules)
- Naming conventions (pep8-naming)
- Dead/commented code (eradicate)
- Performance anti-patterns
- Logging best practices
- Type annotation issues
- Boolean traps
- Unused arguments

**Run commands**:
```bash
# Check and auto-fix
ruff check src/ --fix

# Format code
ruff format src/

# Check specific rules
ruff check src/ --select E,F,I  # errors, flakes, imports only

# Show all enabled rules
ruff check --show-settings
```

**Configuration**: See `[tool.ruff]` in `pyproject.toml`

---

### 2. **Mypy** - Static Type Checker
**Purpose**: Verify type annotations and catch type errors before runtime

**What it detects**:
- Type mismatches
- Missing type annotations
- Invalid attribute access
- Incompatible return types
- Optional type errors
- Generic type violations

**Run commands**:
```bash
# Check types
mypy src/

# Strict mode (for specific modules)
mypy src/ntag424_sdm_provisioner/crypto/ --strict

# Generate type coverage report
mypy src/ --html-report mypy-report
```

**Configuration**: See `[tool.mypy]` in `pyproject.toml`

---

### 3. **Pylint** - Code Quality & Duplication Detector
**Purpose**: Comprehensive code quality analysis and duplicate code detection

**What it detects**:
- Code duplication (6+ similar lines)
- Code smells
- Design issues
- Unused variables/imports
- Inconsistent naming
- Complexity issues
- Best practice violations

**Run commands**:
```bash
# Check for code duplication only
pylint --disable=all --enable=R0801 src/

# Full pylint analysis
pylint src/

# Generate detailed report
pylint src/ --output-format=json > pylint-report.json
```

**Configuration**: See `[tool.pylint]` in `pyproject.toml`

**Duplication threshold**: 6 lines (configurable in `min-similarity-lines`)

---

### 4. **Radon** - Cyclomatic Complexity & Maintainability Index
**Purpose**: Measure code complexity and maintainability

**What it detects**:
- **Cyclomatic Complexity** (decision points in code)
  - A: 1-5 (simple, low risk)
  - B: 6-10 (moderate, low risk)
  - C: 11-20 (complex, moderate risk)
  - D: 21-30 (very complex, high risk)
  - E: 31-40 (extremely complex, very high risk)
  - F: 41+ (unmaintainable, very high risk)

- **Maintainability Index** (0-100 scale)
  - 20+ (maintainable)
  - 10-19 (moderately maintainable)
  - 0-9 (difficult to maintain)

**Run commands**:
```bash
# Cyclomatic complexity (show all functions)
radon cc src/ -a

# CC with averages and totals
radon cc src/ -a -nc --total-average

# Show only complex functions (C grade or worse)
radon cc src/ -nc -a

# Maintainability index
radon mi src/ -s

# Halstead metrics (volume, effort, bugs)
radon hal src/

# Raw metrics (LOC, SLOC, comments)
radon raw src/ -s
```

**No pyproject.toml config** - use CLI args

---

### 5. **Vulture** - Dead Code Detector
**Purpose**: Find unused code (dead code)

**What it detects**:
- Unused functions
- Unused classes
- Unused variables
- Unused imports
- Unused properties
- Unused attributes

**Run commands**:
```bash
# Find dead code (80% confidence minimum)
vulture src/ --min-confidence 80

# Show all potential dead code
vulture src/ --min-confidence 60

# Exclude false positives
vulture src/ --exclude "*/tests/*" --min-confidence 80

# Generate whitelist for false positives
vulture src/ --make-whitelist > .vulture_whitelist
```

**Confidence levels**: 0-100 (higher = more certain it's unused)

---

### 6. **Bandit** - Security Vulnerability Scanner
**Purpose**: Find common security issues in Python code

**What it detects**:
- SQL injection risks
- Hardcoded passwords/secrets
- Insecure random number generation
- Use of exec/eval
- Weak cryptography
- Shell injection vulnerabilities
- Unsafe deserialization
- File permission issues
- And 100+ more security checks

**Run commands**:
```bash
# Scan with medium/high severity only
bandit -r src/ -ll

# Full scan with JSON output
bandit -r src/ -f json -o bandit-report.json

# Scan specific severity
bandit -r src/ --severity-level medium

# Show all issues with confidence scores
bandit -r src/ -v
```

**Configuration**: See `[tool.bandit]` in `pyproject.toml`

---

## Two-Tier Quality Gates

### TIER 1: Quick Checks (Fast Feedback - < 5 seconds)
For rapid development (TDD workflow):

```bash
# Auto-fix what can be fixed
ruff check src/ --fix

# Format code
ruff format src/

# Run tests (fail fast)
pytest tests/ -x -q --tb=no
```

### TIER 2: Full QA Gate (Before Commit/Push)
Comprehensive checks before shipping:

```bash
# Run all linters
ruff check src/                        # Lint (no auto-fix)
ruff format --check src/               # Check formatting
mypy src/                              # Type checking
pylint src/                            # Duplication & quality
radon cc src/ -a -nc --total-average   # Complexity
radon mi src/ -s                       # Maintainability
vulture src/ --min-confidence 80       # Dead code
bandit -r src/ -ll                     # Security
pytest tests/ -v --tb=short --cov      # Full tests + coverage
```

## IDE Integration

### VS Code
Install extensions:
- **Ruff** (charliermarsh.ruff)
- **Pylance** (ms-python.vscode-pylance) - for type checking
- **Python** (ms-python.python)

Add to `.vscode/settings.json`:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "ruff.lint.run": "onSave"
}
```

## Ignoring Violations

### Inline Ignores
```python
# Ruff (specific rule)
x = 1  # noqa: F841

# Ruff (all rules)
x = 1  # noqa

# Mypy
x: Any = get_dynamic_value()  # type: ignore[misc]

# Pylint
def complex_function():  # pylint: disable=too-many-branches
    ...

# Bandit
password = "test123"  # nosec B105
```

### File-level Ignores
```python
# ruff: noqa: D100, D101
"""Module without docstrings."""

# mypy: ignore-errors
```

## Common Workflows

### Before Committing
```bash
# Format code
ruff format src/

# Fix auto-fixable issues
ruff check src/ --fix

# Run full checks
ruff check src/
mypy src/
pytest tests/ --cov
```

### CI/CD Pipeline
```yaml
- name: Lint
  run: |
    ruff check src/
    ruff format --check src/
    mypy src/
    bandit -r src/ -ll
    pytest tests/ --cov --cov-fail-under=80
```

### Refactoring Session
```bash
# Find duplicate code
pylint --disable=all --enable=R0801 src/

# Find dead code
vulture src/ --min-confidence 80

# Check complexity before/after
radon cc src/ -a -nc --total-average
```

## Rule Categories in Ruff

- **E**: pycodestyle errors (formatting, whitespace)
- **F**: pyflakes (unused imports, undefined names)
- **I**: isort (import sorting)
- **UP**: pyupgrade (modern Python syntax)
- **B**: bugbear (common bugs)
- **S**: bandit (security)
- **C90**: mccabe (cyclomatic complexity)
- **N**: pep8-naming (naming conventions)
- **D**: pydocstyle (docstrings)
- **ANN**: flake8-annotations (type hints)
- **ARG**: flake8-unused-arguments
- **ERA**: eradicate (commented code)
- **FBT**: flake8-boolean-trap
- **PIE**: flake8-pie (misc lints)
- **PLR/PLC/PLE/PLW**: pylint rules
- **PERF**: performance anti-patterns
- **FURB**: refurb (modernize patterns)
- **LOG/G**: logging best practices
- **PT**: pytest style

## Metrics Targets

### Cyclomatic Complexity
- **Target**: Most functions ≤ 10 (grade B or better)
- **Acceptable**: ≤ 20 for complex protocol/crypto code
- **Refactor**: Anything > 20

### Maintainability Index
- **Target**: ≥ 20 (maintainable)
- **Warning**: < 20 (consider refactoring)
- **Critical**: < 10 (technical debt)

### Code Coverage
- **Target**: ≥ 80%
- **Critical paths**: 100% (authentication, crypto, provisioning)

### Code Duplication
- **Target**: Zero duplications ≥ 6 lines
- **Action**: Refactor into shared functions

## Troubleshooting

### "Module not found" errors in Mypy
Add to `pyproject.toml`:
```toml
[[tool.mypy.overrides]]
module = "problematic_module.*"
ignore_missing_imports = true
```

### Ruff format changes conflicting with Ruff check
The ignore rules in `pyproject.toml` already handle this. Line length (E501) is ignored since the formatter handles it.

### Too many false positives in Vulture
Create a whitelist:
```bash
vulture src/ --make-whitelist > .vulture_whitelist
vulture src/ --exclude .vulture_whitelist
```

### Bandit reports false positive
Use `# nosec` comment with issue code:
```python
temp_password = "changeme"  # nosec B105
```

## Additional Resources

- [Ruff documentation](https://docs.astral.sh/ruff/)
- [Mypy documentation](https://mypy.readthedocs.io/)
- [Pylint documentation](https://pylint.readthedocs.io/)
- [Radon documentation](https://radon.readthedocs.io/)
- [Bandit documentation](https://bandit.readthedocs.io/)
- [Vulture documentation](https://github.com/jendrikseipp/vulture)
