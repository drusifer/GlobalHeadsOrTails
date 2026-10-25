.PHONY: help install test lint run-server clean

ifneq ("$(wildcard ../.venv/bin/python)","")
PYTHON ?= ../.venv/bin/python
else ifneq ("$(wildcard ../.venv/Scripts/python.exe)","")
PYTHON ?= ..\.venv\Scripts\python.exe
else
PYTHON ?= python
endif

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
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'build', 'dist') if pathlib.Path(p).exists()]"
