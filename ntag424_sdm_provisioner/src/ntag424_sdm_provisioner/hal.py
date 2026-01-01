from __future__ import annotations

import logging
import os
import threading
from collections.abc import Iterator
from types import TracebackType

from smartcard.CardConnection import CardConnection
from smartcard.CardMonitoring import CardMonitor, CardObserver

# ✅ Import the necessary low-level functions and constants
from smartcard.scard import (
    SCARD_SCOPE_USER,
    SCARD_STATE_PRESENT,
    SCARD_STATE_UNAWARE,
    SCardEstablishContext,
    SCardGetStatusChange,
    SCardReleaseContext,
)
from smartcard.System import readers

from ntag424_sdm_provisioner.constants import StatusWord
from ntag424_sdm_provisioner.sequence_logger import SequenceLogger, get_command_sequence_name


# Lazy import to avoid circular dependency: hal → commands/base → hal


# --- PC/SC Constants (Corrected Cross-Platform Import) ---
try:
    # This is the correct import for Windows systems
    from smartcard.scard import SCARD_CTL_CODE

    IOCTL_CCID_ESCAPE = SCARD_CTL_CODE(3500)
except ImportError:
    # This is the correct import for PCSC-Lite (Linux/macOS)
    IOCTL_CCID_ESCAPE = 3500


def hexb(data: bytes | list[int]) -> str:
    """Format bytes or list of ints as hex string (no smartcard dependency)."""
    if isinstance(data, (bytes, list, tuple)):
        return " ".join(f"{b:02X}" for b in data)
    else:
        return str(data)


def format_status_word(sw1: int, sw2: int) -> str:
    """Format status word with enum name for readability."""
    sw_value = (sw1 << 8) | sw2
    try:
        sw_enum = StatusWord(sw_value)
        return f"{sw_enum.name} (0x{sw1:02X}{sw2:02X})"
    except ValueError:
        # Not a known status word
        return f"0x{sw1:02X}{sw2:02X}"


log = logging.getLogger("hal")


class NTag242ConnectionError(Exception):
    """Custom exception for connection failures."""


class NTag242NoReadersError(Exception):
    """Custom exception for when no readers are found."""


class ApduError(Exception):
    """Custom exception for APDU command failures."""


class CardManager:
    """A robust context manager that uses a direct, blocking call to wait for a card tap.

    Establishes a clean connection.

    Requires a SequenceLogger for command tracing (explicit DI).
    """

    def __init__(
        self,
        sequence_logger: SequenceLogger,
        reader_index: int = 0,
        timeout_seconds: int = 15,
    ):
        self.sequence_logger = sequence_logger
        self.reader_index = reader_index
        self.timeout_ms = timeout_seconds * 1000
        self.connection: CardConnection | None = None
        self.context = None

    def __enter__(self) -> NTag424CardConnection:
        try:
            # 1. Establish a PC/SC context. This is the handle to the resource manager.
            hresult, self.context = SCardEstablishContext(SCARD_SCOPE_USER)
            if hresult != 0:
                raise NTag242ConnectionError(f"Failed to establish PC/SC context: {hresult}")

            all_readers = readers()
            if not all_readers:
                raise NTag242NoReadersError("No PC/SC readers found.")

            reader = all_readers[self.reader_index]
            log.info(f"Using reader '{reader}'. Waiting for a card tap...")

            # 2. Get initial state
            reader_states = [(str(reader), SCARD_STATE_UNAWARE)]
            hresult, current_states = SCardGetStatusChange(self.context, 0, reader_states)
            if hresult != 0:
                raise NTag242ConnectionError(f"Initial SCardGetStatusChange failed: {hresult}")

            (reader_name, event_state, atr) = current_states[0]

            # 3. If not present, wait for change
            if not (event_state & SCARD_STATE_PRESENT):
                log.info("Waiting for card tap...")
                # Update expected state to current state to wait for change
                reader_states = [(reader_name, event_state)]
                hresult, current_states = SCardGetStatusChange(
                    self.context, self.timeout_ms, reader_states
                )

                if hresult != 0:
                    # Timeout or error
                    raise NTag242ConnectionError(f"Wait for card failed (Timeout?): {hresult}")

                (reader_name, event_state, atr) = current_states[0]

            # 4. Check if a card was actually presented.
            if not (event_state & SCARD_STATE_PRESENT):
                raise NTag242ConnectionError("Timeout: No card was presented.")

            log.info(f"Card detected with ATR: {hexb(atr)}. Connecting...")

            # 5. Now, create a standard connection and connect to it.
            self.connection = reader.createConnection()
            self.connection.connect()
            log.info("Successfully connected to the card.")

            return NTag424CardConnection(self.connection, self.sequence_logger)

        except Exception as e:
            # Ensure context is released on failure
            self.__exit__(None, None, None)
            log.error(f"Failed to establish card connection: {e}")
            raise NTag242ConnectionError(f"Failed to connect: {e}") from e

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.connection:
            log.info("Disconnecting from the card.")
            self.connection.disconnect()
        # 6. Release the PC/SC context to clean up resources.
        if self.context:
            SCardReleaseContext(self.context)


# --- NTag424CardConnection (with send_apdu method restored) ---
class NTag424CardConnection:
    """A wrapper for a pyscard CardConnection.

    Handles the low-level details of APDU transmission.

    Requires a SequenceLogger for command tracing (explicit DI).
    """

    def __init__(self, connection: CardConnection, sequence_logger: SequenceLogger):
        self.connection = connection
        self.sequence_logger = sequence_logger

    def __str__(self) -> str:
        return str(self.connection.getReader())

    def wait_for_atr(self) -> list[int]:
        atr = wait_for_card_atr()
        return list(atr) if atr else []

    def check_response(
        self,
        sw1: int,
        sw2: int,
        expected: StatusWord = StatusWord.OK,
        error_message: str = "Command failed",
    ) -> None:
        """Check response status word and raise ApduError if not expected.

        Args:
            sw1: Status word 1
            sw2: Status word 2
            expected: Expected status word (default: OK)
            error_message: Error message prefix

        Raises:
            ApduError: If status word doesn't match expected
        """
        sw = StatusWord.from_bytes(sw1, sw2)

        if sw != expected:
            raise NTag242NoReadersError(error_message, sw1, sw2)

    def send(self, command):
        """Send a command to the card (NEW PATTERN).

        This is the preferred way to send commands:
            response = connection.send(GetVersion())

        Automatically handles:
        - Multi-frame responses (0x91AF)
        - Chunked writes for large data (UpdateBinary > 52 bytes)
        - Sequence logging for debugging

        Args:
            command: ApduCommand to send

        Returns:
            Command-specific response (parsed by command.parse_response())
        """
        # Build APDU from command
        apdu = command.build_apdu()

        # Get command name for sequence logging (Sequenceable protocol or class name)
        command_name = get_command_sequence_name(command)

        # Detect if this is a large write that needs chunking
        # UpdateBinary (INS=0xD6) with data > 52 bytes
        if self._needs_chunking(apdu):
            log.debug("Detected large write - using automatic chunking")
            sw1, sw2 = self._send_chunked_write(apdu, command.use_escape)
            # Return parsed response (no data on write)
            return command.parse_response(b"", sw1, sw2)

        # Standard single-APDU path - send_apdu handles sequence logging
        data, sw1, sw2 = self.send_apdu(
            apdu, use_escape=command.use_escape, command_name=command_name
        )

        # Handle multi-frame responses (SW_ADDITIONAL_FRAME = 0x91AF)
        full_response = bytearray(data)
        while sw1 == 0x91 and sw2 == 0xAF:
            # Send GET_ADDITIONAL_FRAME (0x90AF0000) - logged as separate step
            more_data, sw1, sw2 = self.send_apdu(
                [0x90, 0xAF, 0x00, 0x00, 0x00], command_name=f"{command_name} (cont)"
            )
            full_response.extend(more_data)

        # Let command parse the response
        # Check if this is an AuthApduCommand by duck typing (to avoid circular import)
        if hasattr(command, 'is_auth_command') and command.is_auth_command:
            return command.parse_response(bytes(full_response))
        else:
            return command.parse_response(bytes(full_response), sw1, sw2)

    def _needs_chunking(self, apdu: list) -> bool:
        """Check if APDU needs chunking (UpdateBinary with large data)."""
        if len(apdu) < 5:
            return False

        # Check if UpdateBinary command (INS=0xD6)
        if apdu[1] != 0xD6:
            return False

        # Extract data length (everything after 5-byte header)
        data_len = len(apdu) - 5

        # Chunk if data > 52 bytes (safe for most readers)
        return data_len > 52

    def _send_chunked_write(self, apdu: list, use_escape: bool) -> tuple[int, int]:
        """Send large write in chunks using existing send_write_chunked()."""
        # Extract components from APDU
        cla = apdu[0]
        ins = apdu[1]
        offset = (apdu[2] << 8) | apdu[3]
        data = bytes(apdu[5:])  # Data starts after 5-byte header

        log.debug(f"Chunking write: {len(data)} bytes at offset {offset}")

        # Use existing chunked write logic
        return self.send_write_chunked(
            cla=cla, ins=ins, offset=offset, data=data, chunk_size=52, use_escape=use_escape
        )

    def send_write_chunked(
        self,
        cla: int,
        ins: int,
        offset: int,
        data: bytes,
        chunk_size: int = 52,
        use_escape: bool = False,
    ) -> tuple[int, int]:
        """Send write command with automatic chunking for large data.

        For ISO UpdateBinary (0xD6) or similar write commands that use offset addressing.
        Splits large writes into multiple chunks to respect reader limits.

        This handles UNAUTHENTICATED writes. For authenticated writes, use
        AuthenticatedConnection which would apply crypto to each chunk.

        Args:
            cla: Class byte (e.g., 0x00 for ISO)
            ins: Instruction byte (e.g., 0xD6 for UpdateBinary)
            offset: Starting offset for write
            data: Data to write
            chunk_size: Max bytes per chunk (default 52 for most readers)
            use_escape: Whether to use escape mode

        Returns:
            Final (sw1, sw2) status word
        """
        data_length = len(data)
        current_offset = offset

        log.debug(f"  >> Chunked write: {data_length} bytes, chunk_size={chunk_size}")

        while current_offset < offset + data_length:
            chunk_start = current_offset - offset
            chunk_end = min(chunk_start + chunk_size, data_length)
            chunk = data[chunk_start:chunk_end]

            # P1[7]=0: P1-P2 encodes 15-bit offset
            p1 = (current_offset >> 8) & 0x7F
            p2 = current_offset & 0xFF

            apdu = [cla, ins, p1, p2, len(chunk)] + list(chunk)

            log.debug(f"  >> Chunk: offset={current_offset}, size={len(chunk)}")
            _, sw1, sw2 = self.send_apdu(apdu, use_escape=use_escape)

            # Check for errors
            if (sw1, sw2) not in [(0x90, 0x00), (0x91, 0x00)]:
                log.error(
                    f"  << Write chunk failed at offset {current_offset}: SW={sw1:02X}{sw2:02X}"
                )
                return sw1, sw2

            current_offset += len(chunk)

        log.debug(f"  >> Chunked write complete: {data_length} bytes written")
        return sw1, sw2  # Return final status

    def send_apdu(
        self,
        apdu: list[int],
        use_escape: bool = False,
        command_name: str | None = None,
    ) -> tuple[list[int], int, int]:
        """Sends a raw APDU command to the card and returns the response.

        This method contains the pyscard-specific logic, abstracting it away
        from the command classes.

        Args:
            apdu: Raw APDU bytes
            use_escape: Use escape mode for ACR122U readers
            command_name: Optional name for sequence logging (auto-detected if None)
        """
        log.debug(f"  >> C-APDU: {hexb(apdu)}")

        # Auto-detect command name from APDU if not provided
        if command_name is None:
            command_name = self._detect_command_name(apdu)

        # Log command to sequence logger immediately (before sending)
        self.sequence_logger.log_command(command_name, hexb(apdu))

        # Environment overrides for escape mode behavior
        if os.environ.get("FORCE_NO_ESCAPE", "").strip() == "1":
            use_escape = False
            log.debug("  >> Mode override: FORCED transmit() (no-escape)")
        elif os.environ.get("FORCE_ESCAPE", "").strip() == "1":
            use_escape = True
            log.debug("  >> Mode override: FORCED control() (escape)")

        if use_escape:
            try:
                # Use the low-level control() for readers that need it (e.g., ACR122U)
                resp = self.connection.control(IOCTL_CCID_ESCAPE, apdu)

                if len(resp) < 2:
                    raise NTag242NoReadersError(
                        f"APDU response via control() was too short: [{hexb(resp)}]"
                    )

                # Manually parse the raw response
                data, sw1, sw2 = resp[:-2], resp[-2], resp[-1]
                log.debug(f"  << R-APDU (Control): {hexb(data)} [{format_status_word(sw1, sw2)}]")

                # Log response to sequence logger immediately
                self.sequence_logger.log_response(
                    f"{sw1:02X}{sw2:02X}", format_status_word(sw1, sw2), hexb(data)
                )
                return list(data), sw1, sw2
            except Exception as e:
                log.error(f"Error during control() command: {e}")
                log.error("Will Retry with transmit()")
                return self.send_apdu(apdu, use_escape=False, command_name=command_name)
        else:
            # Use the standard transmit() for compliant readers
            data, sw1, sw2 = self.connection.transmit(apdu)
            log.debug(f"  << R-APDU (Transmit): {hexb(data)} [{format_status_word(sw1, sw2)}]")

            # Log response to sequence logger immediately
            self.sequence_logger.log_response(
                f"{sw1:02X}{sw2:02X}", format_status_word(sw1, sw2), hexb(data)
            )
            return data, sw1, sw2

    def _detect_command_name(self, apdu: list[int]) -> str:
        """Auto-detect command name from APDU bytes for sequence logging."""
        if len(apdu) < 2:
            return "Unknown"

        cla, ins = apdu[0], apdu[1]

        # ISO commands (CLA=00)
        if cla == 0x00:
            iso_commands = {
                0xA4: "ISOSelect",
                0xD6: "ISOUpdateBinary",
                0xB0: "ISOReadBinary",
            }
            return iso_commands.get(ins, f"ISO_{ins:02X}")

        # NTAG commands (CLA=90)
        if cla == 0x90:
            ntag_commands = {
                0x60: "GetChipVersion",
                0x71: "AuthenticateEV2First",
                0xAF: "GetAdditionalFrame",
                0x77: "AuthenticateEV2NonFirst",
                0x5F: "ChangeFileSettings",
                0xC4: "ChangeKey",
                0x64: "GetKeyVersion",
                0xF5: "SetConfiguration",
                0x6F: "GetFileIds",
                0xF6: "GetFileSettings",
            }
            return ntag_commands.get(ins, f"NTAG_{ins:02X}")

        return f"CMD_{cla:02X}_{ins:02X}"


class _AtrObserver(CardObserver):
    def __init__(self, target_reader: str | None = None):
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._atr: bytes | None = None
        self._target_reader = target_reader

    def update(self, cards):
        try:
            added = cards[0] if isinstance(cards, (list, tuple)) and len(cards) >= 1 else cards
            for card in added or []:
                reader_name = getattr(card, "reader", None) or getattr(card, "readerName", None)
                if self._target_reader and reader_name is not None:
                    if self._target_reader not in str(reader_name):
                        continue

                atr_val = getattr(card, "atr", None)
                if atr_val is None:
                    get_atr = getattr(card, "getATR", None)
                    if callable(get_atr):
                        atr_val = get_atr()

                if atr_val is None:
                    continue

                if isinstance(atr_val, (list, tuple)):
                    atr_bytes = bytes(atr_val)
                elif isinstance(atr_val, bytes):
                    atr_bytes = atr_val
                else:
                    try:
                        atr_bytes = bytes(atr_val)
                    except Exception:
                        continue

                with self._lock:
                    self._atr = atr_bytes
                    self._event.set()
                    return
        except Exception:
            return

    def wait_for_next_atr(self, timeout: float | None = None) -> bytes | None:
        got = self._event.wait(timeout)
        if not got:
            return None
        with self._lock:
            atr = self._atr
            self._atr = None
            self._event.clear()
        return atr


def watch_atrs(target_reader: str | None = None) -> Iterator[bytes]:
    monitor = CardMonitor()
    obs = _AtrObserver(target_reader=target_reader)
    monitor.addObserver(obs)
    try:
        while True:
            atr = obs.wait_for_next_atr(timeout=None)
            if atr is None:
                continue
            yield atr
    finally:
        monitor.deleteObserver(obs)


def wait_for_card_atr(
    target_reader: str | None = None, timeout: float | None = None
) -> bytes | None:
    """Block until the next card is presented (or timeout) and return ATR bytes.

    Returns None on timeout.
    """
    monitor = CardMonitor()
    obs = _AtrObserver(target_reader=target_reader)
    monitor.addObserver(obs)
    try:
        return obs.wait_for_next_atr(timeout=timeout)
    finally:
        monitor.deleteObserver(obs)
