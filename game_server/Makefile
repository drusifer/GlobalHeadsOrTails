.PHONY: help install test lint run-server clean

PYTHON ?= python

help:
	@echo "game_server targets:"
	@echo "  install     Install game_server in editable mode"
	@echo "  test        Run test suite"
	@echo "  lint        Run ruff linter"
	@echo "  run-server  Run Flask development server"
	@echo "  clean       Remove cache and build artifacts"

install:
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest tests -v

lint:
	$(PYTHON) -m ruff check src tests

run-server:
	$(PYTHON) -m game_server.app

clean:
	rm -rf build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
