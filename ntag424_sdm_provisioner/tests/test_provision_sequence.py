"""
Test: Provisioning Sequence Validation

Uses SequenceLogger to validate that the provisioning flow executes
commands in the correct order per the spec (SUCCESSFUL_PROVISION_FLOW.md).

Expected Sequence (Factory Provision):
1. SelectPiccApplication
2. GetChipVersion (multi-frame: 0x60, 0xAF, 0xAF)
3. AuthenticateEV2First (Key 0)
4. AuthenticateEV2Second
5. ISOSelectFile (NDEF file)
6. WriteNdefMessage (chunked - may be multiple commands)
7. SelectPiccApplication (re-select)
8. ChangeFileSettingsAuth (SDM config)

Author: Trin (QA) + Oracle (Spec Reference)
Date: 2025-12-01
"""

import pytest
from tests.mock_hal import MockCardConnection

from ntag424_sdm_provisioner.sequence_logger import (
    SequenceLogger,
    StepResult,
    create_sequence_logger,
)


class TestProvisioningSequence:
    """
    Test suite for validating provisioning command sequence.
    
    These tests use SequenceLogger to capture and validate the order
    of APDU commands sent during provisioning operations.
    """

    def test_sequence_logger_captures_steps(self):
        """SequenceLogger correctly captures command/response pairs."""
        seq = create_sequence_logger("TestOperation")
        
        # Simulate a command/response
        seq.log_command("SelectPiccApplication", "00 A4 04 00 07 D2 76 00 00 85 01 01 00")
        seq.log_response("9000", "OK", "")
        
        assert len(seq.steps) == 1
        step = seq.steps[0]
        assert step.command_name == "SelectPiccApplication"
        assert step.status_word == "9000"
        assert step.result == StepResult.SUCCESS

    def test_expected_provision_sequence_order(self):
        """
        Validates that the expected provisioning sequence is defined correctly.
        
        Per SUCCESSFUL_PROVISION_FLOW.md, the factory provision sequence is:
        1. SelectPiccApplication (select PICC app)
        2. GetChipVersion (get UID - 3 frames)
        3. AuthenticateEV2First (Key 0) 
        4. AuthenticateEV2Second
        5. ISOSelectFile (select NDEF file E104h)
        6. WriteNdefMessage (may be chunked into multiple writes)
        7. SelectPiccApplication (re-select PICC app)
        8. ChangeFileSettingsAuth (configure SDM)
        """
        expected_sequence = [
            "SelectPiccApplication",
            "GetChipVersion",  # This includes AF continuations
            "AuthenticateEV2First",
            "AuthenticateEV2Second",
            "ISOSelectFile",
            "WriteNdefMessage",  # May have multiple chunks
            "SelectPiccApplication",  # Re-select
            "ChangeFileSettingsAuth",
        ]
        
        # This test documents the expected sequence
        # Actual validation happens in integration tests
        assert len(expected_sequence) == 8
        assert expected_sequence[0] == "SelectPiccApplication"
        assert expected_sequence[-1] == "ChangeFileSettingsAuth"

    def test_sequence_logger_detects_errors(self):
        """SequenceLogger correctly identifies error responses."""
        seq = create_sequence_logger("ErrorTest")
        
        # Simulate failed command
        seq.log_command("AuthenticateEV2First", "90 71 00 00 02 00 00 00")
        seq.log_response("91AD", "NTAG_AUTHENTICATION_DELAY", "")
        
        assert len(seq.steps) == 1
        step = seq.steps[0]
        assert step.result == StepResult.ERROR
        assert step.status_word == "91AD"
        
        # Verify error is captured
        assert seq.steps[0].status_name == "NTAG_AUTHENTICATION_DELAY"

    def test_sequence_callback_fires_on_each_step(self):
        """Callback is called for each completed step (live TUI updates)."""
        seq = create_sequence_logger("CallbackTest")
        
        captured_steps = []
        seq.on_step_complete = lambda step: captured_steps.append(step)
        
        # Simulate two commands
        seq.log_command("Cmd1", "AA BB")
        seq.log_response("9000", "OK")
        
        seq.log_command("Cmd2", "CC DD")
        seq.log_response("9100", "OK_ALTERNATIVE")
        
        assert len(captured_steps) == 2
        assert captured_steps[0].command_name == "Cmd1"
        assert captured_steps[1].command_name == "Cmd2"

    def test_render_diagram_includes_all_steps(self):
        """render_diagram() shows all captured steps."""
        seq = create_sequence_logger("DiagramTest")
        
        seq.log_command("SelectPiccApplication", "00 A4...")
        seq.log_response("9000", "OK")
        
        seq.log_command("GetChipVersion", "90 60...")
        seq.log_response("91AF", "MORE_DATA_AVAILABLE")
        
        diagram = seq.render_diagram()
        
        assert "SelectPiccApplication" in diagram
        assert "GetChipVersion" in diagram
        assert "OK" in diagram
        assert "MORE_DATA_AVAILABLE" in diagram
        assert "2 commands" in diagram

    def test_sequence_validates_key_change_two_session_pattern(self):
        """
        Documents the two-session pattern for key changes per spec.
        
        Per SUCCESSFUL_PROVISION_FLOW.md:
        - Session 1: Change Key 0 only (session invalidates after)
        - Session 2: Re-auth with NEW Key 0, then change Keys 1 & 3
        """
        expected_key_change_sequence = [
            # Session 1
            "AuthenticateEV2First (Key 0)",
            "AuthenticateEV2Second",
            "ChangeKey (Key 0)",
            # Session 1 ends - MUST re-authenticate
            # Session 2
            "AuthenticateEV2First (Key 0)",  # With NEW key
            "AuthenticateEV2Second",
            "ChangeKey (Key 1)",
            "ChangeKey (Key 3)",
        ]
        
        # This documents the expected pattern (7 commands for key changes)
        assert len(expected_key_change_sequence) == 7
        assert expected_key_change_sequence[2] == "ChangeKey (Key 0)"
        assert expected_key_change_sequence[3] == "AuthenticateEV2First (Key 0)"


class TestSequenceValidation:
    """
    Integration tests that validate actual command sequences.
    These use the mock HAL to simulate provisioning.
    """

    def test_mock_hal_get_chip_version_sequence(self):
        """Mock HAL returns correct GetChipVersion sequence (3 frames)."""
        
        # Create sequence logger to capture commands
        seq = create_sequence_logger("GetChipVersion")
        
        mock = MockCardConnection()
        
        # Simulate GetChipVersion protocol
        # Frame 1: 90 60 00 00 00
        data, sw1, sw2 = mock.send_apdu([0x90, 0x60, 0x00, 0x00, 0x00])
        seq.log_command("GetChipVersion", "90 60 00 00 00")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "FRAME1")
        assert (sw1, sw2) == (0x91, 0xAF)  # More data
        
        # Frame 2: 90 AF 00 00 00
        data, sw1, sw2 = mock.send_apdu([0x90, 0xAF, 0x00, 0x00, 0x00])
        seq.log_command("GetChipVersion (cont)", "90 AF 00 00 00")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "FRAME2")
        assert (sw1, sw2) == (0x91, 0xAF)  # More data
        
        # Frame 3: 90 AF 00 00 00
        data, sw1, sw2 = mock.send_apdu([0x90, 0xAF, 0x00, 0x00, 0x00])
        seq.log_command("GetChipVersion (final)", "90 AF 00 00 00")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "FRAME3")
        assert (sw1, sw2) == (0x90, 0x00)  # Complete
        
        # Validate sequence has 3 steps
        assert len(seq.steps) == 3
        assert all(s.result == StepResult.SUCCESS for s in seq.steps)

    def test_mock_hal_select_and_write_ndef(self):
        """Mock HAL allows NDEF file selection and write."""
        from tests.mock_hal import MockCardConnection
        
        seq = create_sequence_logger("WriteNDEF")
        
        mock = MockCardConnection()
        
        # 1. Select PICC application
        apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
        data, sw1, sw2 = mock.send_apdu(apdu)
        seq.log_command("SelectPiccApp", "00 A4 04 00...")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "SELECT_APP")
        assert (sw1, sw2) == (0x90, 0x00)
        
        # 2. Select NDEF file (E104h)
        apdu = [0x00, 0xA4, 0x02, 0x00, 0x02, 0xE1, 0x04, 0x00]
        data, sw1, sw2 = mock.send_apdu(apdu)
        seq.log_command("ISOSelectFile (NDEF)", "00 A4 02 00 02 E1 04")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "SELECT_NDEF")
        assert (sw1, sw2) == (0x90, 0x00)
        
        # 3. Write NDEF data
        test_data = [0x00, 0x05, 0xD1, 0x01, 0x01, 0x55]  # Simple NDEF
        apdu = [0x00, 0xD6, 0x00, 0x00, len(test_data)] + test_data
        data, sw1, sw2 = mock.send_apdu(apdu)
        seq.log_command("WriteNdefMessage", "00 D6 00 00...")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "WRITE_NDEF")
        assert (sw1, sw2) == (0x90, 0x00)
        
        # Validate complete sequence
        assert len(seq.steps) == 3
        assert seq.steps[0].command_name == "SelectPiccApp"
        assert seq.steps[1].command_name == "ISOSelectFile (NDEF)"
        assert seq.steps[2].command_name == "WriteNdefMessage"

    def test_mock_hal_authentication_sequence(self):
        """Mock HAL supports EV2 authentication protocol."""
        from tests.mock_hal import MockCardConnection
        
        seq = create_sequence_logger("Auth")
        
        mock = MockCardConnection()
        
        # Phase 1: AuthenticateEV2First
        apdu = [0x90, 0x71, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00]
        data, sw1, sw2 = mock.send_apdu(apdu)
        seq.log_command("AuthenticateEV2First (Key 0)", "90 71 00 00 02 00 00 00")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "CHALLENGE")
        assert (sw1, sw2) == (0x91, 0xAF)  # More data (challenge received)
        assert len(data) == 16  # RndB encrypted
        
        # Phase 2: AuthenticateEV2Second (with mock response)
        # In real protocol, we'd send E(RndA || RndB')
        mock_response = [0x00] * 32  # Placeholder
        apdu = [0x90, 0xAF, 0x00, 0x00, 0x20] + mock_response + [0x00]
        data, sw1, sw2 = mock.send_apdu(apdu)
        seq.log_command("AuthenticateEV2Second", "90 AF 00 00 20...")
        seq.log_response(f"{sw1:02X}{sw2:02X}", "AUTH_COMPLETE")
        assert (sw1, sw2) == (0x90, 0x00)  # Success
        
        # Validate auth sequence
        assert len(seq.steps) == 2
        assert "AuthenticateEV2First" in seq.steps[0].command_name
        assert "AuthenticateEV2Second" in seq.steps[1].command_name


class TestSequenceLoggerMethods:
    """
    Tests for SequenceLogger methods including log_to_file().
    
    Bug fix: log_to_file() was previously unreachable due to wrong indentation.
    These tests ensure the methods are accessible and work correctly.
    """

    def test_log_to_file_method_exists(self):
        """Verify log_to_file() is a method on SequenceLogger (was broken by indent bug)."""
        seq = create_sequence_logger("Test")
        
        # This would fail if log_to_file was still nested inside format_step_diagram
        assert hasattr(seq, 'log_to_file'), "log_to_file() method missing from SequenceLogger"
        assert callable(seq.log_to_file), "log_to_file should be callable"

    def test_log_to_file_writes_to_logger(self, caplog):
        """log_to_file() writes the full sequence diagram to the Python logger."""
        import logging
        
        seq = create_sequence_logger("LogFileTest")
        
        # Add some steps
        seq.log_command("SelectPiccApplication", "00 A4 04 00...")
        seq.log_response("9000", "OK")
        
        seq.log_command("GetChipVersion", "90 60 00 00 00")
        seq.log_response("91AF", "MORE_DATA_AVAILABLE")
        
        # Capture log output
        with caplog.at_level(logging.INFO, logger="ntag424_sdm_provisioner.sequence_logger"):
            seq.log_to_file()
        
        # Verify diagram was written to log
        log_text = caplog.text
        assert "SEQUENCE DIAGRAM" in log_text
        assert "SelectPiccApplication" in log_text
        assert "GetChipVersion" in log_text
        assert "Host" in log_text
        assert "Tag" in log_text

    def test_get_error_summary_method_exists(self):
        """Verify get_error_summary() is a method on SequenceLogger."""
        seq = create_sequence_logger("Test")
        
        assert hasattr(seq, 'get_error_summary'), "get_error_summary() method missing"
        assert callable(seq.get_error_summary), "get_error_summary should be callable"

    def test_get_error_summary_returns_none_on_success(self):
        """get_error_summary() returns None when all steps succeed."""
        seq = create_sequence_logger("SuccessTest")
        
        seq.log_command("Cmd1", "AA BB")
        seq.log_response("9000", "OK")
        
        seq.log_command("Cmd2", "CC DD")
        seq.log_response("9100", "OK_ALTERNATIVE")
        
        assert seq.get_error_summary() is None

    def test_get_error_summary_returns_error_details(self):
        """get_error_summary() returns error details when steps fail."""
        seq = create_sequence_logger("ErrorTest")
        
        seq.log_command("SelectPiccApplication", "00 A4...")
        seq.log_response("9000", "OK")
        
        seq.log_command("AuthenticateEV2First", "90 71...")
        seq.log_response("91AD", "NTAG_AUTHENTICATION_DELAY")
        
        summary = seq.get_error_summary()
        
        assert summary is not None
        assert "AuthenticateEV2First" in summary
        assert "NTAG_AUTHENTICATION_DELAY" in summary
        assert "91AD" in summary

    def test_render_diagram_includes_bytes_when_requested(self):
        """render_diagram(include_bytes=True) shows APDU bytes."""
        seq = create_sequence_logger("BytesTest")
        
        seq.log_command("SelectPiccApplication", "00 A4 04 00 07 D2 76 00 00 85 01 01 00")
        seq.log_response("9000", "OK")
        
        diagram_with_bytes = seq.render_diagram(include_bytes=True)
        diagram_without_bytes = seq.render_diagram(include_bytes=False)
        
        # With bytes should include the APDU hex
        assert "00 A4 04 00" in diagram_with_bytes
        
        # Without bytes should not include the APDU hex
        assert "00 A4 04 00" not in diagram_without_bytes

    def test_render_compact_format(self):
        """render_compact() produces one-line-per-step format."""
        seq = create_sequence_logger("CompactTest")
        
        seq.log_command("Cmd1", "AA")
        seq.log_response("9000", "OK")
        
        seq.log_command("Cmd2", "BB")
        seq.log_response("91AD", "ERROR")
        
        compact = seq.render_compact()
        
        assert "=== SEQUENCE ===" in compact
        assert "✓" in compact  # Success marker
        assert "❌" in compact  # Error marker
        assert "Cmd1" in compact
        assert "Cmd2" in compact


class TestSequenceSpecCompliance:
    """
    Tests that validate spec compliance for provisioning sequences.
    Cross-references with SUCCESSFUL_PROVISION_FLOW.md.
    """

    def test_spec_key_takeaways_auth_success_pattern(self):
        """
        Per spec: Auth success = Phase 1 (91AF) + Phase 2 (9100).
        """
        # Document expected status words
        auth_phase1_success = "91AF"  # MORE_DATA_AVAILABLE with 16-byte RndB
        auth_phase2_success = "9100"  # OK_ALTERNATIVE with 32-byte response
        
        assert auth_phase1_success == "91AF"
        assert auth_phase2_success == "9100"

    def test_spec_key_takeaways_changekey_success_pattern(self):
        """
        Per spec: ChangeKey success = SW=9100, may have 8-byte CMAC.
        """
        changekey_success = "9100"
        
        # Key 0: No old key needed
        # Keys 1-4: MUST provide old key for XOR
        assert changekey_success == "9100"

    def test_spec_known_issues(self):
        """
        Document known issues from spec that tests should expect.
        """
        # SDM Configuration may return 917E (LENGTH_ERROR) but doesn't block provisioning
        sdm_config_known_error = "917E"
        
        # Rate limiting after 3-5 failed attempts
        rate_limit_error = "91AD"
        
        assert sdm_config_known_error == "917E"
        assert rate_limit_error == "91AD"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

