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

.PHONY: all clean dist pkg test run deps_test test_server deps docker-run uninstall logs pull-db

all: clean test

# 1. Create venv only if activate script is missing
$(VENV_ACTIVATE):
	@echo "Setting up virtual environment..."
	python3 -m venv $(VENV) --system-site-packages
	@echo "Installing dependencies..."
	$(PIP) install --upgrade pip setuptools wheel build
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

dist: deps
	@echo "Building distribution..."
	$(PYTHON) -m build

deps_test: deps $(DEPS_MARKER)
	@echo "Installing test dependencies..."
	$(PIP) install -e .[dev,test]
	touch $(DEPS_MARKER)


test_server: deps_test
	@echo "Running server tests..."
	$(PYTHON) -m pytest tests/*_server*.py -v

test: deps_test
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

run: deps
	@echo "Starting Flask app..."
	. $(VENV_ACTIVATE) && env PYTHONPATH=$(CURDIR)/src FLASK_APP=$(FLASK_APP) flask run --host=0.0.0.0 --port=5001 --debug --cert=adhoc


pkg: dist
	@echo "Building Docker image..."
	sudo docker build -t ntag424-sdm-provisioner .

docker-run: pkg
	@mkdir -p data_prod
	@echo "Running Docker container..."
	sudo docker run -d \
		--name ntag424-sdm-provisioner \
		--restart always \
		-p 8000:8000 \
		--memory="512m" \
		--cpus="1.0" \
		--read-only \
		--tmpfs /tmp \
		-v $(CURDIR)/data_prod:/app/data \
		ntag424-sdm-provisioner

uninstall:
	@echo "Stopping and removing Docker container..."
	-sudo docker stop ntag424-sdm-provisioner
	-sudo docker rm ntag424-sdm-provisioner
	-sudo docker rmi ntag424-sdm-provisioner

logs:
	@echo "Fetching container logs..."
	sudo docker logs ntag424-sdm-provisioner
