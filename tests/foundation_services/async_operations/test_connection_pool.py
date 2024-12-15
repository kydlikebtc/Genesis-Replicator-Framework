"""
Tests for connection pooling implementation.
"""
import asyncio
import pytest
from typing import Dict, Any
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.exceptions import ChainConnectionError

@pytest.fixture
async def chain_manager():
    """Create chain manager instance for testing."""
    manager = ChainManager(max_connections=5)  # Set small pool size for testing
    await manager.start()
    yield manager
    await manager.stop()

async def test_connection_pool_initialization(chain_manager):
    """Test connection pool initialization."""
    # Verify initial pool state
    assert chain_manager._max_connections == 5
    assert len(chain_manager._connection_pool) == 0
    assert chain_manager._pool_semaphore._value == 5

async def test_connection_pool_reuse(chain_manager):
    """Test connection reuse from pool."""
    # Create initial connection
    await chain_manager.connect_to_chain(
        "test_chain",
        "http://localhost:8545",
        credentials={'role': 'admin'}
    )

    # Get connection from pool multiple times
    conn1 = await chain_manager.get_connection("test_chain")
    conn2 = await chain_manager.get_connection("test_chain")

    # Verify same connection is reused
    assert conn1 is conn2
    assert len(chain_manager._connection_pool) == 1

async def test_connection_pool_cleanup(chain_manager):
    """Test connection pool cleanup."""
    # Create multiple connections
    for i in range(3):
        await chain_manager.connect_to_chain(
            f"chain_{i}",
            f"http://localhost:854{i}",
            credentials={'role': 'admin'}
        )

    # Verify connections in pool
    assert len(chain_manager._connection_pool) == 3

    # Cleanup specific connection
    await chain_manager.disconnect_chain("chain_0")
    assert len(chain_manager._connection_pool) == 2

    # Cleanup all connections
    await chain_manager.cleanup()
    assert len(chain_manager._connection_pool) == 0

async def test_connection_pool_limits(chain_manager):
    """Test connection pool limits."""
    # Try to create more connections than pool limit
    tasks = []
    for i in range(7):  # More than pool size (5)
        tasks.append(
            chain_manager.connect_to_chain(
                f"chain_{i}",
                f"http://localhost:854{i}",
                credentials={'role': 'admin'}
            )
        )

    # Should handle limit gracefully
    results = await asyncio.gather(*tasks, return_exceptions=True)
    active_connections = len([r for r in results if not isinstance(r, Exception)])

    # Verify pool limit is enforced
    assert active_connections <= 5
    assert len(chain_manager._connection_pool) <= 5

async def test_connection_pool_timeout(chain_manager):
    """Test connection pool timeout handling."""
    # Fill up the connection pool
    for i in range(5):
        await chain_manager.connect_to_chain(
            f"chain_{i}",
            f"http://localhost:854{i}",
            credentials={'role': 'admin'}
        )

    # Try to get connection with timeout
    with pytest.raises(ChainConnectionError):
        await asyncio.wait_for(
            chain_manager.connect_to_chain(
                "timeout_chain",
                "http://localhost:8545",
                credentials={'role': 'admin'}
            ),
            timeout=1.0
        )

async def test_connection_pool_parallel_access(chain_manager):
    """Test parallel access to connection pool."""
    # Create initial connection
    await chain_manager.connect_to_chain(
        "test_chain",
        "http://localhost:8545",
        credentials={'role': 'admin'}
    )

    async def access_connection():
        conn = await chain_manager.get_connection("test_chain")
        await asyncio.sleep(0.1)  # Simulate work
        return conn

    # Test parallel access
    tasks = [access_connection() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Verify all tasks got the same connection
    assert all(r is results[0] for r in results)
    assert len(chain_manager._connection_pool) == 1

async def test_connection_pool_error_recovery(chain_manager):
    """Test connection pool error recovery."""
    # Create connection that will fail
    await chain_manager.connect_to_chain(
        "failing_chain",
        "http://localhost:8545",
        credentials={'role': 'admin'}
    )

    # Simulate connection failure
    chain_manager._connection_pool["failing_chain"].is_connected = False

    # Try to get connection - should create new one
    conn = await chain_manager.get_connection("failing_chain")
    assert conn.is_connected
    assert len(chain_manager._connection_pool) == 1
