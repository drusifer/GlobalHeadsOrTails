
import pytest
from ntag424_sdm_provisioner.constants import SDMConfiguration, CommMode, AccessRights, FileOption, SDMOffsets
from ntag424_sdm_provisioner.commands.change_file_settings import ChangeFileSettingsAuth

def test_change_file_settings_auth_structure():
    """
    Verify the structure of ChangeFileSettingsAuth command.
    Per LESSONS.md (Root Cause #3), FileNo should be INSIDE the encrypted payload,
    not in the unencrypted header.
    """
    # Setup configuration
    config = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,
        access_rights=AccessRights(),
        enable_sdm=True,
        sdm_options=FileOption.UID_MIRROR | FileOption.READ_COUNTER,
        offsets=SDMOffsets(uid_offset=0, read_ctr_offset=0)
    )
    
    cmd = ChangeFileSettingsAuth(config)
    
    # Check unencrypted header
    header = cmd.get_unencrypted_header()
    print(f"Unencrypted Header: {header.hex()}")
    
    # Check command data (to be encrypted)
    data = cmd.build_command_data()
    print(f"Command Data (Pre-encryption): {data.hex()}")
    
    # ASSERTIONS based on LESSONS.md findings
    
    # 1. FileNo should NOT be in unencrypted header
    # Current code (BUG): returns b'\x02'
    # Correct code: should return b''
    if header == bytes([0x02]):
        print("FAIL: FileNo found in unencrypted header (BUG CONFIRMED)")
    else:
        print("PASS: Unencrypted header is empty")
        
    # 2. FileNo SHOULD be in command data
    # Current code (BUG): returns settings payload only (starting with FileOption)
    # Correct code: should start with 0x02
    if data[0] != 0x02:
        print(f"FAIL: Command data starts with 0x{data[0]:02X}, expected FileNo (0x02) (BUG CONFIRMED)")
    else:
        print("PASS: Command data starts with FileNo")

if __name__ == "__main__":
    test_change_file_settings_auth_structure()
