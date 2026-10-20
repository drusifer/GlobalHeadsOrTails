PYTHON ?= python3

.DEFAULT_GOAL := help

.PHONY: help chat
help: ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    \033[36m%-22s\033[0m %s\n", $$1, $$2}'

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

.PHONY: test-all test-shared test-tag-validator test-sdm-provisioner test-game-server test-art-generator install-all run-game-server run-tui run-tag-validator art-status art-generate art-review
test-all: ## Run full test suites across all packages and tools
	pytest shared/tests -v
	pytest tag_validator_service/tests -v
	pytest sdm_provisioner/tests -v
	pytest game_server/tests -v
	pytest tools/tests/test_art_generator.py -v

test-art-generator: ## Run test suite for generic art generator
	pytest tools/tests/test_art_generator.py -v

art-status: ## Show artwork status for a manifest (MANIFEST=path/to/manifest.yaml)
	$(PYTHON) tools/art_generator.py --manifest $(or $(MANIFEST),game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml) --status

art-generate: ## Generate artwork from YAML manifest (MANIFEST=path/to/manifest.yaml BACKEND=mock|cli)
	$(PYTHON) tools/art_generator.py --manifest $(or $(MANIFEST),game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml) --generate --backend $(or $(BACKEND),mock)

art-review: ## Build clean HTML review contact sheet from YAML manifest (MANIFEST=path/to/manifest.yaml)
	$(PYTHON) tools/art_generator.py --manifest $(or $(MANIFEST),game_server/src/game_server/sticker_catalog/twelve-clans/manifest.yaml) --review

test-shared: ## Run tests for shared contracts package
	pytest shared/tests -v

test-tag-validator: ## Run tests for tag_validator_service
	pytest tag_validator_service/tests -v

test-sdm-provisioner: ## Run tests for sdm_provisioner
	pytest sdm_provisioner/tests -v

test-game-server: ## Run tests for game_server
	pytest game_server/tests -v

install-all: ## Install all workspace packages in editable mode
	pip install -e shared -e tag_validator_service -e sdm_provisioner -e game_server

run-game-server: ## Run Flask game server
	$(PYTHON) -m game_server.app

run-tui: ## Run Textual SDM Provisioner TUI
	$(PYTHON) -m sdm_provisioner.tui.tui_main

run-tag-validator: ## Run Tag Validator Service locally
	$(MAKE) -C tag_validator_service run

clean: ## Clean cache and build artifacts across all packages
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.py[co]')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', 'build', 'dist') if pathlib.Path(p).exists()]"
