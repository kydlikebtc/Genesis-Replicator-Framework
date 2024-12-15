"""
Tests for cryptographic utilities.
"""
import pytest
import os
from genesis_replicator.security.crypto_utils import CryptoManager

async def test_password_hashing(crypto_manager):
    """Test password hashing."""
    password = "test_password"
    hashed = await crypto_manager.hash_password(password)
    assert await crypto_manager.verify_password(password, hashed)


async def test_data_encryption(crypto_manager):
    """Test data encryption/decryption."""
    data = b"test data"
    encrypted = await crypto_manager.encrypt_data(data)
    decrypted = await crypto_manager.decrypt_data(encrypted)
    assert decrypted == data

async def test_key_derivation(crypto_manager):
    """Test key derivation."""
    password = "test_password"
    salt = os.urandom(16)
    key = await crypto_manager.derive_key(password, salt)
    assert len(key) == 44  # Base64 encoded 32-byte key

async def test_encryption_with_derived_key(crypto_manager):
    """Test encryption with derived key."""
    password = "test_password"
    salt = os.urandom(16)
    key = await crypto_manager.derive_key(password, salt)

    custom_crypto = CryptoManager(secret_key=key)
    data = b"test data"
    encrypted = await custom_crypto.encrypt_data(data)
    decrypted = await custom_crypto.decrypt_data(encrypted)
    assert decrypted == data
