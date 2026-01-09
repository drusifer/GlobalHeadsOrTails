# NTAG424 SDM Provisioner

**TLDR;** Service-oriented TUI application for NTAG424 DNA provisioning. Production-ready service layer (ProvisioningService, TagDiagnosticsService) with Text User Interface. Hardware-validated, type-safe architecture with auto-chunking and secure key management. Run `provision-tui` for interactive operations.

**Status**: ✅ Production Ready | Service Layer Architecture | TUI Primary Interface | Hardware Validated

A Python library for provisioning NXP NTAG424 DNA NFC tags with unique keys and Secure Dynamic Messaging (SDM) capabilities.

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd ntag424_sdm_provisioner

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install in editable mode
pip install -e .
```

### Interactive Tool System (Recommended)

```bash
# Connect tag to reader, then run:
python examples/tag_tool_demo.py
```

**Features:**
- 7 tools that adapt to tag state
- Diagnostics, provisioning, URL updates, SDM config
- Tag swapping between operations
- Automatic backup restore
- Safe error recovery

**⚠️ WARNING**: Provisioning changes cryptographic keys permanently. Keys are saved to `tag_keys.csv` with automatic backups.

### Legacy Script (Batch Processing)

```bash
# For scripted/batch provisioning:
python examples/22_provision_game_coin.py
```

Single-shot provisioning script (legacy, maintained for compatibility).

### TUI (Text User Interface)

For a rich terminal experience:
```bash
# Run the TUI
provision-tui
```

---

## Features

✅ **End-to-End Provisioning** - Complete workflow from factory to provisioned  
✅ **Type-Safe Commands** - Compile-time safety for authenticated commands  
✅ **Sequence Logging** - Real-time APDU sequence diagrams for debugging  
✅ **EV2 Authentication** - Full two-phase authentication protocol  
✅ **Key Management** - CSV-based storage with two-phase commit  
✅ **Factory Reset** - Reset tags to factory defaults  
✅ **Clean Architecture** - SOLID principles, DRY, testable  
✅ **Crypto Validated** - All crypto verified vs NXP specifications  
✅ **Production Ready** - Proven working (see docs/analysis/SUCCESSFUL_PROVISION_FLOW.md)

---

## Architecture

### Command Pattern (Inverted Control)

```python
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.commands.change_key import ChangeKey

# New pattern: connection executes command
with CardManager() as card:
    # Unauthenticated commands
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    
    # Authenticated commands
    with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
        auth_conn.send(ChangeKey(0, new_key, None))
```

### Type Safety

Commands are type-checked at compile time:

```python
# ✅ OK: Unauthenticated command with card connection
card.send(SelectPiccApplication())

# ✅ OK: Authenticated command with authenticated connection
auth_conn.send(ChangeKey(0, new_key, None))

# ❌ ERROR: Type checker catches this at development time
card.send(ChangeKey(0, new_key, None))
# Error: ChangeKey requires AuthenticatedConnection
```

### Sequence Logging

Commands implement `Sequenceable` protocol for accurate debugging:

```python
from ntag424_sdm_provisioner.sequence_logger import start_sequence

seq = start_sequence("Provisioning")
card.send(SelectPiccApplication())  # Automatically logged!
card.send(GetChipVersion())         # Automatically logged!

print(seq.render_diagram())  # ASCII sequence diagram
```

Output shows actual commands as executed with timing and status words.

---

## Key Concepts

### Two-Session Provisioning

Changing Key 0 (PICC Master Key) invalidates the current session. Must use two sessions:

```python
# SESSION 1: Change Key 0 only
with AuthenticateEV2(old_key, key_no=0)(card) as auth_conn:
    auth_conn.send(ChangeKey(0, new_key, None))
# Session 1 is now INVALID (Key 0 changed)

# SESSION 2: Change Keys 1 & 3 with NEW Key 0
with AuthenticateEV2(new_key, key_no=0)(card) as auth_conn:
    auth_conn.send(ChangeKey(1, new_key_1, None))
    auth_conn.send(ChangeKey(3, new_key_3, None))
```

### ChangeKey Requirements

**Key 0** (PICC Master Key):
```python
# Only new key needed
auth_conn.send(ChangeKey(0, new_key, None))
```

**Keys 1-4** (Application Keys):
```python
# Old key REQUIRED for XOR verification
auth_conn.send(ChangeKey(1, new_key, old_key))
```

### Key Management

```python
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager

key_mgr = CsvKeyManager()

# Two-phase commit (atomic provisioning)
with key_mgr.provision_tag(uid, url="https://...") as new_keys:
    # Keys generated and saved (status='pending')
    auth_conn.send(ChangeKey(0, new_keys.get_picc_master_key_bytes(), None))
    auth_conn.send(ChangeKey(1, new_keys.get_app_read_key_bytes(), None))
    auth_conn.send(ChangeKey(3, new_keys.get_sdm_mac_key_bytes(), None))
    # On success: status='provisioned'
    # On exception: status='failed', keys backed up

# Retrieve keys later
keys = key_mgr.get_tag_keys(uid)
picc_key = keys.get_picc_master_key_bytes()
```

---

## Examples

### Provisioning
- `22_provision_game_coin.py` - Complete provisioning workflow
- `22a_provision_sdm_factory_keys.py` - Provision without changing keys

### Utilities
- `99_reset_to_factory.py` - Reset tag to factory defaults
- `check_ndef_config.py` - Diagnostic for NDEF and CC files
- `print_asset_tags.py` - List asset tags from database

### Diagnostics
- `10_auth_session.py` - Test authentication
- `20_get_file_counters.py` - Read file counters
- `21_build_sdm_url.py` - Test URL building

---

## Project Structure

```
src/ntag424_sdm_provisioner/
├── commands/              # APDU commands
│   ├── base.py           # Base classes, AuthenticatedConnection
│   ├── authenticate_ev2.py  # EV2 authentication
│   ├── change_key.py     # ChangeKey command
│   ├── change_file_settings.py
│   ├── sun_commands.py   # NDEF read/write
│   ├── iso_commands.py   # ISO 7816 commands
│   ├── select_picc_application.py
│   ├── get_chip_version.py
│   ├── get_file_ids.py
│   ├── get_file_settings.py
│   ├── get_key_version.py
│   ├── get_file_counters.py
│   ├── read_data.py
│   ├── write_data.py
│   ├── sdm_helpers.py    # SDM utilities
│   └── sdm_commands.py   # Compatibility shim
├── crypto/
│   ├── auth_session.py   # Ntag424AuthSession
│   └── crypto_primitives.py  # Verified crypto functions
├── hal.py                # Hardware abstraction
├── csv_key_manager.py    # Key storage
├── constants.py          # Enums, dataclasses
├── uid_utils.py          # UID helpers
└── trace_util.py         # Debug tracing

examples/
├── 22_provision_game_coin.py  # Main provisioning (clean OOP)
├── 99_reset_to_factory.py     # Factory reset utility
└── check_ndef_config.py       # NDEF diagnostics

tests/
├── test_crypto_validation.py  # Crypto vs NXP specs
├── raw_changekey_test_fixed.py  # Raw pyscard test
└── test_production_auth.py    # Production auth test

examples/
├── arduino/              # Arduino sketches and C++ library
├── 22_provision_game_coin.py
...

```

---

## Documentation

### Core Knowledge Base (Root)
- **README.md** - This file (quick start guide)
- **MINDMAP.md** - Project overview and current status
- **ARCH.md** - Architecture documentation (per PRD Section 6.3)
- **DECISIONS.md** - Key project decisions log
- **LESSONS.md** - Key learnings and best practices
- **OBJECTIVES.md** - Project objectives and goals
- **charts.md** - Sequence diagrams with actual flow
- **HOW_TO_RUN.md** - User guide (per PRD Section 6.3)

### Product Requirements
- **docs/PRD.md** - Product Requirements Document (User Stories, Acceptance Criteria, Quality Standards)
- **docs/ROADMAP.md** - Product roadmap and sprint planning guide

### Specifications & Analysis
- **docs/specs/** - External specifications (NXP datasheets, reader specs)
- **docs/analysis/** - Investigation notes, findings, and experiment logs
  - **SUCCESSFUL_PROVISION_FLOW.md** - Captured trace of working provisioning
- **docs/status/** - Progress reports and session summaries

### Agent System
- **agents/CHAT.md** - Team chat log (Bob System protocol)
- **agents/[persona].docs/** - Individual persona state and documentation
- **START_HERE.md** - Bob System protocol quick start (workspace root)

### Code Navigation
- **docs/SYMBOL_INDEX.md** - Auto-generated codebase symbol index
- **COMMAND_GLOSSARY.md** - Command reference guide

**Note**: This project uses the **Bob System** multi-persona protocol. See `agents/CHAT.md` and `START_HERE.md` for details.

---

## Key Classes

### Commands

**`ApduCommand`** - Base for unauthenticated commands:
- `build_apdu()` - Build APDU bytes
- `parse_response()` - Parse response

**`AuthApduCommand`** - Base for authenticated commands:
- `get_command_byte()` - Command byte (e.g., 0xC4)
- `get_unencrypted_header()` - Unencrypted portion
- `build_command_data()` - Plaintext data
- `parse_response()` - Parse decrypted response

### Authentication

**`AuthenticateEV2`** - Protocol orchestrator (callable class):
```python
# Returns AuthenticatedConnection context manager
with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
    # Authenticated operations
    auth_conn.send(ChangeKey(...))
```

**`AuthenticatedConnection`** - Context manager for authenticated operations:
- Transparently handles encryption, CMAC, IV calculation
- Manages session keys and counter
- Delegates to `crypto_primitives.py`

### HAL

**`CardManager`** - Context manager for reader:
```python
with CardManager(reader_index=0) as card:
    # card is NTag424CardConnection
    card.send(Command())
```

**`NTag424CardConnection`** - Card communication:
- `send_apdu()` - Low-level APDU
- `send()` - Execute command object
- `send_write_chunked()` - Multi-chunk writes

---

## Common Tasks

### Read Tag Info
```python
with CardManager() as card:
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    print(f"UID: {version.uid.hex().upper()}")
    print(f"Asset Tag: {version.get_asset_tag()}")
```

### Authenticate
```python
factory_key = bytes(16)  # 0x00 * 16
with AuthenticateEV2(factory_key, key_no=0)(card) as auth_conn:
    # Authenticated operations
    pass
```

### Change Keys
```python
# Key 0 (no old key)
auth_conn.send(ChangeKey(0, new_key, None))

# Keys 1-4 (old key required)
auth_conn.send(ChangeKey(1, new_key, old_key))
```

### Factory Reset
```python
# Must know old keys for Keys 1 & 3
keys = key_mgr.get_tag_keys(uid)

# Session 1: Reset Key 0
with AuthenticateEV2(keys.get_picc_master_key_bytes(), key_no=0)(card) as auth:
    auth.send(ChangeKey(0, factory_key, None, 0x00))

# Session 2: Reset Keys 1 & 3
with AuthenticateEV2(factory_key, key_no=0)(card) as auth:
    auth.send(ChangeKey(1, factory_key, keys.get_app_read_key_bytes(), 0x00))
    auth.send(ChangeKey(3, factory_key, keys.get_sdm_mac_key_bytes(), 0x00))
```

---

## Troubleshooting

### Authentication Fails (91AE)
**Causes**:
- Wrong key (check database)
- Session invalid (changed Key 0 without re-auth)
- Rate limited (wait 60 seconds)

**Solution**: Check `tag_keys.csv` for status, use correct key

### Rate Limiting (91AD)
**Cause**: Too many failed auth attempts (3-5 limit)

**Solution**: 
- Wait 60+ seconds
- Use fresh tag
- Don't test auth upfront

### Integrity Error (911E)
**Causes**:
- Wrong old key for Keys 1-4 (XOR mismatch)
- CMAC verification failed

**Solution**: Verify old key in database is correct

### SDM Not Working (Placeholders Visible)
**Cause**: ChangeFileSettings returns 917E (LENGTH_ERROR)

**Status**: Known issue, under investigation. Doesn't block provisioning.

---

## Testing

### Run Tests
```bash
# All tests
pytest -v

# Specific test
pytest tests/test_crypto_validation.py -v

# With hardware (requires tag on reader)
pytest tests/test_production_auth.py -v
```

### Mock HAL
```bash
# Run tests without hardware
$env:USE_MOCK_HAL="1"
pytest -v
```

---

## Prerequisites

- **Python 3.8+**
- **PC/SC Compliant NFC Reader** (ACR122U recommended)
- **NXP NTAG424 DNA Tags**
- **Windows/Linux/Mac** with PC/SC drivers

### Dependencies
- `pyscard` - PC/SC interface
- `pycryptodome` - AES, CMAC cryptography

Installed automatically via `pip install -e .`

---

## Security Notes

### Key Storage
- Keys stored in `tag_keys.csv`
- **CRITICAL**: Secure this file (contains all tag keys)
- Automatic backups before changes

### Factory Defaults
- Factory key: `0x00` * 16 (all zeros)
- **NEVER use factory keys in production**
- Always change keys during provisioning

### Rate Limiting
- Tags block auth after 3-5 failed attempts
- Counter persists in non-volatile memory
- 60+ second lockout

---

## API Reference

### Core Classes

**CardManager** - Reader connection:
```python
with CardManager(reader_index=0) as card:
    # Use card
```

**AuthenticateEV2** - Authentication protocol:
```python
with AuthenticateEV2(key, key_no=0)(card) as auth_conn:
    # Authenticated operations
```

**CsvKeyManager** - Key storage:
```python
key_mgr = CsvKeyManager()
keys = key_mgr.get_tag_keys(uid)
with key_mgr.provision_tag(uid, url="...") as new_keys:
    # Provision with two-phase commit
```

### Main Commands

**Unauthenticated**:
- `SelectPiccApplication()` - Select PICC app
- `GetChipVersion()` - Read version + UID
- `GetFileIds()` - List files
- `GetFileSettings(file_no)` - Read file settings
- `GetKeyVersion(key_no)` - Read key version
- `ISOSelectFile(file_id)` - Select ISO file
- `ISOReadBinary(offset, length)` - Read data
- `ChangeFileSettings(config)` - Change file settings (PLAIN mode)

**Authenticated**:
- `ChangeKey(key_no, new_key, old_key)` - Change key
- `ChangeFileSettingsAuth(config)` - Change settings (MAC/FULL modes)

**Special**:
- `WriteNdefMessage(data)` - Write NDEF (chunked)
- `ReadNdefMessage()` - Read NDEF

---

## Examples

### Full Provisioning
```python
from ntag424_sdm_provisioner.hal import CardManager
from ntag424_sdm_provisioner.csv_key_manager import CsvKeyManager
from ntag424_sdm_provisioner.commands.authenticate_ev2 import AuthenticateEV2
from ntag424_sdm_provisioner.commands.change_key import ChangeKey
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion

key_mgr = CsvKeyManager()
factory_key = bytes(16)

with CardManager() as card:
    # Get UID
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    uid = version.uid
    
    # Two-phase commit
    with key_mgr.provision_tag(uid, url="https://example.com") as new_keys:
        # Session 1: Change Key 0
        with AuthenticateEV2(factory_key, key_no=0)(card) as auth:
            auth.send(ChangeKey(0, new_keys.get_picc_master_key_bytes(), None))
        
        # Session 2: Change Keys 1 & 3
        with AuthenticateEV2(new_keys.get_picc_master_key_bytes(), key_no=0)(card) as auth:
            auth.send(ChangeKey(1, new_keys.get_app_read_key_bytes(), None))
            auth.send(ChangeKey(3, new_keys.get_sdm_mac_key_bytes(), None))
    
    # Keys automatically saved as 'provisioned'
```

### Read Tag
```python
with CardManager() as card:
    card.send(SelectPiccApplication())
    version = card.send(GetChipVersion())
    
    print(f"UID: {version.uid.hex().upper()}")
    print(f"Hardware: v{version.hardware_protocol}")
    print(f"Software: v{version.software_protocol}")
```

### Factory Reset
```python
keys = key_mgr.get_tag_keys(uid)
factory_key = bytes(16)

# Session 1: Reset Key 0
with AuthenticateEV2(keys.get_picc_master_key_bytes(), key_no=0)(card) as auth:
    auth.send(ChangeKey(0, factory_key, None, 0x00))

# Session 2: Reset Keys 1 & 3
with AuthenticateEV2(factory_key, key_no=0)(card) as auth:
    auth.send(ChangeKey(1, factory_key, keys.get_app_read_key_bytes(), 0x00))
    auth.send(ChangeKey(3, factory_key, keys.get_sdm_mac_key_bytes(), 0x00))

# Update database
key_mgr.save_tag_keys(TagKeys.from_factory_keys(uid))
```

---

## Documentation Reference

| Document | Purpose | Location |
|----------|---------|----------|
| **PRD.md** | Product Requirements Document (User Stories, Acceptance Criteria, Quality Standards) | `docs/PRD.md` |
| **ARCH.md** | Architecture documentation (Service Layer, Commands, Crypto, HAL) | Root |
| **MINDMAP.md** | Project overview and current status | Root |
| **DECISIONS.md** | Key project decisions log | Root |
| **LESSONS.md** | Key learnings and best practices | Root |
| **OBJECTIVES.md** | Project objectives and goals | Root |
| **charts.md** | Sequence diagrams | Root |
| **HOW_TO_RUN.md** | User guide (Windows command reference) | Root |
| **task.md** | Current sprint task board | Root |
| **SYMBOL_INDEX.md** | Auto-generated codebase symbol index | `docs/SYMBOL_INDEX.md` |
| **SUCCESSFUL_PROVISION_FLOW.md** | Proven working trace | `docs/analysis/` |

---

## Development

### Running Tests
```bash
# All tests
pytest -v

# Specific module
pytest tests/test_crypto_validation.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Trace Utilities
```python
from ntag424_sdm_provisioner.trace_util import trace_block, trace_apdu, trace_crypto

with trace_block("My Operation"):
    # Code here
    
trace_apdu("Command Name", apdu, response, sw1, sw2)
trace_crypto("Operation", key, input_data, output_data)
```

---

## References

- **NXP AN12196** - NTAG 424 DNA features and hints
- **NXP AN12343** - Session key derivation
- **NXP Datasheet** - NT4H2421Gx NTAG 424 DNA
- **ISO 7816-4** - APDU command structure

---

## Contributing

### Code Style
- Follow PEP 8
- Type hints for all functions
- Docstrings for public APIs
- Single Responsibility Principle
- DRY (Don't Repeat Yourself)

### Testing
- Add tests for new features
- Maintain >50% coverage
- Validate crypto against NXP specs

### Documentation
- Update relevant .md files
- Add examples for new features
- Keep charts.md diagrams current

---

## License

[Your License Here]

---

## Credits

- NXP Semiconductors - NTAG424 DNA chip and specifications
- pyscard project - PC/SC interface
- Crypto primitives verified against NXP official specifications

---

**Status**: ✅ Production Ready | Service Layer Architecture (Per PRD)  
**Version**: 1.0 (Post-refactor)  
**Last Updated**: 2025-11-28  
**PRD**: See `docs/PRD.md` for product requirements and user stories
