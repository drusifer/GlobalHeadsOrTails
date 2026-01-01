# Sprint: Fix Authenticated NDEF Write (WriteData Command)

**Sprint Goal:** Replace ISOUpdateBinary (0xD6) with native WriteData (0x8D) for authenticated NDEF writes  
**Sprint Start:** 2025-12-02  
**Estimated Points:** 8  
**Priority:** P0 - Blocker for provisioning

---

## Background

The provisioning flow fails at NDEF write with `LENGTH_ERROR (0x917E)` because:
1. `ISOUpdateBinary (0xD6)` only supports `CommMode.Plain` (no MAC)
2. We're trying to add MAC to a command that doesn't support it
3. Native `WriteData (0x8D)` is the correct command for authenticated writes

See: `docs/analysis/NDEF_WRITE_SEQUENCE_SPEC.md`

---

## Sprint Tasks

### Epic 1: Create WriteDataAuth Command
**Owner:** Neo  
**Points:** 3

#### Task 1.1: Create WriteDataAuth class
**File:** `src/ntag424_sdm_provisioner/commands/write_data_auth.py`
**Status:** ⬜ Not Started

```python
# Expected implementation
class WriteDataAuth(AuthApduCommand):
    """
    Native WriteData (0x8D) with CommMode.MAC support.
    
    APDU Format:
    [90 8D 00 00 Lc] [FileNo] [Offset:3] [Length:3] [Data] [MAC:8] [00]
    """
    
    def __init__(self, file_no: int, offset: int, data: bytes):
        super().__init__(use_escape=True)
        self.file_no = file_no
        self.offset = offset  
        self.data = data
    
    def get_command_byte(self) -> int:
        return 0x8D  # WriteData INS
    
    def get_unencrypted_header(self) -> bytes:
        # FileNo + Offset (3 bytes LSB) + Length (3 bytes LSB)
        return bytes([
            self.file_no,
            self.offset & 0xFF,
            (self.offset >> 8) & 0xFF,
            (self.offset >> 16) & 0xFF,
            len(self.data) & 0xFF,
            (len(self.data) >> 8) & 0xFF,
            (len(self.data) >> 16) & 0xFF,
        ])
    
    def needs_encryption(self) -> bool:
        return False  # CommMode.MAC = plaintext + MAC
    
    def build_command_data(self) -> bytes:
        return self.data
    
    def parse_response(self, data: bytes) -> SuccessResponse:
        return SuccessResponse(f"WriteData OK ({len(self.data)} bytes)")
```

**Acceptance Criteria:**
- [ ] Implements `AuthApduCommand` interface
- [ ] Uses INS=0x8D (not 0xD6)
- [ ] Header includes FileNo, Offset (3 bytes), Length (3 bytes)
- [ ] Implements `Sequenceable` protocol for logging
- [ ] Has docstring with APDU format

---

#### Task 1.2: Add exports to commands/__init__.py
**File:** `src/ntag424_sdm_provisioner/commands/__init__.py`
**Status:** ⬜ Not Started

```python
from ntag424_sdm_provisioner.commands.write_data_auth import WriteDataAuth
```

**Acceptance Criteria:**
- [ ] `WriteDataAuth` importable from `commands` package

---

#### Task 1.3: Unit test WriteDataAuth command construction
**File:** `tests/test_write_data_auth.py`
**Status:** ⬜ Not Started

```python
def test_write_data_auth_command_byte():
    cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"test")
    assert cmd.get_command_byte() == 0x8D

def test_write_data_auth_header_format():
    cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"X" * 80)
    header = cmd.get_unencrypted_header()
    assert header == bytes([
        0x02,        # FileNo
        0x00, 0x00, 0x00,  # Offset LSB
        0x50, 0x00, 0x00,  # Length=80 LSB
    ])

def test_write_data_auth_no_encryption():
    cmd = WriteDataAuth(file_no=0x02, offset=0, data=b"test")
    assert cmd.needs_encryption() == False
```

**Acceptance Criteria:**
- [ ] Tests command byte is 0x8D
- [ ] Tests header format matches spec
- [ ] Tests `needs_encryption()` returns False for CommMode.MAC

---

### Epic 2: Update Provisioning Service
**Owner:** Neo  
**Points:** 2

#### Task 2.1: Update _write_ndef_authenticated method
**File:** `src/ntag424_sdm_provisioner/services/provisioning_service.py`
**Status:** ⬜ Not Started

**Before:**
```python
def _write_ndef_authenticated(self, auth_conn, ndef_message):
    self.card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
    auth_conn.send(WriteNdefMessageAuth(ndef_data=ndef_message))
    self.card.send(SelectPiccApplication())
```

**After:**
```python
def _write_ndef_authenticated(self, auth_conn, ndef_message):
    # WriteData directly addresses file by number, no need to select first
    auth_conn.send(WriteDataAuth(
        file_no=0x02,      # NDEF file
        offset=0,          # Start of file
        data=ndef_message
    ))
```

**Acceptance Criteria:**
- [ ] Uses `WriteDataAuth` instead of `WriteNdefMessageAuth`
- [ ] Removes unnecessary `ISOSelectFile` (WriteData addresses file by number)
- [ ] Import updated

---

#### Task 2.2: Remove deprecated WriteNdefMessageAuth usage
**File:** Multiple
**Status:** ⬜ Not Started

Search for any other usages of `WriteNdefMessageAuth` and update:
```bash
grep -r "WriteNdefMessageAuth" src/
```

**Acceptance Criteria:**
- [ ] No remaining usages of `WriteNdefMessageAuth` in production code
- [ ] Consider deprecating the class with warning

---

### Epic 3: Simulator Validation (Trin)
**Owner:** Trin  
**Points:** 3

#### Task 3.1: Add WriteData (0x8D) handler to simulator
**File:** `tests/seritag_simulator.py`
**Status:** ⬜ Not Started

```python
def _handle_write_data(self, data: bytes) -> tuple[bytes, int, int]:
    """Handle WriteData (0x8D) command."""
    if len(data) < 7:
        return b"", 0x91, 0x7E  # LENGTH_ERROR
    
    file_no = data[0]
    offset = data[1] | (data[2] << 8) | (data[3] << 16)
    length = data[4] | (data[5] << 8) | (data[6] << 16)
    payload = data[7:7+length]
    
    if file_no not in self.files:
        return b"", 0x91, 0xF0  # FILE_NOT_FOUND
    
    # Verify MAC if authenticated
    if self.authenticated:
        # MAC is last 8 bytes
        mac = data[-8:]
        data_without_mac = data[:-8]
        # TODO: Verify MAC
    
    # Write to simulated file
    self.files[file_no][offset:offset+length] = payload
    
    return b"", 0x91, 0x00  # OK
```

**Acceptance Criteria:**
- [ ] Simulator handles WriteData (0x8D)
- [ ] Validates file number
- [ ] Validates offset/length boundaries
- [ ] Verifies MAC in authenticated mode

---

#### Task 3.2: Create sequence validation test
**File:** `tests/test_provision_sequence.py`
**Status:** ⬜ Not Started

```python
def test_ndef_write_uses_writedata_command():
    """Verify NDEF write uses WriteData (0x8D) not ISOUpdateBinary (0xD6)."""
    # Setup
    simulator = SeritagCardSimulator()
    seq = start_sequence("NDEF Write Test")
    
    with CardManager(simulator) as card:
        card.set_sequence_logger(seq)
        key_mgr = MockKeyManager()
        service = ProvisioningService(card, key_mgr)
        
        # Execute
        service._write_ndef_authenticated(
            auth_conn=...,  # Mock authenticated connection
            ndef_message=b"test NDEF data"
        )
    
    # Validate sequence
    steps = seq.get_steps()
    write_step = [s for s in steps if "WriteData" in s.command_name][0]
    
    # Should use WriteData (0x8D), not ISOUpdateBinary (0xD6)
    assert write_step.command_bytes[1] == 0x8D
    assert write_step.status_word == (0x91, 0x00)
```

**Acceptance Criteria:**
- [ ] Test verifies INS byte is 0x8D
- [ ] Test runs in headless mode (no hardware)
- [ ] Test captures and validates sequence diagram
- [ ] Test fails if ISOUpdateBinary (0xD6) is used

---

#### Task 3.3: Create expected sequence diagram test
**File:** `tests/test_provision_sequence.py`
**Status:** ⬜ Not Started

```python
EXPECTED_NDEF_WRITE_SEQUENCE = [
    ("SelectPiccApplication", 0x9000),
    ("GetChipVersion", 0x9100),
    ("AuthenticateEV2First", 0x91AF),
    ("AuthenticateEV2First Part2", 0x9100),
    ("WriteData", 0x9100),  # <-- Must be WriteData, not ISOUpdateBinary
    ("ChangeFileSettings", 0x9100),
]

def test_provision_sequence_matches_expected():
    """Validate full provisioning sequence matches spec."""
    # ... test implementation
```

**Acceptance Criteria:**
- [ ] Expected sequence defined as constant
- [ ] Test validates each step in order
- [ ] Test validates status words
- [ ] Test output includes sequence diagram on failure

---

### Epic 4: Integration Testing
**Owner:** Neo + Trin  
**Points:** 2

#### Task 4.1: Run full provisioning with simulator
**Status:** ⬜ Not Started

```bash
# Run provision sequence test
python -m pytest tests/test_provision_sequence.py -v
```

**Acceptance Criteria:**
- [ ] All simulator tests pass
- [ ] Sequence diagram shows WriteData (0x8D)
- [ ] No LENGTH_ERROR in output

---

#### Task 4.2: Hardware validation (acceptance test)
**File:** `acceptance_tests/test_ndef_write_hardware.py`
**Status:** ⬜ Not Started

```python
@pytest.mark.hardware
def test_ndef_write_with_real_tag():
    """Validate NDEF write works on real hardware."""
    with CardManager() as card:
        # ... test with real tag
```

**Acceptance Criteria:**
- [ ] Test runs with real NTAG424 tag
- [ ] NDEF data successfully written
- [ ] Tag readable by phone after provisioning

---

## Sprint Board

| Task | Owner | Points | Status | Blocked By |
|------|-------|--------|--------|------------|
| 1.1 Create WriteDataAuth class | Neo | 1 | ⬜ | - |
| 1.2 Add exports | Neo | 0.5 | ⬜ | 1.1 |
| 1.3 Unit test WriteDataAuth | Neo | 0.5 | ⬜ | 1.1 |
| 2.1 Update provisioning service | Neo | 1 | ⬜ | 1.1 |
| 2.2 Remove deprecated usage | Neo | 0.5 | ⬜ | 2.1 |
| 3.1 Simulator WriteData handler | Trin | 1 | ⬜ | - |
| 3.2 Sequence validation test | Trin | 1 | ⬜ | 3.1, 1.1 |
| 3.3 Expected sequence test | Trin | 0.5 | ⬜ | 3.2 |
| 4.1 Full simulator test | Both | 0.5 | ⬜ | 2.1, 3.2 |
| 4.2 Hardware validation | Both | 0.5 | ⬜ | 4.1 |

---

## Definition of Done

- [ ] WriteDataAuth command created and tested
- [ ] Provisioning service uses WriteData (0x8D)
- [ ] Simulator validates WriteData command
- [ ] Sequence tests pass in headless mode
- [ ] Hardware acceptance test passes
- [ ] No regressions in existing tests
- [ ] Documentation updated

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Simulator doesn't fully replicate tag behavior | Medium | Medium | Also run hardware acceptance test |
| MAC calculation differs between commands | Low | High | Use existing MAC logic, test thoroughly |
| Frame size still exceeds limit | Low | Medium | Implement chaining if needed |

---

## Notes

- WriteData (0x8D) does NOT require prior file selection - it addresses by FileNo
- MAC is calculated over: `CMD || CmdCtr || TI || Header || Data`
- Counter increments only once per complete command
- For data > 248 bytes, implement command chaining (future task)

