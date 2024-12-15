"""
Tests for the blockchain transaction manager.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from genesis_replicator.foundation_services.exceptions import TransactionError
from genesis_replicator.foundation_services.blockchain_integration.transaction_manager import TransactionManager


@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture
async def transaction_manager(event_loop, mock_web3):
    """Create a transaction manager instance."""
    manager = TransactionManager()
    await manager.start()

    # Configure with test chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1
        }
    }

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        await manager.configure(config)
        yield manager
        await manager.stop()


@pytest.fixture
async def mock_web3():
    """Create a mock Web3 instance."""
    mock = MagicMock(spec=AsyncWeb3)
    mock.eth = MagicMock()
    mock.eth.get_transaction_count = AsyncMock(return_value=1)
    mock.eth.send_transaction = AsyncMock(return_value='0x123')
    mock.eth.wait_for_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_transaction = AsyncMock(return_value={
        'blockNumber': 100,
        'from': '0x123',
        'to': '0x456',
        'value': 1000,
        'gasPrice': 20000000000
    })
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.block_number = AsyncMock(return_value=105)
    mock.is_connected = AsyncMock(return_value=True)
    yield mock


@pytest.mark.asyncio
async def test_submit_transaction(transaction_manager):
    """Test submitting a transaction."""
    chain_id = "test_chain"
    tx = {
        'from': '0x123',
        'to': '0x456',
        'value': 1000
    }

    # Submit transaction
    tx_hash = await transaction_manager.submit_transaction(chain_id, tx)
    assert tx_hash is not None
    assert len(tx_hash) == 66  # Valid hex transaction hash


@pytest.mark.asyncio
async def test_submit_transaction_missing_from(transaction_manager):
    """Test submitting transaction without 'from' address."""
    chain_id = "test_chain"
    tx = {
        'to': '0x456',
        'value': 1000
    }

    with pytest.raises(TransactionError) as exc_info:
        await transaction_manager.submit_transaction(chain_id, tx)

    assert "missing 'from' address" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_transaction_failure(transaction_manager, mock_web3):
    """Test submitting a failing transaction."""
    chain_id = "test_chain"
    tx = {
        'from': '0x123',
        'to': '0x456',
        'value': 1000
    }

    # Mock transaction failure
    mock_web3.eth.wait_for_transaction_receipt.return_value = {'status': 0}

    with pytest.raises(TransactionError) as exc_info:
        await transaction_manager.submit_transaction(chain_id, tx)

    assert "Transaction failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_transaction_status(transaction_manager):
    """Test getting transaction status."""
    chain_id = "test_chain"
    tx_hash = '0x' + '1' * 64

    # Get status
    status = await transaction_manager.get_transaction_status(chain_id, tx_hash)

    assert status['hash'] == tx_hash
    assert status['chain_id'] == chain_id
    assert status['block_number'] is not None
    assert status['status'] is not None
    assert status['confirmations'] is not None


@pytest.mark.asyncio
async def test_create_transaction_batch(transaction_manager):
    """Test creating a transaction batch."""
    chain_id = "test_chain"
    transactions = [
        {'from': '0x123', 'to': '0x456', 'value': 1000},
        {'from': '0x789', 'to': '0xabc', 'value': 2000}
    ]

    # Create batch
    batch = await transaction_manager.create_transaction_batch(chain_id, transactions)
    assert len(batch.transactions) == 2
    assert batch.chain_id == chain_id


@pytest.mark.asyncio
async def test_submit_transaction_batch(transaction_manager):
    """Test submitting a transaction batch."""
    chain_id = "test_chain"
    transactions = [
        {'from': '0x123', 'to': '0x456', 'value': 1000},
        {'from': '0x789', 'to': '0xabc', 'value': 2000}
    ]

    # Create and submit batch
    batch = await transaction_manager.create_transaction_batch(chain_id, transactions)
    results = await transaction_manager.submit_transaction_batch(batch)

    assert len(results) == 2
    for tx_hash in results:
        assert len(tx_hash) == 66  # Valid hex transaction hash


@pytest.mark.asyncio
async def test_submit_transaction_batch_parallel(transaction_manager):
    """Test submitting a transaction batch in parallel."""
    chain_id = "test_chain"
    transactions = [
        {'from': '0x123', 'to': '0x456', 'value': 1000},
        {'from': '0x789', 'to': '0xabc', 'value': 2000}
    ]

    # Create and submit batch in parallel
    batch = await transaction_manager.create_transaction_batch(chain_id, transactions)
    results = await transaction_manager.submit_transaction_batch(batch, parallel=True)

    assert len(results) == 2
    for tx_hash in results:
        assert len(tx_hash) == 66  # Valid hex transaction hash
