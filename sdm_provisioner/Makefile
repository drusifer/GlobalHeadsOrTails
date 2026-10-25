.PHONY: help test lint tui cli clean

ifneq ("$(wildcard ../.venv/bin/python)","")
PYTHON ?= ../.venv/bin/python
else ifneq ("$(wildcard ../.venv/Scripts/python.exe)","")
PYTHON ?= ..\.venv\Scripts\python.exe
else ifneq ("$(wildcard .venv/bin/python)","")
PYTHON ?= .venv/bin/python
else ifneq ("$(wildcard .venv/Scripts/python.exe)","")
PYTHON ?= .venv\Scripts\python.exe
else
PYTHON ?= python3
endif

export PYTHONPATH := src:../shared/src:../tag_validator_service/src$(if $(PYTHONPATH),:$(PYTHONPATH))

help: ## Show available make targets
	@echo "Available targets for sdm_provisioner:"
	@echo "  test   Run provisioner unit tests"
	@echo "  lint   Run ruff checks"
	@echo "  tui    Launch interactive Textual provisioner TUI"
	@echo "  cli    Launch CLI tool"
	@echo "  clean  Clean cache and build artifacts"

test: ## Run provisioner unit tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Run ruff checks
	$(PYTHON) -m ruff check src/ tests/

tui: ## Launch interactive Textual provisioner TUI
	$(PYTHON) -m sdm_provisioner.tui.tui_main

cli: ## Launch CLI tool
	$(PYTHON) -m sdm_provisioner.main

clean: ## Clean cache and build artifacts
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'build', 'dist') if pathlib.Path(p).exists()]"

