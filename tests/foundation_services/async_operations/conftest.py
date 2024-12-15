"""
Pytest fixtures for async operations tests.
"""
import pytest
import asyncio
from typing import Dict, Any
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def chain_manager():
    """Create chain manager instance."""
    manager = ChainManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.fixture
async def contract_manager():
    """Create contract manager instance."""
    manager = ContractManager()
    await manager.start()
    yield manager
    await manager.stop()
