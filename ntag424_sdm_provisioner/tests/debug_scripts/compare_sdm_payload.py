#!/usr/bin/env python3
"""Compare spec-based SDM payload calculation vs code-generated payload.

This script calculates what the ChangeFileSettings payload SHOULD be
according to the NXP spec, and compares it to what our code generates.
"""

from ntag424_sdm_provisioner.commands.sdm_helpers import (
    build_sdm_settings_payload,
    calculate_sdm_offsets,
)
from ntag424_sdm_provisioner.constants import (
    GAME_COIN_BASE_URL,
    AccessRight,
    AccessRights,
    CommMode,
    FileOption,
    SDMConfiguration,
    SDMUrlTemplate,
)


def calculate_spec_based_offsets():
    """Calculate offsets based purely on URL structure and NDEF format."""
    # URL Template
    BASE_URL = GAME_COIN_BASE_URL

    # Build URL with placeholders
    uid_placeholder = '00000000000000'  # 14 chars (7 bytes hex)
    ctr_placeholder = '000000'  # 6 chars (3 bytes hex)
    cmac_placeholder = '0000000000000000'  # 16 chars (8 bytes hex)

    # URL format: base?uid=XXX&ctr=XXX&cmac=XXX
    full_url = f'{BASE_URL}?uid={uid_placeholder}&ctr={ctr_placeholder}&cmac={cmac_placeholder}'

    print(f'Full URL: {full_url[:60]}...{full_url[-40:]}')
    print(f'URL length: {len(full_url)} chars')

    # For https:// prefix code = 0x04, we strip 'https://' (8 chars)
    url_without_prefix = full_url[8:]  # Remove 'https://'

    print(f'\nURL without prefix: {url_without_prefix[:50]}...')
    print(f'URL bytes length: {len(url_without_prefix)}')

    # NDEF Type 4 Tag structure:
    # Offset 0-1: NDEF file length (2 bytes, big-endian)
    # Offset 2: TLV Tag = 0x03
    # Offset 3: TLV Length
    # Offset 4: Record Header = 0xD1
    # Offset 5: Type Length = 0x01
    # Offset 6: Payload Length
    # Offset 7: Type = 0x55 ('U')
    # Offset 8: URI Prefix = 0x04 (https://)
    # Offset 9+: URL content (without https://)

    NDEF_HEADER_SIZE = 9  # Bytes before URL content starts

    # Find positions of placeholders in URL content
    uid_pos_in_url = url_without_prefix.find('uid=') + 4  # +4 to skip 'uid='
    ctr_pos_in_url = url_without_prefix.find('ctr=') + 4
    cmac_pos_in_url = url_without_prefix.find('cmac=') + 5  # +5 to skip 'cmac='

    print('\n--- Offset calculations (from start of NDEF file) ---')
    uid_offset = NDEF_HEADER_SIZE + uid_pos_in_url
    ctr_offset = NDEF_HEADER_SIZE + ctr_pos_in_url
    cmac_offset = NDEF_HEADER_SIZE + cmac_pos_in_url

    print(f'UID position in URL content: {uid_pos_in_url}')
    print(f'CTR position in URL content: {ctr_pos_in_url}')
    print(f'CMAC position in URL content: {cmac_pos_in_url}')
    print()
    print(f'UIDOffset (file offset): {uid_offset} (0x{uid_offset:02X})')
    print(f'SDMReadCtrOffset (file offset): {ctr_offset} (0x{ctr_offset:02X})')
    print(f'SDMMACOffset (file offset): {cmac_offset} (0x{cmac_offset:02X})')
    print(f'SDMMACInputOffset (same as UID): {uid_offset} (0x{uid_offset:02X})')

    return uid_offset, ctr_offset, cmac_offset


def build_spec_based_payload(uid_offset, ctr_offset, cmac_offset):
    """Build payload based purely on NXP spec Table 69."""
    print('\n' + '='*70)
    print('SPEC-BASED ChangeFileSettings PAYLOAD')
    print('='*70)

    # Field 1: FileNo
    file_no = 0x02
    print(f'FileNo: 0x{file_no:02X}')

    # Field 2: FileOption
    # Bit 6 = SDM enabled (1), Bits 1-0 = CommMode.PLAIN (00)
    file_option = 0x40
    print(f'FileOption: 0x{file_option:02X} (SDM enabled, CommMode.PLAIN)')

    # Field 3: AccessRights (2 bytes)
    # Per spec: first byte = [Read|Write], second byte = [RW|Change]
    access_byte1 = (0xE << 4) | 0x0  # Read=E, Write=0 -> 0xE0
    access_byte0 = (0xE << 4) | 0xE  # RW=E, Change=E -> 0xEE
    print(f'AccessRights: 0x{access_byte1:02X} 0x{access_byte0:02X}')

    # Field 4: SDMOptions (1 byte)
    # Bit 7 = UID mirror, Bit 6 = ReadCtr, Bit 0 = ASCII
    sdm_options = 0x80 | 0x40 | 0x01  # = 0xC1
    print(f'SDMOptions: 0x{sdm_options:02X} (UID + ReadCtr + ASCII)')

    # Field 5: SDMAccessRights (2 bytes) - Little-endian
    # 16-bit: (MetaRead << 12) | (FileRead << 8) | (RFU << 4) | CtrRet
    # = (E << 12) | (3 << 8) | (F << 4) | E = 0xE3FE
    # LE bytes: 0xFE, 0xE3
    sdm_ar_byte0 = 0xFE  # RFU=F, CtrRet=E
    sdm_ar_byte1 = 0xE3  # MetaRead=E, FileRead=3
    print(f'SDMAccessRights: 0x{sdm_ar_byte0:02X} 0x{sdm_ar_byte1:02X}')

    # Field 6: UIDOffset (3 bytes, LE)
    uid_offset_bytes = uid_offset.to_bytes(3, 'little')
    print(f'UIDOffset: {uid_offset_bytes.hex()} (decimal {uid_offset})')

    # Field 7: SDMReadCtrOffset (3 bytes, LE)
    ctr_offset_bytes = ctr_offset.to_bytes(3, 'little')
    print(f'SDMReadCtrOffset: {ctr_offset_bytes.hex()} (decimal {ctr_offset})')

    # Field 8: PICCDataOffset - NOT present (MetaRead=E)
    print('PICCDataOffset: NOT PRESENT')

    # Field 9: SDMMACInputOffset (3 bytes, LE)
    mac_input_offset_bytes = uid_offset.to_bytes(3, 'little')
    print(f'SDMMACInputOffset: {mac_input_offset_bytes.hex()} (decimal {uid_offset})')

    # Field 10-11: SDMENCOffset/Length - NOT present (Bit 4 = 0)
    print('SDMENCOffset/Length: NOT PRESENT')

    # Field 12: SDMMACOffset (3 bytes, LE)
    cmac_offset_bytes = cmac_offset.to_bytes(3, 'little')
    print(f'SDMMACOffset: {cmac_offset_bytes.hex()} (decimal {cmac_offset})')

    # Field 13: SDMReadCtrLimit - NOT present (Bit 5 = 0)
    print('SDMReadCtrLimit: NOT PRESENT')

    # Build payload
    payload = bytes([
        file_no,
        file_option,
        access_byte1, access_byte0,
        sdm_options,
        sdm_ar_byte0, sdm_ar_byte1,
    ]) + uid_offset_bytes + ctr_offset_bytes + mac_input_offset_bytes + cmac_offset_bytes

    return payload


def get_code_generated_payload():
    """Get what our code actually generates."""
    template = SDMUrlTemplate(
        base_url=GAME_COIN_BASE_URL,
        uid_placeholder='00000000000000',
        cmac_placeholder='0000000000000000',
        read_ctr_placeholder='000000',
        enc_placeholder=None,
    )

    offsets = calculate_sdm_offsets(template)

    print('\n' + '='*70)
    print('CODE-GENERATED OFFSETS')
    print('='*70)
    print(f'uid_offset: {offsets.uid_offset} (0x{offsets.uid_offset:02X})')
    print(f'read_ctr_offset: {offsets.read_ctr_offset} (0x{offsets.read_ctr_offset:02X})')
    print(f'mac_input_offset: {offsets.mac_input_offset} (0x{offsets.mac_input_offset:02X})')
    print(f'mac_offset: {offsets.mac_offset} (0x{offsets.mac_offset:02X})')

    # Build SDM config
    access_rights = AccessRights(
        read=AccessRight.FREE,
        write=AccessRight.KEY_0,
        read_write=AccessRight.FREE,
        change=AccessRight.FREE,
    )

    sdm_config = SDMConfiguration(
        file_no=0x02,
        comm_mode=CommMode.PLAIN,
        access_rights=access_rights,
        enable_sdm=True,
        sdm_options=(FileOption.UID_MIRROR | FileOption.READ_COUNTER),
        offsets=offsets,
    )

    payload = build_sdm_settings_payload(sdm_config)
    return payload, offsets


def main():
    print('='*70)
    print('SDM PAYLOAD COMPARISON: Spec vs Code')
    print('='*70)

    # Step 1: Calculate spec-based offsets
    uid_offset, ctr_offset, cmac_offset = calculate_spec_based_offsets()

    # Step 2: Build spec-based payload
    spec_payload = build_spec_based_payload(uid_offset, ctr_offset, cmac_offset)

    # Step 3: Get code-generated payload
    code_payload, code_offsets = get_code_generated_payload()

    # Step 4: Compare
    print('\n' + '='*70)
    print('PAYLOAD COMPARISON')
    print('='*70)
    print(f'Spec payload: {spec_payload.hex()}')
    print(f'Code payload: {code_payload.hex()}')
    print(f'Length: spec={len(spec_payload)}, code={len(code_payload)}')
    print()

    if spec_payload == code_payload:
        print('MATCH! Payloads are identical.')
    else:
        print('MISMATCH! Differences:')
        print()

        # Compare byte by byte
        max_len = max(len(spec_payload), len(code_payload))
        for i in range(max_len):
            spec_byte = spec_payload[i] if i < len(spec_payload) else None
            code_byte = code_payload[i] if i < len(code_payload) else None

            if spec_byte != code_byte:
                spec_str = f'0x{spec_byte:02X}' if spec_byte is not None else 'N/A'
                code_str = f'0x{code_byte:02X}' if code_byte is not None else 'N/A'
                print(f'  Byte {i:2d}: spec={spec_str}, code={code_str}')

    # Compare offsets
    print('\n' + '='*70)
    print('OFFSET COMPARISON')
    print('='*70)
    print(f'UIDOffset:       spec={uid_offset}, code={code_offsets.uid_offset}, diff={code_offsets.uid_offset - uid_offset}')
    print(f'ReadCtrOffset:   spec={ctr_offset}, code={code_offsets.read_ctr_offset}, diff={code_offsets.read_ctr_offset - ctr_offset}')
    print(f'MACInputOffset:  spec={uid_offset}, code={code_offsets.mac_input_offset}, diff={code_offsets.mac_input_offset - uid_offset}')
    print(f'MACOffset:       spec={cmac_offset}, code={code_offsets.mac_offset}, diff={code_offsets.mac_offset - cmac_offset}')

    print('\n' + '='*70)
    print('ROOT CAUSE ANALYSIS')
    print('='*70)
    print('''
The code has TWO bugs in calculate_sdm_offsets():

1. NDEF HEADER SIZE: Uses ndef_overhead=7, but actual structure is 9 bytes:
   [Length(2)] + [TLV T(1)+L(1)] + [NDEF Header(1)+TypeLen(1)+PayloadLen(1)+Type(1)+URIPrefix(1)]
   = 2 + 2 + 5 = 9 bytes

2. URL PREFIX: Searches for "uid=" in FULL URL including "https://",
   but NDEF stores URL WITHOUT the prefix (prefix is replaced by code 0x04).
   This adds 8 extra characters to the position.

   Total error: 9 - 7 + 8 = 10? No wait...

   Actually the bug is different:
   - Code: ndef_overhead(7) + full_url.find("uid=") + 4
   - Spec: NDEF_HEADER(9) + stripped_url.find("uid=") + 4

   The full_url includes "https://" (8 chars), stripped_url doesn't.
   So full_url.find() returns 8 more than stripped_url.find().

   Code offset = 7 + (stripped_pos + 8) = 15 + stripped_pos
   Spec offset = 9 + stripped_pos

   Difference = Code - Spec = (15 + stripped_pos) - (9 + stripped_pos) = 6

   This explains the constant +6 difference!

FIX: Change ndef_overhead from 7 to 9, AND search in URL without prefix
     (or subtract 8 from the position found in full URL)
''')


if __name__ == '__main__':
    main()
