#!/usr/bin/env python3
"""
Test Setup URL provisioning traces from SUCCESSFUL NDEF TUI.log.txt.

Verifies that the simulator has the correct traces loaded for:
1. UID matching the successful provisioning run
2. NDEF operations (ISOSelectFile, ISOUpdateBinary chunks)
3. Authentication traces for Setup URL (AUTH_PHASE1_5, AUTH_PHASE2_5)
4. ChangeFileSettings response
"""

import logging
from ntag424_sdm_provisioner.commands.get_chip_version import GetChipVersion
from ntag424_sdm_provisioner.commands.iso_commands import ISOSelectFile, ISOFileID
from ntag424_sdm_provisioner.commands.select_picc_application import SelectPiccApplication
from tests.trace_based_simulator import MockCardManager, TraceBasedSimulator

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def test_simulator_has_correct_uid():
    """Verify simulator uses correct UID from SUCCESSFUL NDEF TUI.log.txt."""
    expected_uid = "0451664A2F7080"

    with MockCardManager() as card:
        card.send(SelectPiccApplication())
        version = card.send(GetChipVersion())
        actual_uid = version.uid.hex().upper()

        assert actual_uid == expected_uid, f"UID mismatch: {actual_uid} != {expected_uid}"
        log.info(f"✓ Simulator UID verified: {actual_uid}")


def test_simulator_has_setup_url_auth_traces():
    """Verify simulator has AUTH_PHASE1_5 and AUTH_PHASE2_5 traces loaded."""
    sim = TraceBasedSimulator()

    # Verify AUTH_PHASE1_5 exists (from SUCCESSFUL NDEF TUI.log.txt line 53)
    assert "AUTH_PHASE1_5" in sim.traces, "Missing AUTH_PHASE1_5 trace"
    expected_rndb = bytes.fromhex("AE125987350A6A35A4FC3434ADC52796")
    actual_data, sw1, sw2 = sim.traces["AUTH_PHASE1_5"]
    assert bytes(actual_data) == expected_rndb, "AUTH_PHASE1_5 RndB mismatch"
    assert (sw1, sw2) == (0x91, 0xAF), "AUTH_PHASE1_5 SW mismatch"
    log.info("✓ AUTH_PHASE1_5 trace verified")

    # Verify AUTH_PHASE2_5 exists (from SUCCESSFUL NDEF TUI.log.txt line 65)
    assert "AUTH_PHASE2_5" in sim.traces, "Missing AUTH_PHASE2_5 trace"
    expected_response = bytes.fromhex("85E8D8FD6557667FFCCA80ADB6DADE42C2E98B35536AFEA71ADA8C39AB63802F")
    actual_data, sw1, sw2 = sim.traces["AUTH_PHASE2_5"]
    assert bytes(actual_data) == expected_response, "AUTH_PHASE2_5 response mismatch"
    assert (sw1, sw2) == (0x91, 0x00), "AUTH_PHASE2_5 SW mismatch"
    log.info("✓ AUTH_PHASE2_5 trace verified")


def test_simulator_has_change_file_settings_trace():
    """Verify simulator has ChangeFileSettings response trace."""
    sim = TraceBasedSimulator()

    # Verify 90_5F_1 exists (from SUCCESSFUL NDEF TUI.log.txt line 114)
    assert "90_5F_1" in sim.traces, "Missing ChangeFileSettings trace"
    expected_cmac = bytes.fromhex("6393BAF61A2726F8")
    actual_data, sw1, sw2 = sim.traces["90_5F_1"]
    assert bytes(actual_data) == expected_cmac, "ChangeFileSettings CMAC mismatch"
    assert (sw1, sw2) == (0x91, 0x00), "ChangeFileSettings SW mismatch"
    log.info("✓ ChangeFileSettings trace verified")


def test_simulator_handles_ndef_operations():
    """Verify simulator handles ISOSelectFile and ISOUpdateBinary."""
    with MockCardManager() as card:
        # Select PICC
        card.send(SelectPiccApplication())
        log.info("✓ Selected PICC")

        # Select NDEF file (ISO)
        card.send(ISOSelectFile(ISOFileID.NDEF_FILE))
        log.info("✓ Selected NDEF file")

        # Write NDEF via chunked ISOUpdateBinary
        test_ndef_data = bytes([0x03, 0xB1, 0xD1]) + b"X" * 100
        sw1, sw2 = card.send_write_chunked(
            cla=0x00,
            ins=0xD6,  # UpdateBinary
            offset=0,
            data=test_ndef_data,
            chunk_size=52
        )
        assert (sw1, sw2) == (0x90, 0x00), f"NDEF write failed: {sw1:02X}{sw2:02X}"
        log.info(f"✓ NDEF written ({len(test_ndef_data)} bytes in chunks)")


if __name__ == "__main__":
    test_simulator_has_correct_uid()
    test_simulator_has_setup_url_auth_traces()
    test_simulator_has_change_file_settings_trace()
    test_simulator_handles_ndef_operations()
    print("\n" + "=" * 70)
    print("✓ All simulator trace tests PASSED!")
    print("=" * 70)
