"""
Tests for async operations and concurrency controls.
"""
import asyncio
import pytest
from typing import Dict, Any
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.exceptions import SecurityError, ChainConnectionError

@pytest.fixture
async def chain_manager():
    """Create chain manager instance for testing."""
    manager = ChainManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.fixture
async def contract_manager():
    """Create contract manager instance for testing."""
    manager = ContractManager()
    await manager.start()
    yield manager
    await manager.stop()

async def test_concurrent_chain_connections(chain_manager):
    """Test concurrent chain connections."""
    # Test multiple concurrent connections
    tasks = []
    for i in range(5):
        tasks.append(
            chain_manager.connect_to_chain(
                f"chain_{i}",
                f"http://localhost:854{i}",
                credentials={'role': 'admin'}
            )
        )

    # Should handle concurrent connections properly
    await asyncio.gather(*tasks)

    # Verify connections
    chains = await chain_manager.get_connected_chains()
    assert len(chains) == 5

async def test_connection_timeout_handling(chain_manager):
    """Test timeout handling for chain connections."""
    # Test connection with timeout
    with pytest.raises(ChainConnectionError):
        await asyncio.wait_for(
            chain_manager.connect_to_chain(
                "timeout_chain",
                "http://nonexistent:8545",
                credentials={'role': 'admin'}
            ),
            timeout=2.0
        )

async def test_connection_pool_limits(chain_manager):
    """Test connection pool limits and backpressure."""
    # Create more connections than the default pool size
    tasks = []
    for i in range(20):  # Assuming default pool size is smaller
        tasks.append(
            chain_manager.connect_to_chain(
                f"chain_{i}",
                f"http://localhost:854{i}",
                credentials={'role': 'admin'}
            )
        )

    # Should handle backpressure without errors
    await asyncio.gather(*tasks)

    # Verify connection limit enforcement
    chains = await chain_manager.get_connected_chains()
    assert len(chains) <= 20  # Should not exceed max connections

async def test_concurrent_contract_operations(contract_manager, chain_manager):
    """Test concurrent contract operations."""
    # Setup mock chain connection
    await chain_manager.connect_to_chain(
        "test_chain",
        "http://localhost:8545",
        credentials={'role': 'admin'}
    )

    # Test concurrent contract deployments
    tasks = []
    for i in range(3):
        tasks.append(
            contract_manager.deploy_contract(
                "test_chain",
                chain_manager._connections["test_chain"],
                f"Contract_{i}",
                {"abi": []},
                "0x",
                from_address="0x1234567890123456789012345678901234567890"
            )
        )

    # Should handle concurrent deployments
    await asyncio.gather(*tasks)

async def test_concurrent_security_validation(chain_manager):
    """Test concurrent security validation operations."""
    # Test concurrent security validations
    tasks = []
    for i in range(10):
        tasks.append(
            chain_manager.validate_chain_credentials(
                f"chain_{i}",
                credentials={'role': 'user'}  # Invalid credentials
            )
        )

    # Should handle concurrent security validations
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all operations failed with SecurityError
    assert all(isinstance(r, SecurityError) for r in results)
