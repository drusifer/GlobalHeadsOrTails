.PHONY: help test lint run pkg docker-build verify-container export-image seed-secrets clean

ifneq ("$(wildcard ../.venv/bin/python)","")
PYTHON ?= ../.venv/bin/python
else ifneq ("$(wildcard ../.venv/Scripts/python.exe)","")
PYTHON ?= ..\.venv\Scripts\python.exe
else ifneq ("$(wildcard ../ntag424_sdm_provisioner/.venv/bin/python)","")
PYTHON ?= ../ntag424_sdm_provisioner/.venv/bin/python
else
PYTHON ?= python3
endif

VERSION ?= latest
IMAGE_REPO ?= localhost/tag-validator-service
IMAGE_NAME ?= $(IMAGE_REPO):$(VERSION)
PORT ?= 8080
NAMESPACE ?= tag-secrets

export PYTHONPATH := src$(if $(PYTHONPATH),:$(PYTHONPATH))

help: ## Show available make targets
	@echo "Available targets:"
	@echo "  test              Run unit and integration tests"
	@echo "  lint              Run syntax and lint checks"
	@echo "  run               Run service locally using Python WSGI server"
	@echo "  docker-build      Build standalone container image"
	@echo "  pkg               Alias for docker-build"
	@echo "  verify-container  Verify container dependencies"
	@echo "  export-image      Build, verify, and export container image tarball"
	@echo "  seed-secrets      Seed tag keys from CSV into k3s secrets"
	@echo "  clean             Clean cache and build artifacts"

test: ## Run unit and integration tests
	$(PYTHON) -m pytest tests/ -v

lint: ## Run syntax and lint checks
	$(PYTHON) -m ruff check src/ tests/

run: ## Run service locally using Python WSGI server
	$(PYTHON) -m tag_validator.api.app --host 0.0.0.0 --port $(PORT)

docker-build: ## Build standalone container image
	docker build -t tag-validator-service -t $(IMAGE_NAME) .

pkg: docker-build ## Alias for docker-build (consistent with pi-patch packaging workflow)

verify-container: ## Verify dependency graph, CLI check, and Gunicorn WSGI boot inside read-only container
	@echo "Verifying tag-validator-service container dependencies and Gunicorn WSGI boot..."
	docker run --rm --network none --read-only --tmpfs /tmp \
		--entrypoint sh $(IMAGE_NAME) \
		-c 'pip check && tag-validator --check --backend memory && gunicorn --check-config --bind 0.0.0.0:8080 --worker-tmp-dir /tmp "tag_validator.api.app:create_app()"'

export-image: pkg verify-container ## Build, verify, and export container image tarball for pi-patch
	@echo "Tagging image for k3s / pi-patch import..."
	docker tag $(IMAGE_NAME) $(IMAGE_REPO):$(VERSION)
	@echo "Exporting image tarball..."
	@mkdir -p dist
	@rm -f dist/tag-validator-service-$(VERSION).tar
	docker save $(IMAGE_REPO):$(VERSION) -o dist/tag-validator-service-$(VERSION).tar
	@echo "Image exported -> dist/tag-validator-service-$(VERSION).tar"

seed-secrets: ## Seed tag keys from CSV into k3s secrets (usage: make seed-secrets CSV=tag_keys.csv [NS=tag-secrets])
	@[ -n "$(CSV)" ] || { echo "Usage: make seed-secrets CSV=path/to/tag_keys.csv [NS=tag-secrets]"; exit 1; }
	$(PYTHON) -m tag_validator.cli.importer "$(CSV)" --backend k3s --namespace $(NAMESPACE)

clean: ## Clean cache and build artifacts
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'build', 'dist') if pathlib.Path(p).exists()]"
