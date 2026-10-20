.PHONY: help test lint tui cli clean

PYTHON ?= python3

help: ## Show available make targets
	@echo "Available targets for sdm_provisioner:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

test: ## Run provisioner unit tests
	pytest tests/ -v

lint: ## Run ruff checks
	ruff check src/ tests/

tui: ## Launch interactive Textual provisioner TUI
	$(PYTHON) -m sdm_provisioner.tui.tui_main

cli: ## Launch CLI tool
	$(PYTHON) -m sdm_provisioner.main

clean: ## Clean cache and build artifacts
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'build', 'dist') if pathlib.Path(p).exists()]"
