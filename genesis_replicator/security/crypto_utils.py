"""
Cryptographic utilities for Genesis Replicator Framework.
"""
import asyncio
import bcrypt
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

async def hash_password(password: str) -> str:
    """Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

async def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash.

    Args:
        password: Plain text password
        hashed: Hashed password

    Returns:
        bool: True if password matches
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())

class CryptoManager:
    """Manages cryptographic operations."""

    def __init__(self, secret_key: Optional[str] = None):
        """Initialize crypto manager.

        Args:
            secret_key: Optional base64 encoded key
        """
        if secret_key:
            self._key = base64.urlsafe_b64decode(secret_key)
        else:
            self._key = Fernet.generate_key()
        self._fernet = Fernet(self._key)
        self._lock = asyncio.Lock()

    async def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt binary data.

        Args:
            data: Data to encrypt

        Returns:
            bytes: Encrypted data
        """
        async with self._lock:
            return self._fernet.encrypt(data)

    async def decrypt_data(self, encrypted: bytes) -> bytes:
        """Decrypt binary data.

        Args:
            encrypted: Encrypted data

        Returns:
            bytes: Decrypted data
        """
        async with self._lock:
            return self._fernet.decrypt(encrypted)

    async def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password.

        Args:
            password: Password to derive key from
            salt: Salt for key derivation

        Returns:
            bytes: Derived key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(
            kdf.derive(password.encode())
        )
