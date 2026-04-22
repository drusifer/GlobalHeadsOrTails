# Coin Naming Architecture Enhancement
**Author**: Morpheus (Tech Lead)
**Date**: 2026-01-27
**Status**: Proposed → Awaiting Neo Implementation

---

## Problem Statement

**Current Gap**: The system tracks individual tags but has no concept of a "coin" as a logical unit. Each physical coin contains 2 NFC tags (heads and tails), but there's no way to:
1. Associate the two UIDs together as belonging to the same coin
2. Query "what are both sides of coin X?"
3. Validate that a coin has both heads AND tails provisioned
4. Prevent accidentally provisioning two HEADS tags for the same coin
5. Track coin inventory (as opposed to tag inventory)

**Business Impact**: Production operations cannot track coins properly, leading to:
- Risk of provisioning incomplete coins (only one side)
- No way to audit coin completion status
- Cannot identify which tags belong together
- Difficult to manage coin inventory vs tag inventory

---

## Architectural Design

### Core Concept: Coin as Logical Entity

```
Coin (Logical)
  ├─ coin_name: str (unique identifier, e.g., "COIN_001", "ALPHA_42")
  ├─ heads_tag: TagKeys (UID + keys + outcome=HEADS)
  └─ tails_tag: TagKeys (UID + keys + outcome=TAILS)
```

### Schema Enhancement

**Add to `TagKeys` dataclass** (csv_key_manager.py):
```python
@dataclass
class TagKeys:
    uid: UID
    picc_master_key: str
    app_read_key: str
    sdm_mac_key: str
    outcome: Outcome  # HEADS | TAILS | INVALID
    coin_name: str  # NEW: "COIN_001", "ALPHA_42", etc.
    provisioned_date: str
    status: str
    notes: str = ""
    last_used_date: str = ""
```

**CSV Format** (backwards compatible):
```csv
uid,picc_master_key,app_read_key,sdm_mac_key,outcome,coin_name,provisioned_date,status,notes,last_used_date
04AE664A2F7080,abc123...,def456...,ghi789...,heads,COIN_001,2026-01-27T10:00:00,provisioned,"",2026-01-27T10:05:00
04AE664A2F7081,abc124...,def457...,ghi790...,tails,COIN_001,2026-01-27T10:01:00,provisioned,"",2026-01-27T10:06:00
04AE664A2F7082,abc125...,def458...,ghi791...,heads,COIN_002,2026-01-27T10:02:00,provisioned,"",""
```

**Migration Strategy**: Existing tags with missing `coin_name` default to empty string `""`, allowing gradual migration.

---

## API Design

### CsvKeyManager Enhancements

#### 1. Coin Retrieval
```python
def get_coin_tags(self, coin_name: str) -> dict[str, TagKeys | None]:
    """Get both tags for a coin.

    Returns:
        dict with keys 'heads' and 'tails', values are TagKeys or None if missing

    Example:
        {'heads': TagKeys(...), 'tails': TagKeys(...)}
        {'heads': TagKeys(...), 'tails': None}  # Incomplete coin
    """
```

#### 2. Coin Validation
```python
def validate_coin(self, coin_name: str) -> dict:
    """Validate coin completeness.

    Returns:
        {
            'complete': bool,  # True if both heads and tails exist
            'heads': TagKeys | None,
            'tails': TagKeys | None,
            'issues': list[str]  # ["Missing tails tag", "Heads tag not provisioned"]
        }
    """
```

#### 3. Coin Listing
```python
def list_coins(self) -> dict[str, dict]:
    """List all coins and their status.

    Returns:
        {
            'COIN_001': {'complete': True, 'heads_uid': '...', 'tails_uid': '...'},
            'COIN_002': {'complete': False, 'heads_uid': '...', 'tails_uid': None},
            '': {'complete': False, 'heads_uid': '...', 'tails_uid': None}  # Unnamed tags
        }
    """
```

#### 4. Coin Assignment
```python
def assign_coin_name(self, uid: UID, coin_name: str, outcome: Outcome):
    """Assign a coin name and outcome to a tag.

    Validates:
    - coin_name is not empty
    - outcome is HEADS or TAILS (not INVALID)
    - No duplicate outcome for the same coin_name

    Raises:
        ValueError: If validation fails
    """
```

---

## Validation Rules

### Rule 1: Coin Uniqueness
- Each coin_name must have **at most one** HEADS tag
- Each coin_name must have **at most one** TAILS tag
- A coin_name can have 0, 1, or 2 tags (allows partial provisioning)

### Rule 2: Outcome Enforcement
- Tags with `coin_name != ""` must have `outcome = HEADS | TAILS`
- Tags with `outcome = INVALID` must have `coin_name = ""`
- No duplicate outcomes per coin

### Rule 3: Backwards Compatibility
- Existing tags with missing `coin_name` field are treated as `coin_name = ""`
- Empty coin_name means "unassigned" (no validation)

---

## TUI Integration Points

### Screen: Provision Tag
**Enhancement**: Before provisioning, prompt for coin_name and outcome:
```
╭─ Provision Tag ──────────────────╮
│ UID: 04AE664A2F7080             │
│                                  │
│ Coin Name: [COIN_001______]     │
│ Outcome:   [●] Heads  [ ] Tails │
│                                  │
│ [Provision] [Cancel]             │
╰──────────────────────────────────╯
```

### Screen: Coin Status (NEW)
**Purpose**: Show coin-level inventory
```
╭─ Coin Status ────────────────────────╮
│ COIN_001 ✓ Complete                 │
│   Heads: 04AE664A2F7080 ✓           │
│   Tails: 04AE664A2F7081 ✓           │
│                                      │
│ COIN_002 ⚠ Incomplete                │
│   Heads: 04AE664A2F7082 ✓           │
│   Tails: [Missing]                   │
│                                      │
│ Unassigned Tags: 3                   │
╰──────────────────────────────────────╯
```

### Screen: Tag Status
**Enhancement**: Display coin association
```
╭─ Tag Status ─────────────────────╮
│ UID: 04AE664A2F7080             │
│ Coin: COIN_001 (Heads)           │
│ Status: Provisioned              │
│ Partner: 04AE664A2F7081 (Tails) │
╰──────────────────────────────────╯
```

---

## Implementation Plan for Neo

### Phase 1: Schema & Core API (2 hours)
**File**: `csv_key_manager.py`

1. **Add `coin_name` field to `TagKeys`**
   - Default value: `""` (empty string for backwards compat)
   - Update `__str__()` method to display coin_name
   - Update `from_factory_keys()` to set coin_name = ""

2. **Update CSV FIELDNAMES**
   - Add `"coin_name"` to FIELDNAMES list
   - Verify CSV read/write handles missing column gracefully

3. **Implement `assign_coin_name()`**
   - Validation logic (duplicate outcome check)
   - Update tag and save

4. **Implement `get_coin_tags()`**
   - Query by coin_name
   - Return dict with heads/tails

5. **Implement `validate_coin()`**
   - Check completeness
   - Return validation result

6. **Implement `list_coins()`**
   - Group tags by coin_name
   - Return coin inventory

**Characterization Tests**: `tests/test_coin_naming.py`
```python
def test_assign_coin_name_valid()
def test_assign_coin_name_duplicate_outcome_raises()
def test_get_coin_tags_complete()
def test_get_coin_tags_incomplete()
def test_validate_coin_complete()
def test_validate_coin_incomplete()
def test_list_coins_summary()
def test_backwards_compatibility_missing_coin_name()
```

### Phase 2: TUI Integration (1.5 hours)
**Files**: `tui/screens/provision.py`, `tui/screens/tag_status.py`

1. **Provision Screen Enhancement**
   - Add coin_name input field
   - Add outcome radio buttons (Heads/Tails)
   - Call `assign_coin_name()` after provisioning success
   - Use a random name generatory library for default and unique coin_names

2. **Tag Status Screen Enhancement**
   - Display coin_name and outcome
   - Show partner tag UID (other side of coin)

3. **New Screen: Coin Inventory** (optional, future)
   - `tui/screens/coin_inventory.py`
   - Display `list_coins()` output
   - Navigate to tag details

### Phase 3: Validation & Testing (1 hour)
1. **Run ruff check** (mandatory)
2. **Run pytest** (all tests must pass)
3. **Manual TUI testing**:
   - Provision COIN_001 heads
   - Provision COIN_001 tails
   - Verify coin shows as complete
   - Try to provision COIN_001 heads again (should warn)

---

## Quality Gates

- [ ] `ruff check` passes (zero errors)
- [ ] All existing tests pass (no regressions)
- [ ] New tests pass (11+ characterization tests)
- [ ] CSV backwards compatible (existing files load without error)
- [ ] TUI displays coin_name correctly
- [ ] Duplicate outcome validation works

---

## Trade-offs & Risks

### ✅ Pros
- Clear coin-level inventory tracking
- Prevents incomplete coin provisioning
- Enables coin-centric operations (e.g., "reset coin COIN_001")
- Simple schema extension (one field)
- Backwards compatible

### ⚠️ Cons
- Requires user to enter coin name manually (extra step)
- Migration needed for existing tags (can be gradual)

### 🔍 Risks
- **Risk**: Users forget to assign coin names → Tags remain unassigned
  - **Mitigation**: High Quality Default names
  - **Mitigation**: TUI warns if provisioning without coin_name
  - **Mitigation**: Add "assign coin name" tool for retroactive assignment

- **Risk**: Typos in coin names (COIN_001 vs COIN_01) → Orphan tags
  - **Mitigation**: TUI autocomplete from existing coin names
  - **Mitigation**: `list_coins()` helps identify orphans

---

## Oracle Consultation

**@Oracle *ora ask**: Have we documented any coin tracking or pairing patterns?

**Answer** (from grep results):
- `Outcome` enum already exists (HEADS/TAILS/INVALID)
- No existing coin_name concept found
- Pattern follows existing UID-based tracking architecture

**@Oracle *ora record decision**: "Add coin_name field to TagKeys for coin-level tracking"

---

## Next Steps

1. **@Neo *swe impl**: Implement Phase 1 (Schema & API)
2. **@Trin *qa test**: Verify characterization tests pass
3. **@Neo *swe impl**: Implement Phase 2 (TUI Integration)
4. **@Trin *qa test**: Manual TUI testing
5. **@Oracle *ora record**: Document in ARCH.md after completion

---

**Status**: Ready for implementation
**Estimated Effort**: 4.5 hours total
**Priority**: High (production blocker per Drew)
