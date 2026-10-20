# Sprint Backlog: Game Server Coin Administration Interface

**Sprint Name**: Game Server Coin Administration Interface  
**Owner**: Cypher (Product Manager)  
**Date**: 2026-10-20  
**Status**: Stage 1 - Sprint Planning (Gate 1 Review)  

---

## 1. Executive Summary & Objective

Provide a dedicated administration interface on the `game_server` to view, set up new coins, and modify existing coin metadata (name, clan, rarity, heads/tails UID assignments) in the flip game SQLite database (`data/app.db`).

Per user architectural clarifications:
1. **Security & Authentication**: Protected via an environment-configured token (`ADMIN_TOKEN`), checked via HTTP header, cookie, or query parameter, defaulting to developer mode when running locally.
2. **Metadata Focus**: Operates directly on coin game identities in SQLite `data/app.db` (`coins` table), assuming cryptographic keys are independently provisioned via `sdm_provisioner`.
3. **Tech Stack & Aesthetics**: Built as a native Flask Blueprint with zero extra package dependencies (maintaining raw SQLite with WAL mode, avoiding SQLAlchemy rewrite), styled to match the game's clean arcade design language (Courier New, `#f0f2f5` light background, `#007BFF` blue gradient header, card containers, tomato accents) and accompanied by a companion REST API.

---

## 2. User Stories & Acceptance Criteria

### US-ADMIN-001: Database Layer Coin Pairing & Administration Methods
**As a** game operator,  
**I want** `SqliteGameStateManager` to provide atomic coin administration and pairing helpers,  
**So that** the admin interface can reliably read, pair, create, update, and delete complete two-faced coin records.

#### Acceptance Criteria
- [ ] `SqliteGameStateManager` provides `list_coins_admin()` returning aggregated coin records grouped by `coin_name` with `heads_uid`, `tails_uid`, `clan`, `rarity`, `is_complete`, `created_at`, and total flip count.
- [ ] `SqliteGameStateManager` provides `create_coin(coin_name, heads_uid, tails_uid, clan, rarity)` validating UIDs (14-character hex strings), ensuring unique face assignment, and inserting/updating both face rows in `coins`.
- [ ] `SqliteGameStateManager` provides `update_coin(old_coin_name, new_coin_name, heads_uid, tails_uid, clan, rarity)` supporting safe renaming and face reassignment.
- [ ] `SqliteGameStateManager` provides `delete_coin(coin_name)` removing the coin's face records from `coins`.
- [ ] Validations reject malformed hex UIDs, empty coin names, and mismatched heads/tails UIDs (cannot assign the same UID to both heads and tails of a single coin).

---

### US-ADMIN-002: Flask Admin Security & REST API (`/api/admin/coins`)
**As a** system administrator or integration tool,  
**I want** secure JSON endpoints to query and mutate coin definitions,  
**So that** coin administration can be performed programmatically and power the web interface.

#### Acceptance Criteria
- [ ] Implement `@require_admin_token` decorator verifying `ADMIN_TOKEN` via `X-Admin-Token` header, `admin_token` cookie, or `?token=` parameter.
- [ ] When `ADMIN_TOKEN` is unset in local/dev environments, permits access with an audible warning log.
- [ ] `GET /api/admin/coins`: Returns JSON list of all registered coins and their completeness status.
- [ ] `GET /api/admin/coins/<coin_name>`: Returns specific coin details.
- [ ] `POST /api/admin/coins`: Validates payload and registers a new coin (returns 201 on success, 400 on validation error, 409 on conflict).
- [ ] `PUT /api/admin/coins/<coin_name>`: Updates metadata and face UIDs for an existing coin.
- [ ] `DELETE /api/admin/coins/<coin_name>`: Deletes coin identity records (returns 200 on success, 404 if not found).

---

### US-ADMIN-003: Web Admin Interface (`/admin/coins`)
**As a** game operator,  
**I want** an intuitive, responsive web dashboard on the game server,  
**So that** I can easily inspect, configure, and modify coins from any browser.

#### Acceptance Criteria
- [ ] Admin route `GET /admin` redirects to `GET /admin/coins`.
- [ ] Web view renders `templates/admin_coins.html`, matching the game's aesthetic (Courier New font, `#f0f2f5` background, `#007BFF` gradient banner, card containers, tomato accents).
- [ ] Header includes navigation link to return to the game (`/`) and displays server status.
- [ ] Summary cards display Total Coins, Complete Coins, Incomplete Coins, and Total Flips.
- [ ] Filter/search bar allows quick filtering of coins by name, clan, or UID.
- [ ] "Create New Coin" form/modal with fields:
  - Coin Name (e.g. `TWIN-STARS`)
  - Clan (dropdown of Twelve Clans + custom option)
  - Rarity (common, uncommon, rare, epic, legendary)
  - Heads Face UID (14 hex chars)
  - Tails Face UID (14 hex chars)
- [ ] Table of coins showing Coin Name, Clan badge, Rarity badge, Heads/Tails UIDs with status badges (e.g. green check for paired faces, warning if single-faced), flip count, and Edit/Delete action buttons.
- [ ] "Edit Coin" modal/form allowing modification of coin name, clan, rarity, heads UID, and tails UID.
- [ ] Delete action includes client-side confirmation dialog and triggers clean deletion.
- [ ] User feedback via flash alerts or toasts for successful creations, updates, deletions, and error messages.

---

### US-ADMIN-004: Test Suite & Workspace Regression
**As a** quality guardian,  
**I want** comprehensive automated test coverage for admin endpoints and database methods,  
**So that** the coin administration interface is proven reliable with zero regressions.

#### Acceptance Criteria
- [ ] Create `game_server/tests/test_admin_coins.py` covering:
  - Unit tests for all new `SqliteGameStateManager` methods (`list_coins_admin`, `create_coin`, `update_coin`, `delete_coin`, input validation).
  - Security tests verifying token protection, valid tokens, invalid tokens, and dev-mode fallback.
  - Integration tests for REST API endpoints (`GET`, `POST`, `PUT`, `DELETE`).
  - Integration tests for web interface GET `/admin/coins` and form submissions.
