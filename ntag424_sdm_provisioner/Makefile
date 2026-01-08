# Makefile for ntag424_sdm_provisioner

# Configuration
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Adjust 'src/app.py' to your actual Flask entry point file
FLASK_APP := ntag424_sdm_provisioner.server.app

# Match project convention for centralized cache
export PYTHONPYCACHEPREFIX := $(CURDIR)/.cache/pycache

# Sentinel files to track state
VENV_ACTIVATE := $(VENV)/bin/activate
DEPS_MARKER := $(VENV)/.deps_updated

.PHONY: all clean build test run deps

all: clean test

# 1. Create venv only if activate script is missing
$(VENV_ACTIVATE):
	@echo "Setting up virtual environment..."
	python3 -m venv $(VENV) --system-site-packages
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	touch $(VENV_ACTIVATE)

clean:
	@echo "Cleaning artifacts..."
	rm -rf dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf $(PYTHONPYCACHEPREFIX)
	rm -rf .venv

# 2. Run pip install only if pyproject.toml is newer than the marker
$(DEPS_MARKER): pyproject.toml $(VENV_ACTIVATE)
	@echo "Installing/Updating dependencies..."
	$(PIP) install -e .[server]
	touch $(DEPS_MARKER)

deps: $(DEPS_MARKER)

build: deps
	@echo "Building distribution..."
	$(PYTHON) -m build

deps_test: deps
	@echo "Installing test dependencies..."
	$(PIP) install -e .[dev,test]

test: deps_test
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

run: deps
	@echo "Starting Flask app..."
	. $(VENV_ACTIVATE) && PYTHONPATH=$(CURDIR)/src FLASK_APP=$(FLASK_APP) $(PYTHON) -m flask run --host=0.0.0.0 --debug