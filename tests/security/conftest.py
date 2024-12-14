"""
Test fixtures for security tests.
"""
import pytest
import jwt
from datetime import datetime
from genesis_replicator.security.auth_manager import AuthManager
from genesis_replicator.security.crypto_utils import CryptoManager
from genesis_replicator.security.contract_security import ContractSecurityManager
from web3 import Web3

@pytest.fixture
async def auth_manager():
    """Provide configured auth manager."""
    return AuthManager(secret_key="test_secret")

@pytest.fixture
async def crypto_manager():
    """Provide configured crypto manager."""
    return CryptoManager()

@pytest.fixture
async def contract_security():
    """Provide configured contract security manager."""
    w3 = Web3()
    return ContractSecurityManager(w3)

@pytest.fixture
async def test_user_credentials():
    """Provide test user credentials."""
    return {
        "username": "test_user",
        "password": "test_password",
        "roles": ["user", "admin"]
    }

@pytest.fixture
async def test_contract():
    """Provide test contract data."""
    return {
        "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "source_code": """
        pragma solidity ^0.8.0;
        contract Test {
            address owner;
            constructor() {
                owner = msg.sender;
            }
            modifier onlyOwner() {
                require(msg.sender == owner);
                _;
            }
        }
        """,
        "bytecode": "0x608060405234801561001057600080fd5b50"
    }
