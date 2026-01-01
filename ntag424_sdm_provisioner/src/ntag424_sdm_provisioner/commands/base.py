"""Base classes and constants for APDU commands."""

from __future__ import annotations

import logging
from abc import ABC
from types import TracebackType
from typing import TYPE_CHECKING, Any

from ntag424_sdm_provisioner.constants import (
    ErrorCategory,
    StatusWord,
    StatusWordPair,
    describe_status_word,
    get_error_category,
)
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_cmac,
    calculate_iv_for_command,
    encrypt_key_data,
)
from ntag424_sdm_provisioner.hal import NTag424CardConnection


if TYPE_CHECKING:
    from ntag424_sdm_provisioner.crypto.auth_session import Ntag424AuthSession

log = logging.getLogger(__name__)


class Ntag424Error(Exception):
    """Base exception for all NTAG424 errors."""


class ApduError(Ntag424Error):
    """Raised when an APDU command returns a non-OK status word."""

    def __init__(self, message: str, sw1: int, sw2: int):
        self.sw1 = sw1
        self.sw2 = sw2
        self.status_word = StatusWord.from_bytes(sw1, sw2)
        self.category = get_error_category(self.status_word)

        # Build detailed error message
        sw_desc = describe_status_word(sw1, sw2)
        full_message = f"{message}\n  {sw_desc}"

        super().__init__(full_message)

    def is_authentication_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.category == ErrorCategory.AUTHENTICATION

    def is_permission_error(self) -> bool:
        """Check if this is a permission error."""
        return self.category == ErrorCategory.PERMISSION

    def is_not_found_error(self) -> bool:
        """Check if this is a not found error."""
        return self.category == ErrorCategory.NOT_FOUND


class AuthenticationRateLimitError(ApduError):
    """Authentication rate-limited (0x91AD) - wait between attempts."""

    def __init__(self, command_name: str = "Authentication"):
        super().__init__(
            f"{command_name} rate-limited.\n"
            "  Solution: Wait 5 seconds between authentication attempts",
            0x91,
            0xAD,
        )


class CommandLengthError(ApduError):
    """Command length error (0x917E) - payload format issue."""

    def __init__(self, command_name: str = "Command"):
        super().__init__(
            f"{command_name} length error.\n"
            "  Known Issue: ChangeFileSettings payload format\n"
            "  Status: Under investigation",
            0x91,
            0x7E,
        )


class CommandNotAllowedError(ApduError):
    """Command not allowed (0x911C) - precondition not met."""

    def __init__(self, command_name: str = "Command"):
        super().__init__(
            f"{command_name} not allowed.\n"
            "  Possible causes:\n"
            "    - File not in correct state\n"
            "    - Authentication required but not provided",
            0x91,
            0x1C,
        )


class SecurityNotSatisfiedError(ApduError):
    """Security condition not satisfied (0x6985) - authentication issue."""

    def __init__(self, command_name: str = "Command"):
        super().__init__(
            f"{command_name} security not satisfied.\n"
            "  Possible causes:\n"
            "    - Authentication required\n"
            "    - Wrong key used\n"
            "    - File not selected",
            0x69,
            0x85,
        )


class AuthenticationError(Ntag424Error):
    """Authentication failed."""


class PermissionError(Ntag424Error):
    """Permission denied for operation."""


class ConfigurationError(Ntag424Error):
    """Invalid configuration."""


class CommunicationError(Ntag424Error):
    """Communication with card/reader failed."""


class AuthenticatedConnection:
    """Wraps a card connection with an authenticated session.

    This class acts as a context manager and handles automatic CMAC
    application for all authenticated commands.

    Usage:
        with AuthenticateEV2(key, key_no=0)(connection) as auth_conn:
            # Use auth_conn.send() for authenticated commands
            auth_conn.send(ChangeKey(0, new_key, old_key))
    """

    def __init__(self, connection: NTag424CardConnection, session: Ntag424AuthSession):
        """Initialize AuthenticatedConnection.

        Args:
        connection: The underlying card connection.
        session: The authenticated session with session keys.
        """
        self.connection = connection
        self.session = session
        log.debug(f"AuthenticatedConnection initialized with session: {session}")

    def __enter__(self) -> AuthenticatedConnection:
        """Enter context manager."""
        log.debug("Entering AuthenticatedConnection context")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""
        log.debug(f"Exiting AuthenticatedConnection context (exc_type={exc_type})")
        # Session cleanup could go here if needed

    def send_apdu(self, apdu: list[int], use_escape: bool = False) -> tuple[list[int], int, int]:
        """Send plain APDU without CMAC (for files with CommMode.PLAIN).

        This delegates directly to the underlying connection.

        Args:
            apdu: APDU bytes to send
            use_escape: Whether to use escape command

        Returns:
            Tuple of (data, sw1, sw2)
        """
        log.debug(f"Sending plain APDU: {bytes(apdu).hex()}")
        return self.connection.send_apdu(apdu, use_escape=use_escape)

    def apply_cmac(self, cmd_header: bytes, cmd_data: bytes) -> bytes:
        """Apply CMAC to command data for authenticated commands.

        Delegates to session.apply_cmac() (for now).
        Will be moved directly here in next step.

        Args:
            cmd_header: 4-byte APDU command header [CLA INS P1 P2]
            cmd_data: Command data payload (without CMAC)

        Returns:
            cmd_data + CMAC (8 bytes appended)
        """
        log.debug(f"Applying CMAC with header {cmd_header.hex()} to data of len {len(cmd_data)}")
        return self.session.apply_cmac(cmd_header, cmd_data)

    def encrypt_data(self, plaintext: bytes) -> bytes:
        """Encrypt data using session encryption key.

        Delegates to session.encrypt_data() (for now).
        Uses AES-128 CBC mode with IV derived from command counter.

        Args:
            plaintext: Data to encrypt (will be PKCS7 padded)

        Returns:
            Encrypted data
        """
        log.debug(f"Encrypting {len(plaintext)} bytes of plaintext.")
        encrypted = self.session.encrypt_data(plaintext)
        log.debug(f"  -> Encrypted data is {len(encrypted)} bytes.")
        return encrypted

    def decrypt_data(self, ciphertext: bytes) -> bytes:
        """Decrypt data using session encryption key.

        Delegates to session.decrypt_data() (for now).

        Args:
            ciphertext: Encrypted data

        Returns:
            Decrypted and unpadded plaintext
        """
        log.debug(f"Decrypting {len(ciphertext)} bytes of ciphertext.")
        decrypted = self.session.decrypt_data(ciphertext)
        log.debug(f"  -> Decrypted data is {len(decrypted)} bytes.")
        return decrypted

    def encrypt_and_mac_with_header(
        self, plaintext: bytes, cmd: int, cmd_header_data: bytes
    ) -> bytes:
        """Encrypt data with PKCS7 padding and apply CMAC including cmd_header_data.

        For commands like ChangeFileSettings where:
        - CmdHeader (e.g., FileNo) is unencrypted but MUST be in CMAC
        - Plaintext needs PKCS7 padding

        Per Arduino DNA_CalculateDataEncAndCMACt():
        - CmdHeader is NOT encrypted (sent as plain byte)
        - CmdHeader IS included in CMAC: Cmd || Ctr || Ti || CmdHeader || Encrypted

        Args:
            plaintext: Data to encrypt (will be PKCS7 padded)
            cmd: Command byte (e.g., 0x5F)
            cmd_header_data: Unencrypted header (e.g., FileNo) for CMAC

        Returns:
            Encrypted data + CMAC (8 bytes) - WITHOUT cmd_header_data
            (caller will add cmd_header_data to APDU separately)
        """
        log.debug("TRACE: encrypt_and_mac_with_header called")
        log.debug(f"  - Plaintext ({len(plaintext)} bytes): {plaintext.hex()}")
        log.debug(f"  - Cmd: 0x{cmd:02X}")
        log.debug(f"  - Header Data: {cmd_header_data.hex()}")

        # 1. Encrypt the plaintext with PKCS7 padding
        encrypted = self.encrypt_data(plaintext)
        log.debug(f"  - Intermediate encrypted ({len(encrypted)} bytes): {encrypted.hex()}")

        # 2. Build CMAC input: CmdHeader + encrypted data
        # Per Arduino: CMAC over Cmd || Ctr || Ti || CmdHeader || EncryptedData
        cmd_data_for_mac = cmd_header_data + encrypted
        cmd_header = bytes([0x90, cmd, 0x00, 0x00])

        # 3. Apply CMAC (returns cmd_data_for_mac + CMAC)
        with_cmac = self.apply_cmac(cmd_header, cmd_data_for_mac)

        # 4. Remove cmd_header_data from result (it goes in APDU separately)
        # Result = encrypted + CMAC (no cmd_header_data)
        encrypted_with_mac = with_cmac[len(cmd_header_data) :]
        log.debug(f"  - Final result ({len(encrypted_with_mac)} bytes): {encrypted_with_mac.hex()}")

        return encrypted_with_mac

    def encrypt_and_mac(self, plaintext: bytes, cmd_header: bytes) -> bytes:
        """Convenience method: Encrypt data and apply CMAC in one call.

        This combines encrypt_data() and apply_cmac() for CommMode.FULL commands.

        Args:
            plaintext: Data to encrypt
            cmd_header: APDU command header (CLA INS P1 P2)

        Returns:
            Encrypted data + CMAC (8 bytes)

        Example:
            # For ChangeFileSettings
            encrypted_with_mac = auth_conn.encrypt_and_mac(
                plaintext=settings_data,
                cmd_header=bytes([0x90, 0x5F, 0x00, 0x00])
            )
        """
        # 1. Encrypt the plaintext
        encrypted = self.encrypt_data(plaintext)

        # 2. Apply CMAC to encrypted data
        encrypted_with_mac = self.apply_cmac(cmd_header, encrypted)

        return encrypted_with_mac

    def send(self, command):
        """Send an authenticated command with transparent crypto (NEW PATTERN).

        This is the preferred way to send authenticated commands:
            response = auth_conn.send(ChangeKey(0, new_key, old_key))

        The connection handles ALL crypto operations:
        - IV calculation
        - Encryption (with proper padding)
        - CMAC generation and truncation
        - Response decryption

        Args:
            command: AuthApduCommand to send

        Returns:
            Command-specific response (parsed by command.parse_response())
        """
        log = logging.getLogger(__name__)

        # Get components from command
        cmd = command.get_command_byte()
        p1 = command.get_p1()
        p2 = command.get_p2()
        unencrypted_header = command.get_unencrypted_header()
        plaintext = command.build_command_data()

        log.debug(f"[AUTH_CONN] Sending command 0x{cmd:02X} (P1={p1:02X}, P2={p2:02X})")
        log.debug(f"[AUTH_CONN]   Unencrypted header: {unencrypted_header.hex()}")
        log.debug(f"[AUTH_CONN]   Plaintext ({len(plaintext)} bytes): {plaintext.hex()}")
        assert self.session.session_keys is not None
        log.debug(f"[AUTH_CONN]   Session counter BEFORE: {self.session.session_keys.cmd_counter}")
        log.debug(f"[AUTH_CONN]   Session Ti: {self.session.session_keys.ti.hex()}")

        # Check if command needs encryption (polymorphic)
        needs_encryption = command.needs_encryption()

        # Apply crypto based on command requirements
        if not needs_encryption:
            # MAC only (no encryption) - for ChangeFileSettings with PLAIN files
            # CMAC over: Cmd || Ctr || Ti || UnencryptedHeader || Plaintext
            cmd_data_for_mac = unencrypted_header + plaintext
            cmd_header_bytes = bytes([0x90, cmd, 0x00, 0x00])
            with_mac = self.apply_cmac(cmd_header_bytes, cmd_data_for_mac)
            # Strip header (added to APDU separately)
            encrypted_with_mac = with_mac[len(unencrypted_header) :]
            log.debug("[AUTH_CONN] MAC-only mode (no encryption)")
        elif len(plaintext) % 16 == 0:
            # Block-aligned: Use no-padding encryption (ChangeKey)
            encrypted_with_mac = self.encrypt_and_mac_no_padding(
                plaintext=plaintext, cmd=cmd, cmd_header_data=unencrypted_header
            )
        else:
            # Not block-aligned: Use PKCS7 padding with encryption
            encrypted_with_mac = self.encrypt_and_mac_with_header(
                plaintext=plaintext, cmd=cmd, cmd_header_data=unencrypted_header
            )

        log.debug(
            f"[AUTH_CONN]   Crypto payload ({len(encrypted_with_mac)} bytes): {encrypted_with_mac.hex()}"
        )

        # Build APDU: CLA CMD P1 P2 LC [UnencryptedHeader] EncryptedData MAC LE
        data_len = len(unencrypted_header) + len(encrypted_with_mac)

        apdu = [
            command.get_cla(),
            cmd,
            p1,
            p2,
            data_len,
            *unencrypted_header,
            *encrypted_with_mac,
            0x00,  # LE
        ]

        log.debug(f"[AUTH_CONN]   Full APDU to send: {bytes(apdu).hex()}")

        # Send via underlying connection
        data, sw1, sw2 = self.connection.send_apdu(apdu, use_escape=command.use_escape)

        # Check status word
        log.debug(
            f"[AUTH_CONN] Response: SW={sw1:02X}{sw2:02X}, data={len(data) if data else 0} bytes"
        )

        if (sw1, sw2) == (0x91, 0x00):
            # SUCCESS! Increment counter now (Arduino does this AFTER successful response)
            assert self.session.session_keys is not None
            self.session.session_keys.cmd_counter += 1
            log.debug(
                f"[AUTH_CONN] Command successful, counter incremented to: {self.session.session_keys.cmd_counter}"
            )

            # CRITICAL: Check if this was a ChangeKey for Key 0 (PICC Master Key)
            if cmd == 0xC4 and len(unencrypted_header) > 0 and unencrypted_header[0] == 0x00:
                log.critical("=" * 70)
                log.critical("[AUTH_CONN] KEY 0 (PICC MASTER KEY) WAS CHANGED!")
                log.critical("[AUTH_CONN] Current session is NOW INVALID")
                log.critical("[AUTH_CONN] All subsequent commands will fail with 91AE")
                log.critical("[AUTH_CONN] Must re-authenticate with NEW Key 0 to continue")
                assert self.session.session_keys is not None
                log.critical(
                    f"[AUTH_CONN] Current session: Ti={self.session.session_keys.ti.hex()}, Ctr={self.session.session_keys.cmd_counter}"
                )
                log.critical("=" * 70)
        else:
            # FAILURE! Don't increment counter (card didn't increment either)
            assert self.session.session_keys is not None
            log.warning(
                f"[AUTH_CONN] Command failed with {sw1:02X}{sw2:02X}, counter NOT incremented (stays at {self.session.session_keys.cmd_counter})"
            )
            log.warning(
                f"[AUTH_CONN] Session state: Ti={self.session.session_keys.ti.hex()}, Ctr={self.session.session_keys.cmd_counter}"
            )
            log.warning(
                f"[AUTH_CONN] Session ENC key: {self.session.session_keys.session_enc_key.hex()}"
            )
            log.warning(
                f"[AUTH_CONN] Session MAC key: {self.session.session_keys.session_mac_key.hex()}"
            )

            if (sw1, sw2) == (0x91, 0xAE):
                log.error("[AUTH_CONN] 91AE = AUTHENTICATION_ERROR")
                log.error("[AUTH_CONN] Possible causes:")
                log.error("[AUTH_CONN]   1. Session is invalid (Key 0 was changed)")
                log.error("[AUTH_CONN]   2. CMAC verification failed")
                log.error("[AUTH_CONN]   3. Wrong session keys")

            # Raise exception for failed command
            raise ApduError(f"{command} failed", sw1, sw2)

        # Handle response data (only reached on success)
        if data:
            # Check if data is CMAC-only (8 bytes) or encrypted data
            if len(data) == 8:
                # CMAC-only response (e.g., ChangeKey)
                # TODO: Verify CMAC
                # For now, just return empty (CMAC verified by successful SW)
                decrypted = b""
            elif len(data) % 16 == 0:
                # Encrypted response - decrypt it
                decrypted = self.decrypt_data(bytes(data))
            else:
                # Unexpected length
                log.warning(f"[AUTH_CONN] Unexpected response length: {len(data)} bytes")
                decrypted = b""
        else:
            decrypted = b""

        # Let command parse decrypted response
        return command.parse_response(decrypted)

    def encrypt_and_mac_no_padding(
        self, plaintext: bytes, cmd: int, cmd_header_data: bytes
    ) -> bytes:
        """Encrypt and MAC for data that's already block-aligned (no PKCS7 padding).

        Used by ChangeKey where data is pre-padded to 32 bytes with 0x80 padding.

        Per AN12196 Table 26:
        1. Calculate IVc = E(KSesAuthENC, zero_iv, A5 5A || TI || CmdCtr || zeros)
        2. Encrypt: E(KSesAuthENC, IVc, plaintext)
        3. CMAC over: Cmd || CmdCtr || TI || CmdHeader || Encrypted
        4. Truncate CMAC to even-numbered bytes
        5. Increment counter

        Args:
            plaintext: Pre-padded data (must be multiple of 16 bytes!)
            cmd: Command byte (e.g., 0xC4 for ChangeKey)
            cmd_header_data: Command-specific header (e.g., KeyNo)

        Returns:
            Encrypted data + CMAC (8 bytes)
        """
        log = logging.getLogger(__name__)

        log.debug("=" * 70)
        log.debug("[CHANGEKEY] encrypt_and_mac_no_padding called")
        log.debug(f"[CHANGEKEY]   Command: 0x{cmd:02X}")
        log.debug(f"[CHANGEKEY]   Header data: {cmd_header_data.hex()}")
        log.debug(f"[CHANGEKEY]   Plaintext ({len(plaintext)} bytes): {plaintext.hex()}")

        if len(plaintext) % 16 != 0:
            raise ValueError(f"Data must be block-aligned (got {len(plaintext)} bytes)")

        # Get current counter and session info
        assert self.session.session_keys is not None
        cmd_ctr = self.session.session_keys.cmd_counter
        ti = self.session.session_keys.ti
        session_enc_key = self.session.session_keys.session_enc_key
        session_mac_key = self.session.session_keys.session_mac_key

        log.debug(f"[CHANGEKEY]   Counter: {cmd_ctr}")
        log.debug(f"[CHANGEKEY]   Ti: {ti.hex()}")
        log.debug(f"[CHANGEKEY]   Session ENC key: {session_enc_key.hex()}")
        log.debug(f"[CHANGEKEY]   Session MAC key: {session_mac_key.hex()}")

        # Step 1: Calculate IV using VERIFIED crypto
        iv = calculate_iv_for_command(ti, cmd_ctr, session_enc_key)
        log.debug(f"[CHANGEKEY]   IV (encrypted): {iv.hex()}")

        # Step 2: Encrypt data using VERIFIED crypto
        encrypted = encrypt_key_data(plaintext, iv, session_enc_key)
        log.debug(f"[CHANGEKEY]   Encrypted ({len(encrypted)} bytes): {encrypted.hex()}")

        # Step 3: Calculate CMAC using VERIFIED crypto
        mac = calculate_cmac(cmd, cmd_ctr, ti, cmd_header_data, encrypted, session_mac_key)
        log.debug(f"[CHANGEKEY]   CMAC (truncated): {mac.hex()}")

        # DON'T increment counter yet - Arduino increments AFTER successful response!
        # Counter will be incremented in send() after verifying SW=9100

        result = encrypted + mac
        log.debug(f"[CHANGEKEY]   Result ({len(result)} bytes): {result.hex()}")
        log.debug("=" * 70)

        return result

    def send_authenticated_apdu(
        self, cmd_header: bytes, cmd_data: bytes, use_escape: bool = False
    ) -> tuple[bytes, int, int]:
        """Send an authenticated APDU with automatic CMAC application.

        Handles:
        1. Applies CMAC to command data
        2. Sends APDU
        3. Handles continuation frames with CMAC
        4. Checks status word

        Args:
            cmd_header: Command header (CLA INS P1 P2)
            cmd_data: Command data to be authenticated
            use_escape: Whether to use escape command for reader

        Returns:
            Tuple of (response_data, sw1, sw2)

        Raises:
            ApduError: If status word indicates error
        """
        # Apply CMAC to command data (uses self method now)
        authenticated_data = self.apply_cmac(cmd_header, cmd_data)

        # Build APDU: header + Lc + data + Le
        apdu = list(cmd_header) + [len(authenticated_data)] + list(authenticated_data) + [0x00]

        # Send initial command
        data, sw1, sw2 = self.connection.send_apdu(apdu, use_escape=use_escape)

        # Handle continuation frames with CMAC
        full_response = bytearray(data)
        while (sw1, sw2) == StatusWordPair.SW_ADDITIONAL_FRAME:
            log.debug(
                f"Authenticated command: {StatusWordPair.SW_ADDITIONAL_FRAME}, fetching next frame..."
            )
            # GET_ADDITIONAL_FRAME with CMAC
            af_header = bytes([0x90, 0xAF, 0x00, 0x00])
            af_data = self.apply_cmac(af_header, b"")
            af_apdu = list(af_header) + [len(af_data)] + list(af_data) + [0x00]

            data, sw1, sw2 = self.connection.send_apdu(af_apdu, use_escape=use_escape)
            full_response.extend(data)

        # Check final status
        if (sw1, sw2) not in [StatusWordPair.SW_OK, StatusWordPair.SW_OK_ALTERNATIVE]:
            raise ApduError("Authenticated command failed", sw1, sw2)

        return bytes(full_response), sw1, sw2

    def send_write_chunked_authenticated(
        self,
        cla: int,
        ins: int,
        offset: int,
        data: bytes,
        chunk_size: int = 52,
        use_escape: bool = False,
    ) -> tuple[int, int]:
        """Send authenticated write with automatic chunking and crypto per chunk.

        For authenticated writes to files with CommMode.MAC or CommMode.FULL.
        Each chunk is independently encrypted (if CommMode.FULL) and MACed.

        Args:
            cla: Class byte (e.g., 0x90 for native NTAG424)
            ins: Instruction byte (e.g., 0x8D for WriteData)
            offset: Starting offset for write
            data: Data to write (will be encrypted/MACed per chunk)
            chunk_size: Max plaintext bytes per chunk (default 52)
            use_escape: Whether to use escape mode

        Returns:
            Final (sw1, sw2) status word
        """
        log = logging.getLogger(__name__)

        data_length = len(data)
        current_offset = offset

        log.debug(
            f"[AUTH_WRITE] Chunked authenticated write: {data_length} bytes, chunk_size={chunk_size}"
        )
        assert self.session.session_keys is not None
        log.debug(f"[AUTH_WRITE] Session counter at start: {self.session.session_keys.cmd_counter}")

        while current_offset < offset + data_length:
            chunk_start = current_offset - offset
            chunk_end = min(chunk_start + chunk_size, data_length)
            chunk = data[chunk_start:chunk_end]

            # Build command data: offset + chunk
            # For WriteData: [FileNo] [Offset(3)] [Length(3)] [Data]
            # This is command-specific - caller should prepare properly

            # Apply crypto to this chunk
            cmd_header = bytes([cla, ins, 0x00, 0x00])

            # For FULL mode: encrypt then MAC
            # For MAC mode: just MAC
            # Assume FULL mode for now (can be parameterized later)
            encrypted_chunk = self.encrypt_data(chunk)
            authenticated_chunk = self.apply_cmac(cmd_header, encrypted_chunk)

            # Build APDU
            p1 = (current_offset >> 8) & 0x7F
            p2 = current_offset & 0xFF

            apdu = [cla, ins, p1, p2, len(authenticated_chunk)] + list(authenticated_chunk) + [0x00]

            log.debug(
                f"[AUTH_WRITE] Chunk: offset={current_offset}, plaintext={len(chunk)}, encrypted+MAC={len(authenticated_chunk)}"
            )

            # Send chunk
            _, sw1, sw2 = self.connection.send_apdu(apdu, use_escape=use_escape)

            # Check for errors
            if (sw1, sw2) not in [(0x90, 0x00), (0x91, 0x00)]:
                log.error(
                    f"[AUTH_WRITE] Chunk failed at offset {current_offset}: SW={sw1:02X}{sw2:02X}"
                )
                return sw1, sw2

            # Increment counter after successful write
            assert self.session.session_keys is not None
            self.session.session_keys.cmd_counter += 1
            log.debug(
                f"[AUTH_WRITE] Counter incremented to {self.session.session_keys.cmd_counter}"
            )

            current_offset += len(chunk)

        log.debug(f"[AUTH_WRITE] Complete: {data_length} bytes written")
        return sw1, sw2

    def __str__(self) -> str:
        return f"AuthenticatedConnection(connection={self.connection})"


class ApduCommand(ABC):
    """Abstract base class for all APDU commands.

    This class holds the APDU structure and logic but delegates the actual
    sending of the command to the connection object.
    """

    def __init__(self, use_escape: bool = False) -> None:
        """Initialize ApduCommand.

        Args:
        use_escape: Whether to wrap the APDU in a reader-specific escape
                    command (required for some readers like the ACR122U).
        """
        self.use_escape = use_escape

    # execute() method removed - use connection.send(command) pattern instead
    # Special commands (like AuthenticateEV2) can still define execute() for custom behavior

    def build_apdu(self) -> list[int]:
        """Build the APDU bytes for this command.

        Used by connection.send(command) pattern.
        Override this in subclasses to support the new pattern.

        Returns:
            Complete APDU as list of integers
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't support connection.send() yet. "
            "Use command.execute(connection) instead."
        )

    def parse_response(self, data: bytes, sw1: int, sw2: int) -> Any:
        """Parse the response from the card.

        Used by connection.send(command) pattern.
        Override this in subclasses to support the new pattern.

        Args:
            data: Response data from card.
            sw1: Status word 1 from the card.
            sw2: Status word 2 from the card.

        Returns:
            Command-specific response object
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't support connection.send() yet. "
            "Use command.execute(connection) instead."
        )

    def send_command(
        self, connection: NTag424CardConnection, apdu: list[int], allow_alternative_ok: bool = True
    ) -> tuple[list[int], int, int]:
        """High-level command send with automatic multi-frame handling and error checking.

        This method:
        1. Sends the APDU directly via connection.send_apdu()
        2. Automatically handles SW_ADDITIONAL_FRAME (0x91AF) responses by sending
           GET_ADDITIONAL_FRAME (0x90AF0000) commands until complete
        3. Checks that final status is SW_OK or SW_OK_ALTERNATIVE
        4. Raises ApduError if status indicates failure
        5. Returns complete response data and final status word

        Args:
            connection: Card connection
            apdu: APDU command bytes to send
            allow_alternative_ok: If True, accept both SW_OK (0x9000) and
                                 SW_OK_ALTERNATIVE (0x9100) as success

        Returns:
            Tuple of (data, sw1, sw2) where:
                - data: Complete response data (all frames concatenated)
                - sw1, sw2: Final status word bytes

        Raises:
            ApduError: If final status word indicates error
        """
        # Send initial command directly to connection
        data, sw1, sw2 = connection.send_apdu(apdu, use_escape=self.use_escape)

        # Collect full response if multiple frames
        full_response = bytearray(data)

        # Handle additional frames (0x91AF)
        while (sw1, sw2) == StatusWordPair.SW_ADDITIONAL_FRAME:
            log.debug(
                f"Additional frame requested ({StatusWordPair.SW_ADDITIONAL_FRAME}), fetching next frame..."
            )
            # GET_ADDITIONAL_FRAME: CLA=0x90, INS=0xAF, P1=0x00, P2=0x00, Le=0x00
            get_af_apdu = [0x90, 0xAF, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.send_apdu(get_af_apdu, use_escape=self.use_escape)
            full_response.extend(data)

        # Check final status word
        success_codes = [StatusWordPair.SW_OK]
        if allow_alternative_ok:
            success_codes.append(StatusWordPair.SW_OK_ALTERNATIVE)

        if (sw1, sw2) not in success_codes:
            # Use reflection to get command class name
            command_name = self.__class__.__name__

            # Raise specific exception based on status word
            if (sw1, sw2) == (0x91, 0xAD):
                raise AuthenticationRateLimitError(command_name)
            elif (sw1, sw2) == (0x91, 0x7E):
                raise CommandLengthError(command_name)
            elif (sw1, sw2) == (0x91, 0x1C):
                raise CommandNotAllowedError(command_name)
            elif (sw1, sw2) == (0x69, 0x85):
                raise SecurityNotSatisfiedError(command_name)
            else:
                # Generic error
                raise ApduError(f"{command_name} failed", sw1, sw2)

        return list(full_response), sw1, sw2


class AuthApduCommand(ABC):
    """Base class for authenticated APDU commands.

    These commands require an AuthenticatedConnection and handle crypto transparently.

    New pattern (preferred):
        # Command provides plaintext, connection handles crypto
        auth_conn.send(ChangeKey(0, new_key, old_key))

    Old pattern (deprecated):
        # Command manages crypto explicitly
        ChangeKey(0, new_key, old_key).execute(auth_conn)

    Commands must implement:
        - get_command_byte() -> int: Command byte (e.g., 0xC4 for ChangeKey)
        - build_command_data() -> bytes: Plaintext command data
        - parse_response() -> result: Parse decrypted response
    """

    # Class attribute for duck-typing check (avoids circular import in hal.py)
    is_auth_command = True

    def __init__(self, use_escape: bool = False) -> None:
        """Initialize ApduCommand.

        Args:
        use_escape: Whether to wrap in reader escape command.
        """
        self.use_escape = use_escape

    def get_command_byte(self) -> int:
        """Get the command byte for this command.

        Override this in subclasses to support connection.send(command).

        Returns:
            Command byte (e.g., 0xC4 for ChangeKey)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't support auth_conn.send() yet. "
            "Use command.execute(auth_conn) instead."
        )

    def get_cla(self) -> int:
        """Get CLA byte for command (default 0x90 for native commands)."""
        return 0x90

    def get_p1(self) -> int:
        """Get P1 byte for command (default 0)."""
        return 0x00

    def get_p2(self) -> int:
        """Get P2 byte for command (default 0)."""
        return 0x00

    def get_unencrypted_header(self) -> bytes:
        """Get unencrypted header data that goes after command byte.

        This data is included in CMAC but NOT encrypted.
        Default: empty (most commands have no unencrypted header)

        Returns:
            Unencrypted header bytes (e.g., KeyNo for ChangeKey, FileNo for ChangeFileSettings)
        """
        return b""

    def needs_encryption(self) -> bool:
        """Indicate if command data should be encrypted.

        Returns:
            True if data should be encrypted (default for most commands)
            False if MAC-only (e.g., ChangeFileSettings for PLAIN file mode)
        """
        return True  # Default: encrypt

    def build_command_data(self) -> bytes:
        """Build the plaintext command data to be encrypted.

        Connection will handle encryption/CMAC transparently.
        Override this in subclasses to support connection.send(command).

        Returns:
            Plaintext command data for encryption (e.g., 32-byte KeyData for ChangeKey)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't support auth_conn.send() yet. "
            "Use command.execute(auth_conn) instead."
        )

    def parse_response(self, data: bytes) -> Any:
        """Parse the decrypted response data.

        Override this in subclasses to support connection.send(command).

        Args:
            data: Decrypted response data

        Returns:
            Command-specific response object
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't support auth_conn.send() yet. "
            "Use command.execute(auth_conn) instead."
        )

    # execute() method removed - use auth_conn.send(command) pattern instead
    # Commands define build_command_data() and parse_response() only
