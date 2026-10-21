ifneq ("$(wildcard .venv/bin/python)","")
PYTHON ?= .venv/bin/python
else ifneq ("$(wildcard ntag424_sdm_provisioner/.venv/bin/python)","")
PYTHON ?= ntag424_sdm_provisioner/.venv/bin/python
else
PYTHON ?= python3
endif

VERSION ?= latest
export PYTHONPATH := $(CURDIR)/shared/src:$(CURDIR)/tag_validator_service/src:$(CURDIR)/sdm_provisioner/src:$(CURDIR)/game_server/src$(if $(PYTHONPATH),:$(PYTHONPATH))

.DEFAULT_GOAL := help

.PHONY: help chat
help: ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-30s\033[0m %s\n", $$1, $$2}'

chat: ## Post a message to CHAT.md (usage: make chat MSG="<msg>" [PERSONA="<name>"] [CMD="<cmd>"] [TO="<recipient>"])
	@[ -n "$(MSG)" ] || { echo "Usage: make chat MSG=\"<message>\" [PERSONA=\"<name>\"] [CMD=\"<cmd>\"] [TO=\"<recipient>\"]"; exit 1; }
	@$(PYTHON) agents/tools/chat.py "$(MSG)" \
		$(if $(PERSONA),--persona "$(PERSONA)") \
		$(if $(CMD),--cmd "$(CMD)") \
		$(if $(TO),--to "$(TO)")

.PHONY: rangers-roster-audit
rangers-roster-audit: ## Snapshot and reconcile complete official NHL Rangers player stats
	$(PYTHON) tools/rangers_roster_audit.py

.PHONY: sticker-art-gallery
sticker-art-gallery: ## Browse clan artwork (HOST=0.0.0.0 PORT=8765)
	$(PYTHON) tools/sticker_gallery.py --host $(or $(HOST),0.0.0.0) --port $(or $(PORT),8765)

.PHONY: test-sticker-gallery
test-sticker-gallery: ## Check Rangers gallery search/pagination and actual-art access in mobile Chromium
	STICKER_PACK=rangers-history $(PYTHON) tools/check_sticker_gallery.py

.PHONY: rangers-roster-seasons
rangers-roster-seasons: ## Audit first/last NYR seasons against the frozen roster
	$(PYTHON) tools/rangers_roster_audit.py --seasons

.PHONY: rangers-catalog
rangers-catalog: ## Build full Rangers catalog from frozen NHL snapshot
	$(PYTHON) tools/rangers_catalog.py

.PHONY: test-all test-shared test-tag-validator test-sdm-provisioner test-game-server install-all run-game-server run-tui run-tag-validator pkg-tag-validator verify-tag-validator-container export-tag-validator-image install-art art-status art-generate art-pack art-review art-verify
test-all: ## Run full test suites across all packages and tools
	$(PYTHON) -m pytest shared/tests -v
	$(PYTHON) -m pytest tag_validator_service/tests -v
	$(PYTHON) -m pytest sdm_provisioner/tests -v
	$(PYTHON) -m pytest game_server/tests -v

# Sticker art is made with artai, pip-installed (editable) from a sibling checkout
# (ARTAI_SRC, default ../artai) into its own .venv-art so the workspace .venv and
# every other target are unaffected. MANIFEST defaults to the Twelve Clans set.
ARTAI_SRC ?= ../artai
ARTAI     := .venv-art/bin/artai
ART_MANIFEST = $(or $(MANIFEST),game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml)

install-art: ## pip-install artai (../artai or ARTAI_SRC=) into .venv-art
	@test -d "$(ARTAI_SRC)" || { echo "artai not found at $(ARTAI_SRC) - clone it there or run: make install-art ARTAI_SRC=<path>"; exit 1; }
	test -x .venv-art/bin/python || python3 -m venv .venv-art
	.venv-art/bin/pip install -q -e "$(ARTAI_SRC)"

art-status: install-art ## Show artwork status for a manifest (MANIFEST=path/to/manifest.yaml)
	$(ARTAI) status $(ART_MANIFEST)

art-generate: install-art ## Paint stickers with no art yet, then pack (BACKEND= required; FORCE=1 redoes existing)
	$(ARTAI) generate $(ART_MANIFEST) $(if $(BACKEND),--backend $(BACKEND)) $(if $(FORCE),--force) $(ARGS)
	$(if $(filter mock,$(BACKEND)),@echo "BACKEND=mock: placeholder masters are not packed into the shipped output_dir",$(ARTAI) pack $(ART_MANIFEST) $(if $(FORCE),--force))

art-pack: install-art ## Pack new/changed masters into the manifest's output_dir (MANIFEST=... FORCE=1 rewrites all)
	$(ARTAI) pack $(ART_MANIFEST) $(if $(FORCE),--force)

art-review: install-art ## Build the HTML review contact sheet (MANIFEST=...)
	$(ARTAI) review $(ART_MANIFEST)

art-verify: install-art ## Check every sticker exists, fits and is real art (MANIFEST=...)
	$(ARTAI) verify $(ART_MANIFEST)

test-shared: ## Run tests for shared contracts package
	$(PYTHON) -m pytest shared/tests -v

test-tag-validator: ## Run tests for tag_validator_service
	$(PYTHON) -m pytest tag_validator_service/tests -v

test-sdm-provisioner: ## Run tests for sdm_provisioner
	$(PYTHON) -m pytest sdm_provisioner/tests -v

test-game-server: ## Run tests for game_server
	$(PYTHON) -m pytest game_server/tests -v

install-all: ## Install all workspace packages in editable mode
	pipx install -e shared -e tag_validator_service -e sdm_provisioner -e game_server

run-game-server: ## Run Flask game server
	$(PYTHON) -m game_server.app

run-tui: ## Run Textual SDM Provisioner TUI
	$(PYTHON) -m sdm_provisioner.tui.tui_main

run-tag-validator: ## Run Tag Validator Service locally
	$(MAKE) -C tag_validator_service run

pkg-tag-validator: ## Build standalone container image for tag_validator_service
	$(MAKE) -C tag_validator_service pkg VERSION=$(VERSION)

verify-tag-validator-container: ## Verify tag_validator_service container dependencies and Gunicorn WSGI boot
	$(MAKE) -C tag_validator_service verify-container VERSION=$(VERSION)

export-tag-validator-image: ## Build, verify, and export tag_validator_service container tarball for pi-patch
	$(MAKE) -C tag_validator_service export-image VERSION=$(VERSION)
	@mkdir -p dist
	@cp -f tag_validator_service/dist/tag-validator-service-$(VERSION).tar dist/tag-validator-service-$(VERSION).tar
	@echo "Artifact ready for pi-patch -> dist/tag-validator-service-$(VERSION).tar"

clean: ## Clean cache and build artifacts across all packages
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'build', 'dist') if pathlib.Path(p).exists()]"
