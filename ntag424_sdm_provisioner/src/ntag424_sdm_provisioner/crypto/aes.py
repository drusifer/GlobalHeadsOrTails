from Crypto.Cipher import AES  # nosec
from Crypto.Hash import CMAC  # nosec


class AesKey:
    """Wrapper for AES-128 key operations."""

    def __init__(self, key_bytes: bytes):
        if len(key_bytes) != 16:
            raise ValueError("Key must be 16 bytes")
        self._key = key_bytes

    def encrypt(self, data: bytes, iv: bytes | None = None) -> bytes:
        """Encrypt data using AES-CBC."""
        if iv is None:
            iv = b"\x00" * 16
        cipher = AES.new(self._key, AES.MODE_CBC, iv=iv)
        return cipher.encrypt(data)

    def decrypt(self, data: bytes, iv: bytes | None = None) -> bytes:
        """Decrypt data using AES-CBC."""
        if iv is None:
            iv = b"\x00" * 16
        cipher = AES.new(self._key, AES.MODE_CBC, iv=iv)
        return cipher.decrypt(data)

    def cmac(self, data: bytes) -> bytes:
        """Calculate CMAC."""
        c = CMAC.new(self._key, ciphermod=AES)
        c.update(data)
        return c.digest()

    def __bytes__(self) -> bytes:
        return self._key
