"""
Tests for async operations and concurrency controls.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.providers import AsyncBaseProvider
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.exceptions import SecurityError, ChainConnectionError

# Mock Web3 provider for testing
class MockAsyncProvider(AsyncBaseProvider):
    """Mock Web3 provider that simulates blockchain responses."""
    async def make_request(self, method, params):
        await asyncio.sleep(0.1)  # Simulate network delay
        if method == "eth_chainId":
            return {"result": "0x1"}
        elif method == "eth_blockNumber":
            return {"result": "0x1"}
        elif method == "eth_gasPrice":
            return {"result": "0x1"}
        elif method == "eth_syncing":
            return {"result": False}
        return {"result": None}

@pytest.fixture
async def mock_web3():
    """Create a mock Web3 instance."""
    provider = MockAsyncProvider()
    web3 = AsyncWeb3(provider)
    return web3

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

@pytest.mark.asyncio
async def test_concurrent_chain_connections(chain_manager, mock_web3):
    """Test concurrent chain connections."""
    with patch('web3.AsyncWeb3', return_value=mock_web3):
        # Create multiple connections concurrently
        tasks = []
        for i in range(5):
            tasks.append(
                chain_manager.connect_to_chain(
                    f"chain_{i}",
                    f"http://localhost:854{i}",
                    credentials={'role': 'admin'}
                )
            )

        # Should handle concurrent connections without errors
        await asyncio.gather(*tasks)

        # Verify connections
        chains = await chain_manager.get_connected_chains()
        assert len(chains) == 5

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_connection_pool_limits(chain_manager, mock_web3):
    """Test connection pool limits and backpressure."""
    with patch('web3.AsyncWeb3', return_value=mock_web3):
        # Create more connections than the default pool size
        tasks = []
        for i in range(20):  # More than semaphore limit
            tasks.append(
                chain_manager.connect_to_chain(
                    f"chain_{i}",
                    f"http://localhost:854{i}",
                    credentials={'role': 'admin'}
                )
            )

        # Should handle backpressure without errors
        await asyncio.gather(*tasks)

        # Verify connections
        chains = await chain_manager.get_connected_chains()
        assert len(chains) == 20

@pytest.mark.asyncio
async def test_concurrent_contract_operations(contract_manager, chain_manager, mock_web3):
    """Test concurrent contract operations."""
    await chain_manager.connect_to_chain(
        "test_chain",
        "http://localhost:8545",
        credentials={'role': 'admin'}
    )

    with patch('web3.AsyncWeb3', return_value=mock_web3):
        # Deploy multiple contracts concurrently
        tasks = []
        for i in range(5):
            tasks.append(
                contract_manager.deploy_contract(
                    f"contract_{i}",
                    "TestContract",
                    credentials={'role': 'admin'}
                )
            )

        # Should handle concurrent deployments
        await asyncio.gather(*tasks)

        # Verify deployments
        contracts = await contract_manager.get_deployed_contracts()
        assert len(contracts) == 5

@pytest.mark.asyncio
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
