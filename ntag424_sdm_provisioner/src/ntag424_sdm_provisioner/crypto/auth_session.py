import logging

from Crypto.Cipher import AES  # nosec
from Crypto.Hash import CMAC  # nosec
from Crypto.Random import get_random_bytes  # nosec

from ntag424_sdm_provisioner.commands.base import (
    ApduCommand,
    ApduError,
    AuthenticatedConnection,
    AuthenticationError,
)
from ntag424_sdm_provisioner.constants import (
    AuthenticationChallengeResponse,
    AuthenticationResponse,
    AuthSessionKeys,
    StatusWordPair,
)

# Import verified crypto primitives - ALL auth crypto now uses these verified functions
from ntag424_sdm_provisioner.crypto.crypto_primitives import (
    calculate_iv_for_command,
    decrypt_auth_response,
    decrypt_rndb,
    derive_session_keys,
    encrypt_auth_response,
    rotate_left,
)
from ntag424_sdm_provisioner.hal import NTag424CardConnection


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AuthenticateEV2First(ApduCommand):
    """Begins the first phase of an EV2 authentication with an AES key.

    This command requests an encrypted challenge (RndB) from the tag.
    Response SW=91AF is expected (means "additional frame" but is actually success).
    """

    def __init__(self, key_no: int):
        super().__init__(use_escape=True)
        self.key_no = key_no

    def __str__(self) -> str:
        return f"AuthenticateEV2First(key_no=0x{self.key_no:02X})"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return f"AuthenticateEV2First (Key {self.key_no})"

    @property
    def sequence_description(self) -> str:
        return f"Start EV2 authentication with key {self.key_no}"

    def get_sequence_params(self) -> dict[str, str]:
        return {"key_no": str(self.key_no)}

    # --- ApduCommand Implementation ---
    def execute(self, connection: NTag424CardConnection) -> AuthenticationChallengeResponse:
        """Execute Phase 1 of EV2 authentication.

        Args:
            connection: Card connection

        Returns:
            AuthenticationChallengeResponse with encrypted RndB

        Raises:
            ApduError: If Phase 1 fails
        """
        # Format: CLA CMD P1 P2 Lc KeyNo LenCap Le
        # LenCap=00h means no PCDcap2 present
        apdu = [0x90, 0x71, 0x00, 0x00, 0x02, self.key_no, 0x00, 0x00]
        log.debug(f"AuthenticateEV2First APDU: {[hex(x) for x in apdu]}")
        log.debug(f"Requesting challenge for key number: {self.key_no}")

        # Special case: This command expects SW_ADDITIONAL_FRAME as success, not error
        # So we can't use send_command() and must call connection.send_apdu() directly
        data, sw1, sw2 = connection.send_apdu(apdu, use_escape=self.use_escape)
        log.debug(f"Response: data={len(data)} bytes, SW={sw1:02X}{sw2:02X}")

        if (sw1, sw2) != StatusWordPair.SW_ADDITIONAL_FRAME:
            log.error(f"AuthenticateEV2First failed with SW={sw1:02X}{sw2:02X}")
            log.error(f"Expected {StatusWordPair.SW_ADDITIONAL_FRAME}, got SW={sw1:02X}{sw2:02X}")
            raise ApduError("AuthenticateEV2First failed", sw1, sw2)

        # Phase 1 returns SW=91AF with encrypted RndB (16 bytes)
        encrypted_rndb = bytes(data)

        # Verify we got exactly 16 bytes
        if len(encrypted_rndb) != 16:
            log.warning(f"Phase 1 returned {len(encrypted_rndb)} bytes, expected 16")
            if len(encrypted_rndb) < 16:
                raise ApduError(
                    f"Phase 1 response too short: {len(encrypted_rndb)} bytes", sw1, sw2
                )

        log.debug(f"Successfully received challenge: {encrypted_rndb.hex().upper()}")
        return AuthenticationChallengeResponse(key_no_used=self.key_no, challenge=encrypted_rndb)


class AuthenticateEV2Second(ApduCommand):
    """Completes the second phase of an EV2 authentication.

    Sends the encrypted response (RndA || RndB') to the tag and receives
    the encrypted card response containing Ti and RndA'.
    """

    def __init__(self, data_to_card: bytes):
        super().__init__(use_escape=True)
        if len(data_to_card) != 32:
            raise ValueError("Authentication data for phase two must be 32 bytes.")
        self.data_to_card = data_to_card

    def __str__(self) -> str:
        return f"AuthenticateEV2Second(data=<{len(self.data_to_card)} bytes>)"

    # --- Sequenceable Protocol ---
    @property
    def sequence_name(self) -> str:
        return "AuthenticateEV2Second"

    @property
    def sequence_description(self) -> str:
        return "Complete EV2 authentication (send response)"

    def get_sequence_params(self) -> dict[str, str]:
        return {"data_len": str(len(self.data_to_card))}

    # --- ApduCommand Implementation ---
    def execute(self, connection: NTag424CardConnection) -> bytes:
        """Execute Phase 2 of EV2 authentication.

        Args:
            connection: Card connection

        Returns:
            Encrypted card response (32 bytes: Ti || RndA' || PDcap2 || PCDcap2)

        Raises:
            ApduError: If Phase 2 fails
        """
        apdu = [0x90, 0xAF, 0x00, 0x00, len(self.data_to_card), *self.data_to_card, 0x00]
        # send_command() handles multi-frame and status checking automatically
        full_response, _sw1, _sw2 = self.send_command(connection, apdu)
        return bytes(full_response)  # Return the card's encrypted response data


class Ntag424AuthSession:
    """Handles EV2 authentication and session key management for NTAG424 DNA.

    Manages the two-phase authentication protocol and derives session keys
    for subsequent encrypted/MACed commands.
    """

    def __init__(self, key: bytes):
        """Initialize authentication session.

        Args:
            key: 16-byte AES-128 key (factory default = all zeros)

        Raises:
            ValueError: If key is not 16 bytes
        """
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes (AES-128)")

        self.key = key
        self.session_keys: AuthSessionKeys | None = None
        self.authenticated = False

    def authenticate(self, connection: NTag424CardConnection, key_no: int = 0) -> AuthSessionKeys:
        """Perform complete EV2 authentication (both phases).

        Args:
            connection: Active card connection
            key_no: Key number to authenticate with (0-4)

        Returns:
            AuthSessionKeys with derived session keys

        Raises:
            ApduError: If authentication fails
        """
        log.info(f"Starting EV2 authentication with key {key_no:02X}")

        # Phase 1: Get encrypted RndB from card
        encrypted_rndb = self._phase1_get_challenge(connection, key_no)

        # Phase 2: Complete authentication and derive keys
        self.session_keys = self._phase2_authenticate(connection, encrypted_rndb)

        self.authenticated = True
        log.info("✅ Authentication successful")
        log.info("=" * 70)
        log.info("[NEW SESSION CREATED]")
        assert self.session_keys is not None
        log.info(f"  Ti: {self.session_keys.ti.hex()}")
        log.info(f"  Counter: {self.session_keys.cmd_counter}")
        log.info(f"  Session ENC: {self.session_keys.session_enc_key.hex()}")
        log.info(f"  Session MAC: {self.session_keys.session_mac_key.hex()}")
        log.info("=" * 70)
        log.debug(f"{self.session_keys}")

        return self.session_keys

    def _phase1_get_challenge(self, connection: NTag424CardConnection, key_no: int) -> bytes:
        """Phase 1: Send authentication request and get encrypted RndB.

        Args:
            connection: Card connection
            key_no: Key number to use

        Returns:
            Encrypted RndB (16 bytes)
        """
        log.debug(f"Phase 1: Requesting challenge for key {key_no:02X}")
        log.debug(f"Using authentication key: {self.key.hex().upper()}")

        cmd = AuthenticateEV2First(key_no=key_no)
        log.debug(f"Sending AuthenticateEV2First command: {cmd}")

        try:
            response = cmd.execute(connection)
            log.debug(f"Received encrypted RndB: {response.challenge.hex()}")
            log.debug(f"Challenge length: {len(response.challenge)} bytes")
            return response.challenge
        except Exception as e:
            log.error(f"Phase 1 failed: {e}")
            log.error(f"Key used: {self.key.hex().upper()}")
            log.error(f"Key number: {key_no}")
            raise

    def _phase2_authenticate(
        self, connection: NTag424CardConnection, encrypted_rndb: bytes
    ) -> AuthSessionKeys:
        """Phase 2: Decrypt RndB, generate RndA, authenticate, derive keys.

        Args:
            connection: Card connection
            encrypted_rndb: 16-byte encrypted challenge from card

        Returns:
            Derived session keys
        """
        log.debug("Phase 2: Processing challenge and deriving keys")

        # 1. Decrypt RndB from card
        rndb = self._decrypt_rndb(encrypted_rndb)
        log.debug(f"Decrypted RndB: {rndb.hex()}")

        # 2. Rotate RndB using verified crypto_primitives
        rndb_rotated = rotate_left(rndb)
        log.debug(f"[crypto_primitives] rotate_left(RndB): {rndb_rotated.hex()}")

        # 3. Generate random RndA
        rnda = get_random_bytes(16)
        log.debug(f"Generated RndA: {rnda.hex()}")

        # 4. Encrypt RndA + RndB_rotated and send to card
        response_data = self._encrypt_response(rnda, rndb_rotated)

        cmd = AuthenticateEV2Second(data_to_card=response_data)
        encrypted_response = cmd.execute(connection)

        # 5. Parse and decrypt the card's response
        auth_response = self._parse_card_response(encrypted_response)

        # 6. Verify RndA' matches expected rotation
        expected_rnda_rotated = rotate_left(rnda)
        if auth_response.rnda_rotated != expected_rnda_rotated:
            raise AuthenticationError(
                f"RndA' verification failed. Expected: {expected_rnda_rotated.hex()}, Got: {auth_response.rnda_rotated.hex()}"
            )

        log.debug("✅ RndA' verification successful")
        log.debug(f"Card response: {auth_response}")

        # 7. Derive session keys using actual Ti from card
        session_keys = self._derive_session_keys(rnda, rndb, auth_response.ti)

        return session_keys

    def _decrypt_rndb(self, encrypted_rndb: bytes) -> bytes:
        """Decrypt RndB received from card using verified crypto_primitives.

        Args:
            encrypted_rndb: 16 bytes encrypted challenge

        Returns:
            Decrypted RndB (16 bytes)
        """
        result = decrypt_rndb(encrypted_rndb, self.key)
        log.debug(f"[crypto_primitives] decrypt_rndb: {encrypted_rndb.hex()} -> {result.hex()}")
        return result

    def _encrypt_response(self, rnda: bytes, rndb_rotated: bytes) -> bytes:
        """Encrypt authentication response (RndA + RndB') using verified crypto_primitives.

        Args:
            rnda: 16-byte random A generated by reader
            rndb_rotated: 16-byte rotated RndB

        Returns:
            Encrypted 32-byte response
        """
        result = encrypt_auth_response(rnda, rndb_rotated, self.key)
        log.debug(f"[crypto_primitives] encrypt_auth_response: {len(result)} bytes")
        return result

    def _parse_card_response(self, encrypted_response: bytes) -> AuthenticationResponse:
        """Parse and decrypt the card's authentication response.

        The card responds with: E(Kx, Ti || RndA' || PDcap || PCDcap)

        Args:
            encrypted_response: Encrypted response from card

        Returns:
            Parsed authentication response

        Raises:
            AuthenticationError: If response parsing fails
        """
        log.debug(f"Parsing card response: {encrypted_response.hex()}")

        # Decrypt using verified crypto_primitives
        decrypted_response = decrypt_auth_response(encrypted_response, self.key)
        log.debug(f"[crypto_primitives] decrypt_auth_response: {decrypted_response.hex()}")

        # Parse the response structure
        # Format: Ti (4 bytes) || RndA' (16 bytes) || PDcap2 (6 bytes) || PCDcap2 (6 bytes)
        if len(decrypted_response) < 32:  # Expected: Ti(4) + RndA'(16) + PDcap2(6) + PCDcap2(6)
            raise AuthenticationError(f"Card response too short: {len(decrypted_response)} bytes")

        ti = decrypted_response[0:4]
        rnda_rotated = decrypted_response[4:20]
        pdcap2 = decrypted_response[20:26]
        pcdcap2 = decrypted_response[26:32]

        log.debug(f"Parsed - Ti: {ti.hex()}, RndA': {rnda_rotated.hex()}")
        log.debug(f"Parsed - PDcap2: {pdcap2.hex()}, PCDcap2: {pcdcap2.hex()}")

        return AuthenticationResponse(
            ti=ti, rnda_rotated=rnda_rotated, pdcap=pdcap2, pcdcap=pcdcap2
        )

    def _derive_session_keys(self, rnda: bytes, rndb: bytes, ti: bytes) -> AuthSessionKeys:
        """Derive session encryption and MAC keys from RndA, RndB, and Ti.

        Delegates to crypto_primitives.derive_session_keys() which implements
        the correct 32-byte SV formula per NXP datasheet Section 9.1.7.

        Args:
            rnda: Random A (16 bytes)
            rndb: Random B (16 bytes)
            ti: Transaction Identifier from card response (4 bytes)

        Returns:
            AuthSessionKeys dataclass with derived keys
        """
        # Use verified crypto_primitives implementation
        session_enc_key, session_mac_key = derive_session_keys(self.key, rnda, rndb)

        log.debug("[crypto_primitives] derive_session_keys:")
        log.debug(f"  Auth key: {self.key.hex()}")
        log.debug(f"  RndA: {rnda.hex()}")
        log.debug(f"  RndB: {rndb.hex()}")
        log.debug(f"  -> Session ENC: {session_enc_key.hex()}")
        log.debug(f"  -> Session MAC: {session_mac_key.hex()}")
        log.debug(f"  Using Ti from card: {ti.hex()}")

        return AuthSessionKeys(
            session_enc_key=session_enc_key,
            session_mac_key=session_mac_key,
            ti=ti,  # Use actual Ti from card response
            cmd_counter=0,
        )

    def apply_cmac(self, cmd_header: bytes, cmd_data: bytes) -> bytes:
        """Apply CMAC to command data for authenticated commands.

        Per AN12196 and NXP datasheet:
        CMAC is calculated over: Cmd || CmdCounter || TI || CmdHeader || CmdData

        CRITICAL: Uses CURRENT counter value, increments AFTER command succeeds.

        Args:
            cmd_header: 4-byte APDU command header [CLA INS P1 P2]
                       (INS byte will be extracted as native Cmd)
            cmd_data: Command data payload (without CMAC)

        Returns:
            cmd_data + CMAC (8 bytes appended)

        Raises:
            RuntimeError: If not authenticated
        """
        if not self.authenticated or self.session_keys is None:
            raise RuntimeError("Must authenticate before applying CMAC")

        # Use CURRENT counter value (increment happens AFTER command succeeds)
        assert self.session_keys is not None
        current_counter = self.session_keys.cmd_counter

        # Build data to MAC: Cmd || CmdCtr || TI || CmdHeader || CmdData
        # Per AN12196: "Cmd" is the native command byte (INS), not full APDU header!
        native_cmd = cmd_header[1]  # Extract INS byte from [CLA, INS, P1, P2]
        cmd_ctr_bytes = current_counter.to_bytes(2, "little")
        assert self.session_keys is not None
        ti = self.session_keys.ti

        # CmdHeader in CMAC is the command-specific header (e.g., FileNo, KeyNo)
        # which is already in cmd_data, so we don't include full APDU header
        data_to_mac = bytes([native_cmd]) + cmd_ctr_bytes + ti + cmd_data

        log.debug(f"CMAC input (counter={current_counter}): {data_to_mac.hex()}")

        # Calculate CMAC using session MAC key
        assert self.session_keys is not None
        cmac = CMAC.new(self.session_keys.session_mac_key, ciphermod=AES)
        cmac.update(data_to_mac)
        mac_full = cmac.digest()  # 16 bytes

        # Truncate to 8 bytes using EVEN-NUMBERED bytes (indices 1,3,5,7,9,11,13,15)
        # Per NXP NT4H2421Gx datasheet line 852:
        # "The MAC used in NT4H2421Gx is truncated by using only the 8 even-numbered bytes"
        # This applies to ALL CMAC calculations in NTAG424 DNA
        mac_truncated = bytes([mac_full[i] for i in range(1, 16, 2)])

        log.debug(f"CMAC (truncated): {mac_truncated.hex()}")

        return cmd_data + mac_truncated

    def encrypt_data(self, plaintext: bytes) -> bytes:
        """Encrypt data using session encryption key.

        Uses AES-128 CBC mode with IV derived from command counter.
        Applies ISO 7816-4 padding per NXP spec Section 9.1.4.

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted data

        Raises:
            RuntimeError: If not authenticated

        Reference:
            NT4H2421Gx Section 9.1.4 (Encryption)
        """
        if not self.authenticated or self.session_keys is None:
            raise RuntimeError("Must authenticate before encrypting")

        # Derive IV from command counter and TI
        iv = self._derive_iv()

        # ISO 7816-4 padding (0x80 + zeros)
        padded = self._iso7816_4_pad(plaintext)

        # Encrypt
        assert self.session_keys is not None
        cipher = AES.new(self.session_keys.session_enc_key, AES.MODE_CBC, iv=iv)
        cipher_text = cipher.encrypt(padded)

        log.debug(
            f"Encrypted {len(plaintext)} bytes (padded to {len(padded)}) -> {len(cipher_text)} bytes"
        )

        return cipher_text

    def decrypt_data(self, cipher_text: bytes) -> bytes:
        """Decrypt data using session encryption key.

        Removes ISO 7816-4 padding per NXP spec Section 9.1.4.

        Args:
            cipher_text: Encrypted data

        Returns:
            Decrypted and unpadded plaintext

        Raises:
            RuntimeError: If not authenticated

        Reference:
            NT4H2421Gx Section 9.1.4 (Encryption)
        """
        if not self.authenticated or self.session_keys is None:
            raise RuntimeError("Must authenticate before decrypting")

        # Derive IV
        iv = self._derive_iv()

        # Decrypt
        assert self.session_keys is not None
        cipher = AES.new(self.session_keys.session_enc_key, AES.MODE_CBC, iv=iv)
        padded = cipher.decrypt(cipher_text)

        # Remove ISO 7816-4 padding
        plaintext = self._iso7816_4_unpad(padded)

        log.debug(f"Decrypted {len(cipher_text)} bytes -> {len(plaintext)} bytes")

        return plaintext

    def _derive_iv(self) -> bytes:
        """Derive IV for encryption/decryption using verified crypto_primitives.

        Per NXP spec: IV = Enc(K, A55A || Ti || CmdCtr || 0x00...)

        Returns:
            16-byte IV
        """
        assert self.session_keys is not None
        iv = calculate_iv_for_command(
            self.session_keys.ti, self.session_keys.cmd_counter, self.session_keys.session_enc_key
        )
        log.debug(
            f"[crypto_primitives] calculate_iv (ctr={self.session_keys.cmd_counter}): {iv.hex()}"
        )
        return iv

    @staticmethod
    def _iso7816_4_pad(data: bytes) -> bytes:
        """Apply ISO/IEC 9797-1 Padding Method 2 (ISO 7816-4).

        Per NXP spec Section 9.1.4 line 181:
        "by adding always 80h followed, if required, by zero bytes"

        CRITICAL: "if the plain data is a multiple of 16 bytes already,
        an additional padding block is added."

        Args:
            data: Data to pad

        Returns:
            Padded data (multiple of 16 bytes)

        Reference:
            NT4H2421Gx Section 9.1.4 line 181
        """
        # Calculate padding needed
        length = len(data)
        padding_len = 16 - (length % 16)

        # Build padding: 0x80 followed by zeros
        padding = b"\x80" + b"\x00" * (padding_len - 1)

        return data + padding

    @staticmethod
    def _iso7816_4_unpad(padded_data: bytes) -> bytes:
        """Remove ISO/IEC 9797-1 Padding Method 2 (ISO 7816-4).

        Args:
            padded_data: Padded data

        Returns:
            Original data without padding

        Raises:
            ValueError: If padding is invalid
        """
        # Find 0x80 marker from end
        for i in range(len(padded_data) - 1, -1, -1):
            if padded_data[i] == 0x80:
                # Verify all bytes after 0x80 are 0x00
                if all(b == 0x00 for b in padded_data[i + 1 :]):
                    return padded_data[:i]
                else:
                    raise ValueError("Invalid ISO 7816-4 padding: non-zero bytes after 0x80")

        raise ValueError("Invalid ISO 7816-4 padding: no 0x80 marker found")

    @staticmethod
    def _pkcs7_pad(data: bytes) -> bytes:
        """Apply PKCS7 padding to data.

        DEPRECATED: Use _iso7816_4_pad() for NTAG424 secure messaging.
        PKCS7 is NOT compatible with NXP spec.

        Args:
            data: Data to pad

        Returns:
            Padded data (multiple of 16 bytes)
        """
        padding_len = 16 - (len(data) % 16)
        padding = bytes([padding_len] * padding_len)
        return data + padding

    @staticmethod
    def _pkcs7_unpad(padded_data: bytes) -> bytes:
        """Remove PKCS7 padding from data.

        DEPRECATED: Use _iso7816_4_unpad() for NTAG424 secure messaging.

        Args:
            padded_data: Padded data

        Returns:
            Original data without padding

        Raises:
            ValueError: If padding is invalid
        """
        padding_len = padded_data[-1]

        # Validate padding
        if padding_len > 16 or padding_len == 0:
            raise ValueError("Invalid PKCS7 padding")

        if padded_data[-padding_len:] != bytes([padding_len] * padding_len):
            raise ValueError("Invalid PKCS7 padding bytes")

        return padded_data[:-padding_len]


class AuthenticateEV2:
    """EV2 Authentication orchestrator (NOT a command - it's a protocol handler).

    This performs the two-phase EV2 authentication protocol and returns
    an AuthenticatedConnection context manager.

    Usage:
        key = get_key()
        with CardManager() as connection:
            with AuthenticateEV2(key, key_no=0)(connection) as auth_conn:
                # Perform authenticated operations
                auth_conn.send(ChangeKey(...))

    Or:
        auth_conn = AuthenticateEV2(key, key_no=0)(connection)
        auth_conn.send(ChangeKey(...))
    """

    def __init__(self, key: bytes, key_no: int = 0):
        """Initialize AuthenticateEV2.

        Args:
        key: 16-byte AES key for authentication.
        key_no: Key number to authenticate with (0-4).
        """
        if len(key) != 16:
            raise ValueError(f"Key must be 16 bytes, got {len(key)}")
        if not (0 <= key_no <= 4):
            raise ValueError(f"Key number must be 0-4, got {key_no}")

        self.key = key
        self.key_no = key_no

    def __str__(self) -> str:
        return f"AuthenticateEV2(key_no=0x{self.key_no:02X})"

    def __call__(self, connection: "NTag424CardConnection") -> "AuthenticatedConnection":
        """Perform complete EV2 authentication and return authenticated connection.

        Args:
            connection: Card connection to authenticate

        Returns:
            AuthenticatedConnection context manager with session keys

        Raises:
            ApduError: If authentication fails
        """
        log.info(f"Performing EV2 authentication with key {self.key_no}")

        # Create session and authenticate
        session = Ntag424AuthSession(self.key)
        session.authenticate(connection, key_no=self.key_no)

        log.info("Authentication successful, session established")

        # Return authenticated connection wrapper
        return AuthenticatedConnection(connection, session)
