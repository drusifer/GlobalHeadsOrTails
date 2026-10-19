.PHONY: help test lint run docker-build seed-secrets clean

IMAGE_NAME ?= localhost/tag-validator-service:latest
PORT ?= 8080
NAMESPACE ?= tag-secrets

help: ## Show available make targets
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

test: ## Run unit and integration tests
	pytest tests/ -v

lint: ## Run syntax and lint checks
	ruff check src/ tests/

run: ## Run service locally using Python WSGI server
	python -c "from tag_validator.api.app import create_app; from wsgiref.simple_server import make_server; app = create_app(); print('Running tag-validator-service on port $(PORT)...'); make_server('0.0.0.0', $(PORT), app).serve_forever()"

docker-build: ## Build container image
	docker build -t $(IMAGE_NAME) .

seed-secrets: ## Seed tag keys from CSV into k3s secrets (usage: make seed-secrets CSV=tag_keys.csv [NS=tag-secrets])
	@[ -n "$(CSV)" ] || { echo "Usage: make seed-secrets CSV=path/to/tag_keys.csv [NS=tag-secrets]"; exit 1; }
	python -m tag_validator.cli.importer "$(CSV)" --backend k3s --namespace $(NAMESPACE)

clean: ## Clean cache and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache build dist *.egg-info
