# How to Run Scripts and Tests in This Project

**CRITICAL**: This project uses a Python virtual environment at `.venv`. ALL commands MUST use the venv Python.

**Environment**: Windows PowerShell (use `&` operator and forward slashes for paths)

---

## Activating Virtual Environment (RECOMMENDED)

The standard workflow for this project is to activate the virtual environment first. This ensures all commands run with the correct dependencies and Python version.

```powershell
# Navigate to project root
cd ntag424_sdm_provisioner

# Activate venv with project settings (centralizes __pycache__)
. .\scripts\activate.ps1

# Now you can use python directly
python script.py
python -m pytest tests/ -v

# Run the TUI (Text User Interface)
provision-tui
# OR
python -m ntag424_sdm_provisioner.tui.tui_main

# Deactivate when done
deactivate
```

### Linting Scripts

```powershell
# Quick checks (TDD - fast feedback)
.\scripts\lint-quick.ps1

# Full QA gate (sprint acceptance)
.\scripts\lint-full.ps1

# Full QA without slow tests
.\scripts\lint-full.ps1 -SkipSlowTests
```

---

## Alternative: Direct Path Execution

If you cannot activate the environment, you can use the full path to the Python executable.

### Base Python Command

```powershell
# From project root (ntag424_sdm_provisioner/)
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe script.py

# Or with full path (adjust username)
& c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/.venv/Scripts/python.exe script.py
```

**Always use the `&` operator and forward slashes in PowerShell!**

### Common Commands

```powershell
# Run TUI
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe -m ntag424_sdm_provisioner.tui.tui_main

# Run tests
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe -m pytest tests/ -v

# Run example script
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe examples/22_provision_game_coin.py

# Generate symbol index
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe docs\analysis\scripts\generate_symbol_index.py

# Syntax check
cd ntag424_sdm_provisioner
& .\.venv\Scripts\python.exe -m py_compile src\ntag424_sdm_provisioner\constants.py
```

---

## Project Structure Reference

```
ntag424_sdm_provisioner/
├── .venv/                          # Virtual environment
│   └── Scripts/
│       └── python.exe             # ← Use this Python!
├── src/
│   └── ntag424_sdm_provisioner/   # Main package
│       ├── commands/
│       ├── crypto/
│       └── *.py
├── tests/                         # Test files
│   └── ntag424_sdm_provisioner/
│       └── test_*.py
├── examples/                      # Example scripts
│   └── *.py
└── pyproject.toml                # Package config
```

---

---

## Troubleshooting

### Import Errors
If you see `ImportError` or `NameError` when running the TUI:
1. Check syntax: `python -m py_compile src/ntag424_sdm_provisioner/constants.py`
2. Test imports: `python -c "from ntag424_sdm_provisioner.constants import CommMode, AccessRight"`
3. Verify virtual environment is activated or use full path

### Path Issues
- **PowerShell**: Always use `&` operator for direct execution: `& .\.venv\Scripts\python.exe`
- **Forward slashes**: Use forward slashes in full paths: `c:/Users/...`
- **Working directory**: Commands should be run from `ntag424_sdm_provisioner/` directory

### TUI Won't Start
1. Verify syntax errors are fixed: `python -m py_compile src/ntag424_sdm_provisioner/constants.py`
2. Check all imports: `python -c "from ntag424_sdm_provisioner.tui.tui_main import main"`
3. Review recent changes to `constants.py` for missing enum definitions

---

**Last Updated:** 2025-11-28  
**Remember:** Always use the full path with `&` operator in PowerShell!  
**Environment:** Windows PowerShell (use `&` operator and forward slashes for paths)

