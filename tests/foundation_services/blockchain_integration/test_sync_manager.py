"""
Tests for blockchain synchronization manager.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager
from genesis_replicator.foundation_services.exceptions import (
    BlockchainError,
    ChainConnectionError,
    SyncError
)

@pytest.fixture
async def sync_manager(base_web3_mock):
    """Create a sync manager instance."""
    manager = SyncManager()
    await manager.initialize()

    # Configure with test chain
    config = {
        "chains": {
            "test_chain": {
                "rpc_url": "http://localhost:8545",
                "chain_id": 1,
                "start_block": 1000,
                "batch_size": 100
            }
        }
    }

    with patch.object(AsyncWeb3, '__new__', return_value=base_web3_mock):
        await manager.configure(config)

    try:
        yield manager
    finally:
        await manager.cleanup()

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
    with pytest.raises(SyncError) as exc_info:
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

    with pytest.raises(SyncError) as exc_info:
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

    # Verify status fields
    assert status['chain_id'] == chain_id
    assert status['is_syncing'] is True
    assert status['current_block'] is not None
    assert status['latest_block'] is not None
    assert status['blocks_remaining'] is not None

@pytest.mark.asyncio
async def test_get_sync_status_not_found(sync_manager):
    """Test getting sync status for non-existent chain."""
    chain_id = "nonexistent_chain"

    with pytest.raises(SyncError) as exc_info:
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
async def test_reorg_detection(sync_manager, base_web3_mock):
    """Test blockchain reorganization detection."""
    chain_id = "test_chain"

    # Mock blocks for reorg scenario
    blocks = [
        {'number': 1000, 'hash': '0x123', 'transactions': []},
        {'number': 1000, 'hash': '0x456', 'transactions': []}  # Different hash
    ]
    base_web3_mock.eth.get_block = AsyncMock(side_effect=blocks)

    # Start sync
    await sync_manager.start_sync(chain_id)

    # Let reorg monitor run
    await asyncio.sleep(0.1)

    # Get status and verify reorg detection
    status = await sync_manager.get_sync_status(chain_id)
    assert status['reorg_detected'] is True

@pytest.mark.asyncio
async def test_web3_error_handling(sync_manager, base_web3_mock):
    """Test Web3 error handling during sync."""
    chain_id = "test_chain"

    # Mock Web3 error
    base_web3_mock.eth.get_block = AsyncMock(side_effect=Web3Exception("Network error"))

    # Start sync and verify error handling
    with pytest.raises(BlockchainError) as exc_info:
        await sync_manager.start_sync(chain_id)
    assert "Network error" in str(exc_info.value)
