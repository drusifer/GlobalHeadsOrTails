# Runner Refactor Plan - Centralized I/O

## Goal

Separate concerns: Tools handle business logic, Runner handles all user interaction.

## Current Problems

1. **Tools print directly** - Hard to test, can't capture output
2. **Tools ask for input** - Breaks non-interactive mode, inconsistent UX
3. **Mixed concerns** - Business logic tangled with I/O
4. **Hard to mock** - Can't test without actual console I/O
5. **Inconsistent formatting** - Each tool formats output differently

## Proposed Architecture

### Tool Responsibilities (Business Logic Only)
- Execute operations on tag
- Return structured results (dataclasses)
- Raise exceptions on errors
- NO printing, NO input()

### Runner Responsibilities (I/O Only)
- Display menus and prompts
- Collect user input
- Display tool results
- Format output consistently
- Handle errors and display messages

---

## Design Changes

### 1. Tool Base Protocol

**Current:**
```python
class Tool(Protocol):
    name: str
    description: str
    
    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        ...
    
    def execute(self, tag_state: TagState, card: NTag424CardConnection, 
                key_mgr: CsvKeyManager) -> bool:
        # Prints stuff
        # Asks for input
        return True/False
```

**Proposed:**
```python
@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    
    # Optional: Structured data for specific tools
    sdm_config: Optional[SDMConfiguration] = None
    ndef_data: Optional[bytes] = None
    diagnostics: Optional[dict] = None

@dataclass
class ConfirmationRequest:
    """Request for user confirmation before executing tool."""
    title: str
    description: str
    items: list[str]  # List of actions to confirm
    default_yes: bool = False

class Tool(Protocol):
    name: str
    description: str
    
    def is_available(self, tag_state: TagState) -> bool | tuple[bool, str]:
        ...
    
    def get_confirmation_request(self, tag_state: TagState) -> Optional[ConfirmationRequest]:
        """
        Get confirmation details if tool needs user confirmation.
        
        Returns:
            ConfirmationRequest if confirmation needed, None otherwise
        """
        ...
    
    def execute(self, tag_state: TagState, card: NTag424CardConnection, 
                key_mgr: CsvKeyManager) -> ToolResult:
        """
        Execute tool logic - NO I/O!
        
        Returns:
            ToolResult with success status, message, and optional details
            
        Raises:
            Exception on error (runner will catch and display)
        """
        ...
```

---

## 2. Runner Flow

### Current Flow:
```
Runner:
  1. Show menu
  2. Get user selection
  3. Call tool.execute()
  4. Tool prints/asks for input internally
  5. Tool returns True/False
```

### Proposed Flow:
```
Runner:
  1. Show menu (runner displays tool.name, tool.description)
  2. Get user selection
  3. Check tool.is_available()
  4. Get confirmation_request = tool.get_confirmation_request()
  5. If confirmation needed:
     - Display confirmation dialog
     - Get user input (y/n)
     - If declined, return to menu
  6. Call result = tool.execute()  # NO I/O inside!
  7. Display result:
     - Show result.message
     - Format and show result.details
     - If error, show troubleshooting
```

---

## 3. Migration Strategy

### Phase 1: Add New Interfaces (Non-Breaking)
- [ ] Add `ToolResult` dataclass to `base.py`
- [ ] Add `ConfirmationRequest` dataclass to `base.py`
- [ ] Add `get_confirmation_request()` method to `Tool` protocol (optional)
- [ ] Update `execute()` signature to return `ToolResult` (breaking change)

### Phase 2: Create Output Formatters
- [ ] Add `ResultFormatter` class to runner
- [ ] Implement formatters for common patterns:
  - `format_success_message(result: ToolResult)`
  - `format_error_message(exception: Exception)`
  - `format_diagnostics(details: dict)`
  - `format_table(rows: list[tuple])`

### Phase 3: Refactor Tools One by One
- [ ] **DiagnosticsTool** - Return structured dict instead of printing
- [ ] **ReadUrlTool** - Return URL data
- [ ] **UpdateUrlTool** - Return before/after URLs
- [ ] **ConfigureSdmTool** - Return SDMConfiguration
- [ ] **RestoreBackupTool** - Return restoration status
- [ ] **ReprovisionTool** - Return key change status
- [ ] **ProvisionFactoryTool** - Return provisioning data

### Phase 4: Update Runner
- [ ] Implement confirmation dialog handling
- [ ] Implement result display
- [ ] Remove direct tool printing
- [ ] Add consistent error handling

---

## 4. Example Refactoring - ConfigureSdmTool

### Before (Current):
```python
def execute(self, tag_state, card, key_mgr) -> bool:
    print("\n" + "="*70)
    print("Configure Secure Dynamic Messaging (SDM)")
    print("="*70)
    print(f"Tag: {uid_to_asset_tag(tag_state.uid)}")
    print()
    
    # Read current URL
    current_url = read_current_url(card)
    print(f"Current URL: {current_url[:80]}...")
    
    # Show what will be configured
    print()
    print("SDM will be configured with:")
    print("  Base URL: ...")
    
    # Ask for confirmation
    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Cancelled.")
        return False
    
    try:
        # Do the work
        with AuthenticatedConnection(...) as auth_conn:
            sdm_config = configure_sdm_with_offsets(auth_conn, template)
            print("  [OK] SDM configured")
            
        print("\n[SUCCESS] SDM Configuration Complete!")
        return True
        
    except Exception as e:
        print(f"[FAILED] {e}")
        return False
```

### After (Proposed):
```python
def get_confirmation_request(self, tag_state: TagState) -> Optional[ConfirmationRequest]:
    """Get confirmation before configuring SDM."""
    return ConfirmationRequest(
        title="Configure Secure Dynamic Messaging (SDM)",
        description=f"Tag: {uid_to_asset_tag(tag_state.uid)}",
        items=[
            "Authenticate with PICC Master Key",
            "Configure file settings for SDM",
            "Write NDEF with SDM placeholders"
        ],
        default_yes=False
    )

def execute(self, tag_state, card, key_mgr) -> ToolResult:
    """Execute SDM configuration - NO I/O!"""
    # Build template
    template = build_sdm_url_template(self.base_url)
    url_template = template.build_url()
    
    # Authenticate and configure
    with AuthenticatedConnection(
        card, 
        key_mgr.get_tag_keys(tag_state.uid).picc_master_key, 
        0x00
    ) as auth_conn:
        sdm_config = configure_sdm_with_offsets(auth_conn, template)
    
    # Write NDEF
    ndef_record = build_ndef_uri_record(url_template)
    card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
    card.send(WriteNdefMessage(ndef_record))
    
    # Update database
    key_mgr.update_notes(tag_state.uid, f"SDM configured: {self.base_url}")
    
    # Return structured result
    return ToolResult(
        success=True,
        message="SDM Configuration Complete!",
        details={
            'url_template': url_template,
            'uid_offset': sdm_config.offsets.uid_offset,
            'ctr_offset': sdm_config.offsets.read_ctr_offset,
            'cmac_offset': sdm_config.offsets.mac_offset,
        },
        sdm_config=sdm_config
    )
```

### Runner Handles Display:
```python
def _run_tool(self, tool: Tool, tag_state: TagState, card, key_mgr):
    """Run a tool with centralized I/O handling."""
    
    # Show tool header
    print("\n" + "="*70)
    print(f"Executing: {tool.name}")
    print("="*70)
    print()
    
    # Check if confirmation needed
    confirmation = tool.get_confirmation_request(tag_state)
    if confirmation:
        self._display_confirmation(confirmation)
        if not self._get_user_confirmation():
            print("Cancelled.")
            return False
    
    # Execute tool (no I/O inside!)
    try:
        result = tool.execute(tag_state, card, key_mgr)
        
        # Display result
        self._display_tool_result(result)
        
        return result.success
        
    except Exception as e:
        self._display_tool_error(tool.name, e)
        return False
```

---

## 5. Benefits

### For Tools
- ✅ Pure business logic - easy to test
- ✅ No I/O dependencies - can mock everything
- ✅ Consistent return values
- ✅ Reusable in other contexts (CLI, GUI, API)

### For Runner
- ✅ Centralized formatting - consistent UX
- ✅ Easy to add features (logging, JSON output, etc.)
- ✅ Better error handling
- ✅ Support --yes flag properly

### For Testing
- ✅ Can test tools without mocking print/input
- ✅ Can verify tool results programmatically
- ✅ Can test runner display separately from logic

### For Future Features
- ✅ Add JSON output mode for automation
- ✅ Add GUI wrapper around runner
- ✅ Add web API using same tools
- ✅ Generate reports from tool results

---

## 6. Implementation Order

### Step 1: Define New Types (Non-Breaking)
- Add `ToolResult` dataclass
- Add `ConfirmationRequest` dataclass
- Add `get_confirmation_request()` to Tool protocol (optional method)
- Keep old `execute()` signature for now

### Step 2: Create Result Formatter
- Add `ResultFormatter` class with display methods
- Implement common formatting patterns
- Test with mock results

### Step 3: Update Runner Infrastructure
- Add `_display_confirmation()` method
- Add `_get_user_confirmation()` method (checks --yes flag)
- Add `_display_tool_result()` method
- Add `_display_tool_error()` method
- Keep old flow working

### Step 4: Refactor One Tool (Proof of Concept)
- Pick simplest tool (ReadUrlTool)
- Implement new interface
- Remove all print/input from tool
- Runner displays results
- Test thoroughly

### Step 5: Refactor Remaining Tools
- DiagnosticsTool
- UpdateUrlTool
- ConfigureSdmTool (fix import error too!)
- RestoreBackupTool
- ReprovisionTool
- ProvisionFactoryTool

### Step 6: Cleanup
- Remove old compatibility code
- Update tests
- Update documentation

---

## 7. Open Questions

1. **Should tools log?** Or should runner collect log messages?
2. **Progress updates?** For long operations, how to show progress?
3. **Nested confirmations?** What if tool needs multiple confirmations?
4. **Structured vs free-form output?** Balance between structure and flexibility

---

## 8. Immediate Fix Needed

Before refactoring, fix the import error in `configure_sdm_tool.py`:

```python
# Current (WRONG):
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticatedConnection

# Should be:
from ntag424_sdm_provisioner.crypto.auth_session import AuthenticateEV2
```

Check where `AuthenticatedConnection` is actually defined!

---

**Status:** Plan created - ready for review
**Complexity:** Medium-High (touches all tools and runner)
**Time Estimate:** 2-3 hours
**Breaking Changes:** Yes (tool interface changes)

