# Technical Architecture: Game Server Coin Administration Interface

**Sprint**: Game Server Coin Administration Interface  
**Author**: Morpheus (Tech Lead / Architect)  
**Date**: 2026-10-20  
**Status**: Stage 1 - Sprint Planning (Gate 2 Review)  

---

## 1. Context & Architectural Overview

The Global Heads or Tails flip game stores coin identities in SQLite `data/app.db` (`coins` table), mapping 14-character hex tag UIDs to coin names, outcomes (`heads` or `tails`), clans, and rarities.

While `sdm_provisioner` handles physical chip flashing, operators currently lack an administrative web interface to configure new coins, pair heads and tails UIDs, modify clan/rarity attributes, or correct coin metadata directly on the running game server.

This architecture introduces a native, zero-dependency administrative subsystem to `game_server`:
1. **Core Data Layer (`SqliteGameStateManager`)**: Aggregates, validates, pairs, and mutates coin records atomically in `data/app.db`.
2. **Security & Route Layer (`admin_routes.py`)**: Flask Blueprint providing token-guarded web endpoints (`/admin/coins`) and REST APIs (`/api/admin/coins`).
3. **Frontend Presentation Layer (`templates/admin_coins.html`)**: Responsive web view matching the game's established light/blue-gradient aesthetic (Courier New, `#f0f2f5` background, `#007BFF` gradient header, card containers, tomato accents).

---

## 2. Component Design & Interfaces

### 2.1 Database Layer (`SqliteGameStateManager`)

The `coins` table schema:
```sql
CREATE TABLE IF NOT EXISTS coins (
    uid TEXT PRIMARY KEY,
    coin_name TEXT NOT NULL,
    outcome TEXT DEFAULT '',
    clan TEXT DEFAULT '',
    rarity TEXT DEFAULT 'common',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### New Manager Methods:
1. `list_coins_admin() -> list[dict]`:
   - Aggregates records by `coin_name`.
   - Resolves `heads_uid` (row where `outcome = 'heads'`) and `tails_uid` (row where `outcome = 'tails'`).
   - Computes `is_complete: bool` (`bool(heads_uid and tails_uid)`).
   - Aggregates flip statistics from `scan_logs` for this coin (`total_flips`, `heads_flips`, `tails_flips`).
   - Returns list sorted alphabetically by `coin_name`.

2. `create_coin(coin_name: str, heads_uid: str, tails_uid: str, clan: str = "", rarity: str = "common") -> dict`:
   - Validates `coin_name` is non-empty, alphanumeric/hyphenated.
   - Validates `heads_uid` and `tails_uid` are 14-character uppercase hex strings.
   - Enforces `heads_uid != tails_uid`.
   - Checks that neither UID is already registered to another coin (raises `ValueError` on conflict).
   - In an atomic transaction, inserts both rows:
     - `INSERT INTO coins (uid, coin_name, outcome, clan, rarity) VALUES (?, ?, 'heads', ?, ?)`
     - `INSERT INTO coins (uid, coin_name, outcome, clan, rarity) VALUES (?, ?, 'tails', ?, ?)`

3. `update_coin(old_coin_name: str, new_coin_name: str, heads_uid: str, tails_uid: str, clan: str = "", rarity: str = "common") -> dict`:
   - Validates inputs.
   - Handles renaming if `new_coin_name != old_coin_name`.
   - Reassigns heads and tails UIDs cleanly within an atomic transaction.

4. `delete_coin(coin_name: str) -> bool`:
   - Deletes all rows from `coins` where `coin_name = ?`.
   - Leaves `scan_logs` intact for historical auditability.

---

### 2.2 Security & Authentication (`@require_admin_token`)

The admin interface requires authorization via `ADMIN_TOKEN`:
- Checked sequentially from:
  1. `X-Admin-Token` HTTP header (for API / curl requests).
  2. `admin_token` Cookie (for browser sessions).
  3. `token` Query string parameter (for direct URL access or bookmarking).
- Environment Variable: `ADMIN_TOKEN`
- Development Fallback: If `ADMIN_TOKEN` is unset in the environment, the server logs a warning and permits local development access (or checks for default `"dev-admin-secret"`).

---

### 2.3 Route Specification (`admin_routes.py`)

Registered with Blueprint `admin_bp`:

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/admin` | Yes | Redirects to `/admin/coins` |
| `GET` | `/admin/coins` | Yes | Renders `admin_coins.html` dashboard |
| `GET` | `/api/admin/coins` | Yes | Returns JSON list of all paired coins and summary stats |
| `GET` | `/api/admin/coins/<name>` | Yes | Returns JSON details for a specific coin |
| `POST` | `/api/admin/coins` | Yes | Creates new coin (accepts JSON or Form data) |
| `PUT` | `/api/admin/coins/<name>` | Yes | Updates existing coin |
| `POST` | `/admin/coins/<name>/update` | Yes | Web form update handler (redirects with flash) |
| `DELETE` | `/api/admin/coins/<name>` | Yes | Deletes coin definition |
| `POST` | `/admin/coins/<name>/delete` | Yes | Web form delete handler (redirects with flash) |

---

### 2.4 Presentation Layer (`templates/admin_coins.html`)

- **Typography & Aesthetics**:
  - Inherits the game's font stack (`'Courier New', monospace`).
  - Container width: 900px, responsive down to mobile viewports.
  - Header: Blue gradient banner with title `Flip Game Coin Registry & Admin` and back-link `[← Back to Game]`.
- **Top Summary Cards**:
  - Total Coins, Complete Coins, Incomplete Coins, Total Lifetime Flips.
- **Action Toolbar**:
  - Search filter input (filters table in real time via JavaScript).
  - "＋ Register New Coin" primary button (opens modal or expands creation card).
- **Coin Registry Table**:
  - Columns: Coin Name, Clan, Rarity, Heads Face (UID + status), Tails Face (UID + status), Total Flips, Actions.
  - Badges: Rarity color coding (common: grey, uncommon: green, rare: blue, epic: purple, legendary: gold).
  - Completeness indicator: Green `● Paired` badge when both heads and tails are set; amber `▲ Single Face` badge if incomplete.
  - Action buttons: `[Edit]` opens edit modal pre-filled with coin data; `[Delete]` triggers confirmation prompt.
- **Modals / Forms**:
  - Client-side validation for 14-hex character UIDs.
  - Dropdown for Twelve Clans (The Twelve Clans list from game) + Custom entry.
  - Toast/Alert banners for immediate feedback.

---

## 3. Rubric ARCH Verification

- **BOUND**: Clearly bounded to `game_server` admin routes, database layer, and templates. Zero changes to cryptographic engine or other packages.
- **FLOW**: Clear request and mutation flow with two-phase validation and atomic SQLite transactions.
- **FAIL**: Graceful error handling for duplicate UIDs, malformed hex values, missing fields, and unauthorized tokens.
- **USER**: Preserves exact UI aesthetic of the game (Courier New, `#007BFF` gradient, card containers), with mobile responsiveness and clear feedback.
- **DECS**: Leverages Decision 10 (SQLite `app.db` coin ownership) and aligns with zero new dependencies.
- **FEAS**: Direct implementation without complex ORMs or external packages.

Verdict: `rubric ARCH: BOUND=S FLOW=S FAIL=S USER=S DECS=S FEAS=S`
