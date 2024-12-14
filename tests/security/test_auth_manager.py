"""
Tests for authentication manager.
"""
import pytest
import jwt
from datetime import datetime

async def test_user_registration(auth_manager, test_user_credentials):
    """Test user registration."""
    success = await auth_manager.register_user(
        test_user_credentials["username"],
        test_user_credentials["password"],
        test_user_credentials["roles"]
    )
    assert success is True

async def test_duplicate_registration(auth_manager, test_user_credentials):
    """Test duplicate user registration."""
    await auth_manager.register_user(
        test_user_credentials["username"],
        test_user_credentials["password"],
        test_user_credentials["roles"]
    )
    success = await auth_manager.register_user(
        test_user_credentials["username"],
        test_user_credentials["password"],
        test_user_credentials["roles"]
    )
    assert success is False

async def test_authentication(auth_manager, test_user_credentials):
    """Test user authentication."""
    await auth_manager.register_user(
        test_user_credentials["username"],
        test_user_credentials["password"],
        test_user_credentials["roles"]
    )
    token = await auth_manager.authenticate(
        test_user_credentials["username"],
        test_user_credentials["password"]
    )
    assert token is not None

async def test_invalid_authentication(auth_manager, test_user_credentials):
    """Test invalid authentication."""
    await auth_manager.register_user(
        test_user_credentials["username"],
        test_user_credentials["password"],
        test_user_credentials["roles"]
    )
    token = await auth_manager.authenticate(
        test_user_credentials["username"],
        "wrong_password"
    )
    assert token is None

async def test_token_verification(auth_manager, test_user_credentials):
    """Test token verification."""
    await auth_manager.register_user(
        test_user_credentials["username"],
        test_user_credentials["password"],
        test_user_credentials["roles"]
    )
    token = await auth_manager.authenticate(
        test_user_credentials["username"],
        test_user_credentials["password"]
    )
    payload = await auth_manager.verify_token(token)
    assert payload is not None
    assert payload["sub"] == test_user_credentials["username"]
    assert set(payload["roles"]) == set(test_user_credentials["roles"])
