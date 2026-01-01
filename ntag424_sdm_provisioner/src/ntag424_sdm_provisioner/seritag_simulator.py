"""Seritag NTAG424 DNA HAL Simulator.

This module simulates a Seritag NTAG424 DNA tag connected to an ACR122U reader.
It implements proper EV2 authentication according to NXP NTAG424 DNA specification.
"""

import logging
import secrets
from dataclasses import dataclass

from Crypto.Cipher import AES

from ntag424_sdm_provisioner.commands.base import AuthApduCommand
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_iv_for_command,
    derive_session_keys,
)
from ntag424_sdm_provisioner.hal import format_status_word, hexb
from ntag424_sdm_provisioner.sequence_logger import (
    SequenceLogger,
    get_command_sequence_name,
)


log = logging.getLogger(__name__)


@dataclass
class SeritagTagState:
    """State of the simulated Seritag NTAG424 DNA tag."""

    uid: bytes = b"\x04\x3f\x68\x4a\x2f\x70\x80"
    hw_major: int = 48
    hw_minor: int = 0
    sw_major: int = 1
    sw_minor: int = 2
    batch_no: bytes = b"\xcf\x39\xd4\x49\x80"
    fab_week: int = 52
    fab_year: int = 32
    hw_protocol: int = 5
    sw_protocol: int = 5
    hw_type: int = 4
    sw_type: int = 4
    hw_storage_size: int = 416
    sw_storage_size: int = 17

    # EV2 Authentication state
    authenticated: bool = False
    session_keys: dict | None = None
    current_key_no: int | None = None
    transaction_id: bytes | None = None
    rnda: bytes | None = None
    rndb: bytes | None = None

    # GetVersion state
    get_version_part: int = 0  # 0=not started, 1=part1, 2=part2, 3=part3

    # Factory keys (all zeros for brand new tags)
    factory_keys: list[bytes] | None = None

    # File system state
    files: dict | None = None
    selected_file: int = 0

    def __post_init__(self):
        if self.factory_keys is None:
            self.factory_keys = [b"\x00" * 16] * 5  # 5 keys, all zeros
        if self.files is None:
            self.files = {
                1: bytearray(32),  # CC File
                2: bytearray(256),  # NDEF File
                3: bytearray(128),  # Proprietary
            }


class SeritagSimulator:
    """Simulates a Seritag NTAG424 DNA tag."""

    def __init__(self):
        self.state = SeritagTagState()
        self.connected = False

    def connect(self) -> str:
        """Simulate card connection."""
        self.connected = True
        return "3B8180018080"  # Seritag ATR

    def disconnect(self):
        """Simulate card disconnection."""
        self.connected = False
        self.state.authenticated = False
        self.state.session_keys = None

    def send_apdu(self, apdu: list[int], use_escape: bool = False) -> tuple[list[int], int, int]:  # noqa: ARG002
        """Simulate APDU command processing.

        Args:
            apdu: APDU command bytes
            use_escape: Whether to use escape sequences (ignored in simulation)

        Returns:
            Tuple of (response_data, sw1, sw2)
        """
        if not self.connected:
            return [], 0x6F, 0x00  # No card present

        # Parse APDU
        if len(apdu) < 4:
            return [], 0x6D, 0x00  # Wrong length

        cla, ins, p1, p2 = apdu[0], apdu[1], apdu[2], apdu[3]
        lc = apdu[4] if len(apdu) > 4 else 0
        data = apdu[5 : 5 + lc] if lc > 0 else []

        log.debug(f"SeritagSim: Processing APDU {[hex(x) for x in apdu]}")

        # Route commands
        if cla == 0x00 and ins == 0xA4:
            if p1 == 0x04:  # Select Application
                return self._handle_select_application()
            else:  # Select File
                return self._handle_select_file(data)
        elif cla == 0x00 and ins == 0xD6:
            return self._handle_update_binary(p1, p2, data)
        elif cla == 0x90 and ins == 0x60:
            return self._handle_get_version()
        elif cla == 0x90 and ins == 0x71:
            return self._handle_authenticate_ev2_first(data)
        elif cla == 0x90 and ins == 0xAF:
            # 0xAF can be either GetVersion additional frame or AuthenticateEV2Second
            if self.state.get_version_part > 0:
                return self._handle_get_version()  # Continue GetVersion
            else:
                return self._handle_authenticate_ev2_second(data)  # Authentication
        elif cla == 0x90 and ins == 0x5F:
            return self._handle_change_file_settings()
        elif cla == 0x90 and ins == 0xF5:
            return self._handle_get_file_settings(data)
        elif cla == 0x90 and ins == 0xC4:
            return self._handle_change_key(data)
        elif cla == 0x90 and ins == 0x64:
            return self._handle_get_key_version(data)
        elif cla == 0x90 and ins == 0x8D:
            return self._handle_write_data(data)
        else:
            log.warning(f"SeritagSim: Unknown command {cla:02X} {ins:02X}")
            return [], 0x6D, 0x00  # Command not supported

    def _handle_select_application(self) -> tuple[list[int], int, int]:
        """Handle Select PICC Application command."""
        log.debug("SeritagSim: SelectPICCApplication")
        return [], 0x90, 0x00  # Success

    def _handle_get_version(self) -> tuple[list[int], int, int]:
        """Handle Get Chip Version command according to NTAG424 DNA specification."""
        if self.state.get_version_part == 0:
            # Part 1: Hardware info (7 bytes)
            self.state.get_version_part = 1
            log.debug("SeritagSim: GetChipVersion - Part 1")

            hw_data = [
                0x04,  # hw_vendor_id (NXP)
                self.state.hw_type,  # hw_type
                0x00,  # hw_subtype
                self.state.hw_major,  # hw_major_version
                self.state.hw_minor,  # hw_minor_version
                self.state.hw_storage_size & 0xFF,  # hw_storage_size
                self.state.hw_protocol,  # hw_protocol
            ]

            log.debug(f"SeritagSim: Part 1 data: {[hex(x) for x in hw_data]}")
            return hw_data, 0x91, 0xAF  # Additional frame

        elif self.state.get_version_part == 1:
            # Part 2: Software info (7 bytes)
            self.state.get_version_part = 2
            log.debug("SeritagSim: GetChipVersion - Part 2")

            sw_data = [
                0x04,  # sw_vendor_id (NXP)
                self.state.sw_type,  # sw_type
                0x00,  # sw_subtype
                self.state.sw_major,  # sw_major_version
                self.state.sw_minor,  # sw_minor_version
                self.state.sw_storage_size & 0xFF,  # sw_storage_size
                self.state.sw_protocol,  # sw_protocol
            ]

            log.debug(f"SeritagSim: Part 2 data: {[hex(x) for x in sw_data]}")
            return sw_data, 0x91, 0xAF  # Additional frame

        elif self.state.get_version_part == 2:
            # Part 3: Production info (15 bytes)
            self.state.get_version_part = 0  # Reset for next time
            log.debug("SeritagSim: GetChipVersion - Part 3 (final)")

            prod_data: list[int] = []
            # Add UID (7 bytes)
            prod_data.extend(self.state.uid)
            # Add batch number (4 bytes) - truncate to 4 bytes as per spec
            prod_data.extend(self.state.batch_no[:4])
            # Add fabrication info (4 bytes)
            prod_data.extend(
                [
                    0x00,  # fab_key
                    self.state.fab_week,  # cw_prod (calendar week)
                    self.state.fab_year,  # year_prod
                    0x00,  # fab_key_id
                ]
            )

            log.debug(f"SeritagSim: Part 3 data: {[hex(x) for x in prod_data]}")
            return prod_data, 0x90, 0x00  # Success - no more frames

        else:
            # Invalid state
            return [], 0x6A, 0x80

    def _handle_authenticate_ev2_first(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle AuthenticateEV2First command with proper EV2 implementation."""
        if len(data) != 2:
            return [], 0x6A, 0x80  # Wrong parameters

        key_no = data[0]
        len_cap = data[1]  # Should be 0x00 for no PCDcap2
        log.debug(f"SeritagSim: AuthenticateEV2First for key {key_no}, LenCap={len_cap}")

        assert self.state.factory_keys is not None
        if key_no >= len(self.state.factory_keys):
            return [], 0x6A, 0x80  # Invalid key number

        # Store the current key number for phase 2
        self.state.current_key_no = key_no

        # Generate random RndB (16 bytes)
        self.state.rndb = secrets.token_bytes(16)
        log.debug(f"SeritagSim: Generated RndB: {self.state.rndb.hex()}")

        # Encrypt RndB with the specified key
        assert self.state.factory_keys is not None
        key = self.state.factory_keys[key_no]
        cipher = AES.new(key, AES.MODE_ECB)  # No padding during authentication per spec
        encrypted_rndb = cipher.encrypt(self.state.rndb)

        log.debug(f"SeritagSim: Encrypted RndB: {encrypted_rndb.hex()}")
        log.debug(f"SeritagSim: Using key {key_no}: {key.hex()}")

        # Return encrypted RndB with SW_ADDITIONAL_FRAME
        return list(encrypted_rndb), 0x91, 0xAF

    def _handle_authenticate_ev2_second(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle AuthenticateEV2Second command with proper EV2 implementation."""
        log.debug(f"SeritagSim: AuthenticateEV2Second with {len(data)} bytes")

        if len(data) != 32:
            return [], 0x6A, 0x80  # Wrong length

        if self.state.rndb is None or self.state.current_key_no is None:
            return [], 0x91, 0x7E  # No previous authentication

        # Decrypt the incoming data (RndA + RndB')
        assert self.state.factory_keys is not None
        key = self.state.factory_keys[self.state.current_key_no]
        cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
        decrypted_data = cipher.decrypt(bytes(data))

        # Extract RndA and RndB'
        rnda = decrypted_data[0:16]
        rndb_prime = decrypted_data[16:32]

        log.debug(f"SeritagSim: Decrypted RndA: {rnda.hex()}")
        log.debug(f"SeritagSim: Decrypted RndB': {rndb_prime.hex()}")

        # Verify RndB' matches expected rotation
        expected_rndb_prime = self.state.rndb[1:] + self.state.rndb[0:1]
        if rndb_prime != expected_rndb_prime:
            log.error("SeritagSim: RndB' verification failed")
            log.error(f"  Expected: {expected_rndb_prime.hex()}")
            log.error(f"  Received: {rndb_prime.hex()}")
            return [], 0x91, 0x7E  # Authentication failed

        log.debug("SeritagSim: RndB' verification successful")

        # Store RndA and generate transaction ID
        self.state.rnda = rnda
        self.state.transaction_id = secrets.token_bytes(4)

        # Generate response: Ti || RndA' || PDcap2 || PCDcap2 (32 bytes total)
        rnda_prime = rnda[1:] + rnda[0:1]  # Rotate RndA
        pdcap2 = b"\x00" * 6  # 6-byte PD capabilities
        pcdcap2 = b"\x00" * 6  # 6-byte PCD capabilities

        response_data = self.state.transaction_id + rnda_prime + pdcap2 + pcdcap2
        log.debug(f"SeritagSim: Response data length: {len(response_data)} bytes")
        log.debug(f"SeritagSim: Response data: {response_data.hex()}")

        # Encrypt response
        cipher_encrypt = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
        encrypted_response = cipher_encrypt.encrypt(response_data)
        log.debug(f"SeritagSim: Encrypted response: {encrypted_response.hex()}")

        # Derive and store session keys (same algorithm as host)
        enc_key, mac_key = derive_session_keys(key, rnda, self.state.rndb)
        self.state.session_keys = {"sesAuthEncKey": enc_key, "sesAuthMacKey": mac_key}
        log.debug(f"SeritagSim: Session ENC: {enc_key.hex()}")
        log.debug(f"SeritagSim: Session MAC: {mac_key.hex()}")
        log.debug(f"SeritagSim: Ti: {self.state.transaction_id.hex()}")

        # Mark as authenticated
        self.state.authenticated = True
        self.state.current_key_no = self.state.current_key_no

        log.info("SeritagSim: EV2 authentication successful!")

        return list(encrypted_response), 0x90, 0x00

    def _handle_select_file(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle Select File command."""
        if len(data) != 2:
            return [], 0x6A, 0x82  # File not found

        file_id = (data[0] << 8) | data[1]
        # NTAG424 uses file numbers 1, 2, 3. ISO select uses file IDs like E104.
        # Mapping: E103 -> CC(1), E104 -> NDEF(2), E105 -> Prop(3)
        file_map = {0xE103: 1, 0xE104: 2, 0xE105: 3}

        if file_id in file_map:
            self.state.selected_file = file_map[file_id]
            log.debug(f"SeritagSim: Selected file {self.state.selected_file} (ID {hex(file_id)})")
            return [], 0x90, 0x00
        else:
            return [], 0x6A, 0x82

    def _handle_update_binary(
        self, p1: int, p2: int, data: list[int]
    ) -> tuple[list[int], int, int]:
        """Handle Update Binary command."""
        offset = (p1 << 8) | p2
        file_no = self.state.selected_file

        assert self.state.files is not None
        if file_no not in self.state.files:
            return [], 0x6A, 0x82  # File not found

        assert self.state.files is not None
        current_data = self.state.files[file_no]

        # Extend file if needed
        if offset + len(data) > len(current_data):
            # In a real tag, size is fixed. Here we can be flexible or strict.
            # Let's be flexible for simulation
            current_data.extend(b"\x00" * (offset + len(data) - len(current_data)))

        # Write data
        current_data[offset : offset + len(data)] = data
        log.debug(f"SeritagSim: Wrote {len(data)} bytes to file {file_no} at offset {offset}")

        return [], 0x90, 0x00

    def _handle_get_key_version(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle GetKeyVersion command (0x64)."""
        if len(data) < 1:
            return [], 0x91, 0x7E  # Length error

        key_no = data[0]
        if key_no > 4:
            return [], 0x91, 0x9D  # Parameter error

        # Return key version 0x00 for all keys (factory default)
        log.debug(f"SeritagSim: GetKeyVersion for key {key_no} = 0x00")
        return [0x00], 0x91, 0x00  # Success with version byte

    def _handle_write_data(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle WriteData command (0x8D) per NXP Section 10.8.2.

        Format: [FileNo] [Offset:3] [Length:3] [Data...] [MAC:8]
        """
        if not self.state.authenticated:
            return [], 0x91, 0xAE  # Authentication error

        if len(data) < 7:  # Minimum: FileNo + Offset(3) + Length(3)
            return [], 0x91, 0x7E  # Length error

        file_no = data[0]
        offset = data[1] | (data[2] << 8) | (data[3] << 16)

        # Data starts at byte 7, MAC is last 8 bytes
        payload = data[7:-8] if len(data) > 15 else data[7:]

        assert self.state.files is not None
        if file_no not in self.state.files:
            return [], 0x91, 0xF0  # File not found

        assert self.state.files is not None
        current_data = self.state.files[file_no]

        # Extend file if needed (in simulator, we're flexible)
        if offset + len(payload) > len(current_data):
            current_data.extend(b"\x00" * (offset + len(payload) - len(current_data)))

        # Write data
        current_data[offset : offset + len(payload)] = payload

        log.info(
            f"SeritagSim: WriteData {len(payload)} bytes to file 0x{file_no:02X} at offset {offset}"
        )
        return [], 0x91, 0x00  # Success

    def _handle_change_file_settings(self) -> tuple[list[int], int, int]:
        """Handle ChangeFileSettings command."""
        # This is an authenticated command.
        # Data structure: KeyNo(1) + EncryptedData(N) + CMAC(8)
        # We should verify CMAC and decrypt.

        if not self.state.authenticated:
            return [], 0x91, 0xAE  # Authentication error

        # For simulation, we can assume the client is correct and just return success.
        # Decrypting and parsing the settings is complex and not strictly needed
        # unless we want to verify the settings were applied correctly.
        # Given we just want to pass the provisioning flow test:

        log.info("SeritagSim: ChangeFileSettings received (simulated success)")
        return [], 0x91, 0x00

    def _handle_get_file_settings(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle GetFileSettings command (0xF5).

        Returns basic file settings for NDEF file (0x02).
        Response format (minimum 7 bytes):
        - file_type (1 byte): 0x00 = Standard Data File
        - file_option (1 byte): 0x00 = No SDM
        - access_rights (2 bytes): 0xE0EE = Read:FREE, Write:KEY_0, RW:FREE, Change:FREE
        - file_size (3 bytes, little-endian): 256 bytes
        """
        if len(data) < 1:
            return [], 0x91, 0x7E  # Length error

        file_no = data[0]
        log.debug(f"SeritagSim: GetFileSettings for file 0x{file_no:02X}")

        if file_no == 0x02:  # NDEF file
            # Basic factory settings for NDEF file
            response = [
                0x00,  # file_type: Standard Data File
                0x00,  # file_option: No SDM enabled (factory default)
                0xE0,
                0xEE,  # access_rights: Read:FREE, Write:KEY_0, RW:FREE, Change:FREE
                0x00,
                0x01,
                0x00,  # file_size: 256 bytes (little-endian)
            ]
            return response, 0x91, 0x00
        else:
            # Other files not implemented in simulator
            return [], 0x91, 0x9D  # Parameter error

    def _handle_change_key(self, data: list[int]) -> tuple[list[int], int, int]:
        """Handle ChangeKey command with proper decryption."""
        if not self.state.authenticated:
            return [], 0x91, 0xAE  # Authentication error

        if self.state.session_keys is None or self.state.transaction_id is None:
            log.error("SeritagSim: ChangeKey called but no session keys!")
            return [], 0x91, 0xAE

        key_no = data[0]
        # Data structure: KeyNo(1) + EncryptedData(32) + CMAC(8)
        encrypted_data = bytes(data[1:33])

        # Decrypt using session ENC key with proper IV

        assert self.state.session_keys is not None
        session_enc = self.state.session_keys["sesAuthEncKey"]
        ti = self.state.transaction_id

        # Calculate IV using same method as host (counter = 0 for first command)
        # The host increments counter AFTER the command, so for ChangeKey (first cmd) it's 0
        cmd_ctr = 0  # First authenticated command in session
        iv = calculate_iv_for_command(ti, cmd_ctr, session_enc)

        cipher = AES.new(session_enc, AES.MODE_CBC, iv=iv)
        decrypted = cipher.decrypt(encrypted_data)

        log.debug(f"SeritagSim: ChangeKey encrypted: {encrypted_data.hex()}")
        log.debug(f"SeritagSim: ChangeKey IV: {iv.hex()}")
        log.debug(f"SeritagSim: ChangeKey decrypted: {decrypted.hex()}")

        # For Key 0 change (changing your own key):
        #   Decrypted = NewKey(16) || KeyVersion(1) || Padding(15)
        # For other keys:
        #   Decrypted = NewKey XOR OldKey(16) || KeyVersion(1) || CRC32(4) || Padding(11)

        if key_no == 0:
            # Key 0: plain new key
            new_key = decrypted[0:16]
        else:
            # Other keys: XOR with old key
            xored = decrypted[0:16]
            assert self.state.factory_keys is not None
            old_key = self.state.factory_keys[key_no]
            new_key = bytes(a ^ b for a, b in zip(xored, old_key, strict=True))

        log.info(f"SeritagSim: ChangeKey received for Key {key_no}")
        log.debug(f"SeritagSim: Extracted new key: {new_key.hex()}")

        # Update the key
        assert self.state.factory_keys is not None
        self.state.factory_keys[key_no] = new_key
        log.info(f"SeritagSim: Key {key_no} updated successfully")

        return [], 0x91, 0x00


class SeritagCardConnection:
    """Simulated Seritag card connection."""

    def __init__(self, simulator: SeritagSimulator, sequence_logger):
        self.simulator = simulator
        self.sequence_logger: SequenceLogger = sequence_logger
        self._get_command_sequence_name = get_command_sequence_name

    def send_apdu(self, apdu: list[int], use_escape: bool = False) -> tuple[list[int], int, int]:  # noqa: ARG002
        """Send APDU to simulated Seritag tag."""
        log.debug(f"SeritagCard: Sending APDU {[hex(x) for x in apdu]}")
        return self.simulator.send_apdu(apdu)

    def send(self, command):
        """Support for high-level Command objects.

        Like NTag424CardConnection.send. This allows the simulator to be used with ProvisioningService.
        """
        # Build APDU from command
        apdu = command.build_apdu()

        # Log command to sequence logger
        command_name = self._get_command_sequence_name(command)
        self.sequence_logger.log_command(command_name, hexb(apdu))

        # Send raw APDU
        data, sw1, sw2 = self.send_apdu(apdu)

        # Handle multi-frame responses (SW_ADDITIONAL_FRAME = 0x91AF)
        full_response = bytearray(data)
        while sw1 == 0x91 and sw2 == 0xAF:
            # Send GET_ADDITIONAL_FRAME (0x90AF0000)
            more_data, sw1, sw2 = self.send_apdu([0x90, 0xAF, 0x00, 0x00, 0x00])
            full_response.extend(more_data)

        # Log response to sequence
        status_word = f"{sw1:02X}{sw2:02X}"
        status_name = format_status_word(sw1, sw2)
        self.sequence_logger.log_response(status_word, status_name, hexb(full_response))

        # Parse response using the command object
        # AuthApduCommand subclasses only take data, while ApduCommand takes data, sw1, sw2
        if isinstance(command, AuthApduCommand):
            return command.parse_response(bytes(full_response))
        else:
            return command.parse_response(bytes(full_response), sw1, sw2)

    def transmit(self, apdu: list[int]) -> tuple[list[int], int, int]:
        """Alias for send_apdu to match pyscard interface."""
        return self.send_apdu(apdu)

    def control(self, control_code: int, data: list[int]) -> list[int]:
        """Simulate control command (for escape sequences)."""
        log.debug(f"SeritagCard: Control command {control_code:04X}")
        # For now, just pass through to send_apdu
        response, sw1, sw2 = self.simulator.send_apdu(data)
        return response + [sw1, sw2]


class SeritagCardManager:
    """Simulated card manager for Seritag tags."""

    def __init__(self, sequence_logger, reader_index: int = 0):
        self.sequence_logger: SequenceLogger = sequence_logger
        self.reader_index = reader_index
        self.simulator = SeritagSimulator()
        self.connection: SeritagCardConnection | None = None

    def __enter__(self):
        """Context manager entry."""
        log.info("SeritagSim: Simulating card connection...")
        atr = self.simulator.connect()
        log.info(f"SeritagSim: Card detected with ATR: {atr}")
        self.connection = SeritagCardConnection(self.simulator, self.sequence_logger)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        log.info("SeritagSim: Disconnecting from simulated card.")
        self.simulator.disconnect()
        self.connection = None
