"""
Tests for blockchain synchronization manager.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3

from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager
from genesis_replicator.foundation_services.blockchain_integration.exceptions import ChainConnectionError

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def web3_mock():
    """Create a mock Web3 instance."""
    mock = AsyncMock()
    mock.__class__ = AsyncWeb3
    mock.eth = AsyncMock()
    mock.eth.block_number = AsyncMock(return_value=1000)
    mock.eth.get_block = AsyncMock(return_value={
        'number': 900,
        'hash': '0x123',
        'transactions': []
    })
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.is_connected = AsyncMock(return_value=True)

    # Mock provider
    mock_provider = AsyncMock()
    mock_provider.is_connected = AsyncMock(return_value=True)
    mock.provider = mock_provider

    return mock

@pytest.fixture
async def sync_manager(web3_mock):
    """Create a sync manager instance."""
    manager = SyncManager()
    await manager.start()

    # Configure with test chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1
        }
    }
    await manager.configure(config)

    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_start_sync(sync_manager):
    """Test starting blockchain synchronization."""
    chain_id = "test_chain"

    # Start sync
    await sync_manager.start_sync(chain_id)

    # Verify sync state
    status = await sync_manager.get_sync_status(chain_id)
    assert status['is_syncing'] is True
    assert status['current_block'] is not None
    assert status['chain_id'] == chain_id

@pytest.mark.asyncio
async def test_start_sync_already_running(sync_manager):
    """Test starting sync when already running."""
    chain_id = "test_chain"

    # Start first sync
    await sync_manager.start_sync(chain_id)

    # Try starting second sync
    with pytest.raises(ChainConnectionError) as exc_info:
        await sync_manager.start_sync(chain_id)

    assert "already running" in str(exc_info.value)

@pytest.mark.asyncio
async def test_stop_sync(sync_manager):
    """Test stopping blockchain synchronization."""
    chain_id = "test_chain"

    # Start sync
    await sync_manager.start_sync(chain_id)

    # Stop sync
    await sync_manager.stop_sync(chain_id)

    # Verify cleanup
    status = await sync_manager.get_sync_status(chain_id)
    assert status['is_syncing'] is False

@pytest.mark.asyncio
async def test_stop_sync_not_running(sync_manager):
    """Test stopping sync when not running."""
    chain_id = "nonexistent_chain"

    with pytest.raises(ChainConnectionError) as exc_info:
        await sync_manager.stop_sync(chain_id)

    assert "No sync running" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_sync_status(sync_manager):
    """Test getting sync status."""
    chain_id = "test_chain"

    # Start sync
    await sync_manager.start_sync(chain_id)

    # Get status
    status = await sync_manager.get_sync_status(chain_id)

    assert status['chain_id'] == chain_id
    assert status['is_syncing'] is True
    assert status['current_block'] is not None
    assert status['latest_block'] is not None
    assert status['blocks_remaining'] is not None

@pytest.mark.asyncio
async def test_get_sync_status_not_found(sync_manager):
    """Test getting sync status for non-existent chain."""
    chain_id = "nonexistent_chain"

    with pytest.raises(ChainConnectionError) as exc_info:
        await sync_manager.get_sync_status(chain_id)

    assert "No sync found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_sync_blockchain(sync_manager):
    """Test blockchain synchronization process."""
    chain_id = "test_chain"

    # Start sync
    await sync_manager.start_sync(chain_id)

    # Let sync run for a bit
    await asyncio.sleep(0.1)

    # Get status and verify block processing
    status = await sync_manager.get_sync_status(chain_id)
    assert status['current_block'] is not None
    assert status['blocks_remaining'] is not None

@pytest.mark.asyncio
async def test_reorg_detection(sync_manager, web3_mock):
    """Test blockchain reorganization detection."""
    chain_id = "test_chain"

    # Mock blocks for reorg scenario
    block1 = {'number': 1000, 'hash': '0x123', 'transactions': []}
    block2 = {'number': 1000, 'hash': '0x456', 'transactions': []}  # Different hash
    web3_mock.eth.get_block.side_effect = [block1, block2]

    # Start sync
    await sync_manager.start_sync(chain_id)

    # Let reorg monitor run
    await asyncio.sleep(0.1)

    # Get status and verify reorg detection
    status = await sync_manager.get_sync_status(chain_id)
    assert status['reorg_detected'] is True

@pytest.mark.asyncio
async def test_web3_error_handling(sync_manager, web3_mock):
    """Test Web3 error handling during sync."""
    chain_id = "test_chain"

    # Mock Web3 error
    web3_mock.eth.get_block.side_effect = ChainConnectionError("Connection error")

    # Start sync and verify error handling
    await sync_manager.start_sync(chain_id)
    status = await sync_manager.get_sync_status(chain_id)
    assert status['error'] is not None
    assert "Connection error" in status['error']
