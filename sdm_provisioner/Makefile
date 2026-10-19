.PHONY: help test lint tui cli clean

help: ## Show available make targets
	@echo "Available targets for sdm_provisioner:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

test: ## Run provisioner unit tests
	pytest tests/ -v

lint: ## Run ruff checks
	ruff check src/ tests/

tui: ## Launch interactive Textual provisioner TUI
	python -m sdm_provisioner.tui.tui_main

cli: ## Launch CLI tool
	python -m sdm_provisioner.main

clean: ## Clean cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache build dist *.egg-info
