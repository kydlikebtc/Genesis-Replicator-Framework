"""
Tests for the blockchain sync manager.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from genesis_replicator.foundation_services.exceptions import BlockchainError
from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager


@pytest.fixture
async def sync_manager():
    """Create a sync manager instance."""
    return SyncManager()


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    web3 = AsyncMock(spec=AsyncWeb3)
    web3.eth = AsyncMock()
    web3.eth.block_number = AsyncMock(return_value=1000)
    web3.eth.get_block = AsyncMock()
    return web3


@pytest.mark.asyncio
async def test_start_sync(sync_manager, mock_web3):
    """Test starting blockchain synchronization."""
    chain_id = "test_chain"
    start_block = 900

    # Start sync
    await sync_manager.start_sync(chain_id, mock_web3, start_block)

    # Verify sync state
    assert chain_id in sync_manager._sync_tasks
    assert chain_id in sync_manager._sync_states
    assert chain_id in sync_manager._reorg_monitors
    assert chain_id in sync_manager._processed_blocks

    state = sync_manager._sync_states[chain_id]
    assert state['current_block'] == start_block
    assert state['latest_block'] == 1000
    assert state['running'] is True


@pytest.mark.asyncio
async def test_start_sync_already_running(sync_manager, mock_web3):
    """Test starting sync when already running."""
    chain_id = "test_chain"

    # Start first sync
    await sync_manager.start_sync(chain_id, mock_web3)

    # Try starting second sync
    with pytest.raises(BlockchainError) as exc_info:
        await sync_manager.start_sync(chain_id, mock_web3)

    assert "already running" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stop_sync(sync_manager, mock_web3):
    """Test stopping blockchain synchronization."""
    chain_id = "test_chain"

    # Start sync
    await sync_manager.start_sync(chain_id, mock_web3)

    # Stop sync
    await sync_manager.stop_sync(chain_id)

    # Verify cleanup
    assert chain_id not in sync_manager._sync_tasks
    assert chain_id not in sync_manager._sync_states
    assert chain_id not in sync_manager._reorg_monitors
    assert chain_id not in sync_manager._processed_blocks


@pytest.mark.asyncio
async def test_stop_sync_not_running(sync_manager):
    """Test stopping sync when not running."""
    chain_id = "test_chain"

    with pytest.raises(BlockchainError) as exc_info:
        await sync_manager.stop_sync(chain_id)

    assert "No sync running" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_sync_status(sync_manager, mock_web3):
    """Test getting sync status."""
    chain_id = "test_chain"
    start_block = 900

    # Start sync
    await sync_manager.start_sync(chain_id, mock_web3, start_block)

    # Get status
    status = await sync_manager.get_sync_status(chain_id)

    assert status['chain_id'] == chain_id
    assert status['current_block'] == start_block
    assert status['latest_block'] == 1000
    assert status['blocks_remaining'] == 100
    assert status['is_running'] is True
    assert status['processed_blocks'] == 0


@pytest.mark.asyncio
async def test_get_sync_status_not_found(sync_manager):
    """Test getting sync status for non-existent chain."""
    chain_id = "test_chain"

    with pytest.raises(BlockchainError) as exc_info:
        await sync_manager.get_sync_status(chain_id)

    assert "No sync found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_blockchain(sync_manager, mock_web3):
    """Test blockchain synchronization process."""
    chain_id = "test_chain"
    start_block = 900

    # Mock block data
    mock_block = {
        'number': start_block,
        'hash': '0x123',
        'transactions': []
    }
    mock_web3.eth.get_block.return_value = mock_block

    # Start sync
    await sync_manager.start_sync(chain_id, mock_web3, start_block)

    # Let sync run for a bit
    await asyncio.sleep(0.1)

    # Stop sync
    await sync_manager.stop_sync(chain_id)

    # Verify block processing
    mock_web3.eth.get_block.assert_called_with(start_block, full_transactions=True)


@pytest.mark.asyncio
async def test_reorg_detection(sync_manager, mock_web3):
    """Test blockchain reorganization detection."""
    chain_id = "test_chain"
    block_number = 1000

    # Mock blocks for reorg scenario
    block1 = {'number': block_number, 'hash': '0x123'}
    block2 = {'number': block_number, 'hash': '0x456'}  # Different hash, same height

    mock_web3.eth.get_block.side_effect = [block1, block2]

    # Start sync
    await sync_manager.start_sync(chain_id, mock_web3)

    # Let reorg monitor run
    await asyncio.sleep(0.1)

    # Stop sync
    await sync_manager.stop_sync(chain_id)

    # Verify reorg detection
    assert mock_web3.eth.get_block.call_count >= 2


@pytest.mark.asyncio
async def test_web3_error_handling(sync_manager, mock_web3):
    """Test Web3 error handling during sync."""
    chain_id = "test_chain"

    # Mock Web3 error
    mock_web3.eth.block_number.side_effect = Web3Exception("Connection error")

    # Try starting sync
    with pytest.raises(BlockchainError) as exc_info:
        await sync_manager.start_sync(chain_id, mock_web3)

    assert "Web3 error" in str(exc_info.value)
    assert "Connection error" in str(exc_info.value)
