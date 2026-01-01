#!/usr/bin/env python3
"""
Debug tool to analyze SDM provisioning sequence against spec.

Reads a TUI log file and compares the actual APDU sequence against
the expected sequence per NXP spec and SDM_SETUP_SEQUENCE.md.
"""

import re
import sys
from pathlib import Path


def parse_log_apdus(log_path: str) -> list[dict]:
    """Parse C-APDU and R-APDU lines from a TUI log."""
    apdus = []
    with open(log_path, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for C-APDU
        capdu_match = re.search(r'>> C-APDU: ([0-9A-Fa-f ]+)', line)
        if capdu_match:
            capdu_hex = capdu_match.group(1).replace(' ', '').upper()

            # Try to find corresponding R-APDU
            rapdu_hex = None
            rapdu_status = None
            for j in range(i+1, min(i+10, len(lines))):
                rapdu_match = re.search(r'<< R-APDU.*?: (.*?) \[(.*?)\]', lines[j])
                if rapdu_match:
                    rapdu_hex = rapdu_match.group(1).replace(' ', '').upper()
                    rapdu_status = rapdu_match.group(2)
                    break

            apdus.append({
                'capdu': capdu_hex,
                'rapdu': rapdu_hex,
                'status': rapdu_status,
                'line': i + 1
            })
        i += 1

    return apdus


def decode_apdu(hex_str: str) -> dict:
    """Decode an APDU into its components."""
    if len(hex_str) < 8:
        return {'error': 'too short'}

    cla = int(hex_str[0:2], 16)
    ins = int(hex_str[2:4], 16)
    p1 = int(hex_str[4:6], 16)
    p2 = int(hex_str[6:8], 16)

    result = {
        'cla': cla,
        'ins': ins,
        'p1': p1,
        'p2': p2,
        'cla_hex': f'0x{cla:02X}',
        'ins_hex': f'0x{ins:02X}',
    }

    if len(hex_str) > 8:
        lc = int(hex_str[8:10], 16)
        result['lc'] = lc
        if len(hex_str) > 10:
            data = hex_str[10:10+lc*2]
            result['data'] = data
            result['data_len'] = len(data) // 2

    # Identify command
    if cla == 0x00 and ins == 0xA4:
        result['name'] = 'ISOSelectFile'
        if p1 == 0x04:
            result['name'] = 'SelectApplication'
        elif p1 == 0x02:
            result['name'] = 'ISOSelectFile (EF)'
    elif cla == 0x00 and ins == 0xD6:
        result['name'] = 'ISOUpdateBinary'
    elif cla == 0x00 and ins == 0xB0:
        result['name'] = 'ISOReadBinary'
    elif cla == 0x90 and ins == 0x71:
        result['name'] = 'AuthenticateEV2First'
    elif cla == 0x90 and ins == 0xAF:
        result['name'] = 'GetAdditionalFrame'
    elif cla == 0x90 and ins == 0x5F:
        result['name'] = 'ChangeFileSettings'
    elif cla == 0x90 and ins == 0x8D:
        result['name'] = 'WriteData'
    elif cla == 0x90 and ins == 0x60:
        result['name'] = 'GetChipVersion'
    elif cla == 0x90 and ins == 0xF5:
        result['name'] = 'GetFileSettings'
    elif cla == 0x90 and ins == 0x64:
        result['name'] = 'GetKeyVersion'
    else:
        result['name'] = f'Unknown (CLA={cla:02X}, INS={ins:02X})'

    return result


def analyze_sequence(apdus: list[dict]) -> None:
    """Analyze the APDU sequence against spec."""
    print("\n" + "="*80)
    print("SDM PROVISIONING SEQUENCE ANALYSIS")
    print("="*80)

    print("\n## OBSERVED APDU SEQUENCE:\n")

    for i, apdu in enumerate(apdus):
        decoded = decode_apdu(apdu['capdu'])
        status_indicator = "[OK]" if apdu['status'] and ('OK' in apdu['status'] or '9100' in apdu['status'] or '91AF' in apdu['status'] or '9000' in apdu['status']) else "[FAIL]"

        print(f"  [{i+1:2d}] {decoded.get('name', 'Unknown'):30s} CLA={decoded.get('cla_hex', '??')} INS={decoded.get('ins_hex', '??')} {status_indicator} {apdu.get('status', 'unknown')}")

        # Check for issues
        issues = []

        # Issue: ISO command with MAC
        if decoded.get('cla') == 0x00 and decoded.get('ins') == 0xA4:
            if decoded.get('lc', 0) > 2:  # More than just file ID
                issues.append("WARNING: ISO command sent with extra data (MAC?) - ISO commands don't support secure messaging!")

        # Issue: ISOUpdateBinary in authenticated session
        if decoded.get('cla') == 0x00 and decoded.get('ins') == 0xD6:
            issues.append("WARNING: ISOUpdateBinary (0xD6) is CommMode.Plain only - cannot be used authenticated!")
            issues.append("    -> Use WriteData (0x8D) instead for authenticated writes")

        for issue in issues:
            print(f"        {issue}")

    print("\n" + "="*80)
    print("SPEC-COMPLIANT SEQUENCE OPTIONS FOR SDM PROVISIONING:")
    print("="*80)
    print("""
Per NXP NT4H2421Gx Datasheet Section 10.8.2:

OPTION A: WriteData (0x8D) for Authenticated Write (IF SMConfig Bit 2 allows)
================================================================================
  1. SelectPiccApplication (00 A4 04 00 ...)
  2. AuthenticateEV2First with Key 0 (90 71 00 00 02 00 00 00)
  3. AuthenticateEV2Second (90 AF 00 00 20 ...)
  4. ChangeFileSettings for SDM config (90 5F 00 00 ...)
     -> Sets FileOption, Access Rights, SDM offsets
     -> Counter increments to 1
  5. WriteData for NDEF content (90 8D 00 00 ...)
     -> Format: FileNo(1) || Offset(3 LE) || Length(3 LE) || Data || MAC(8)
     -> FileNo = 0x02 (NDEF file)
     -> No ISOSelectFile needed - FileNo is in command data!
     -> Counter increments to 2 (or more for chunked writes)

OPTION B: ISOUpdateBinary (0xD6) for Plain Write (IF SMConfig Bit 2 blocks WriteData)
=======================================================================================
  1. SelectPiccApplication (00 A4 04 00 ...)
  2. ISOSelectFile NDEF (00 A4 02 00 02 E1 04 00) - Plain mode, no MAC
  3. ISOUpdateBinary to write NDEF (00 D6 00 00 ...) - Plain mode, no auth
  4. AuthenticateEV2First with Key 0 (90 71 00 00 02 00 00 00)
  5. AuthenticateEV2Second (90 AF 00 00 20 ...)
  6. ChangeFileSettings for SDM (90 5F 00 00 ...)
     -> SDM offsets now reference existing NDEF content
     -> Counter increments to 1

CRITICAL NOTES:
  * SMConfig Bit 2 (SetConfiguration Option 04h):
    - If SET (1b): Disables WriteData in CommMode.MAC/Full → Use Option B
    - If CLEAR (0b): WriteData works in MAC mode → Use Option A

  * Operation Order Ambiguity:
    - NXP spec does NOT explicitly require NDEF before ChangeFileSettings
    - Spec implies it through references to "placeholders within the file"
    - Either order may work depending on chip configuration

  * WriteData (0x8D):
    - Supports CommMode.MAC and CommMode.Full when SMConfig allows
    - FileNo specified in command data (no ISOSelectFile needed)

  * ISOUpdateBinary (0xD6):
    - CommMode.Plain ONLY - no MAC/encryption support
    - Requires prior ISOSelectFile (00 A4) for file selection
    - CLA=0x00 commands do NOT support secure messaging

  * ISOSelectFile with CLA=0x00:
    - Does NOT support secure messaging (no MAC appending)
    - Sending with MAC causes 0x6A87 (Lc inconsistent with TLV)
""")


def main():
    if len(sys.argv) < 2:
        # Try to find most recent log
        log_dir = Path(__file__).parent.parent
        logs = sorted(log_dir.glob("tui_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            log_path = str(logs[0])
            print(f"Using most recent log: {log_path}")
        else:
            print("Usage: python debug_sdm_sequence.py <log_file>")
            sys.exit(1)
    else:
        log_path = sys.argv[1]

    print(f"\nAnalyzing: {log_path}")

    apdus = parse_log_apdus(log_path)
    print(f"Found {len(apdus)} APDUs")

    analyze_sequence(apdus)


if __name__ == "__main__":
    main()
