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


@pytest.fixture
async def transaction_manager():
    """Create a transaction manager instance."""
    return TransactionManager()


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    web3 = AsyncMock(spec=AsyncWeb3)
    web3.eth = AsyncMock()
    web3.eth.get_transaction_count = AsyncMock(return_value=1)
    web3.eth.send_transaction = AsyncMock()
    web3.eth.wait_for_transaction_receipt = AsyncMock()
    web3.eth.get_transaction = AsyncMock()
    web3.eth.get_transaction_receipt = AsyncMock()
    return web3


@pytest.mark.asyncio
async def test_submit_transaction(transaction_manager, mock_web3):
    """Test submitting a transaction."""
    chain_id = "test_chain"
    tx = {'from': '0x123', 'to': '0x456', 'value': 1000}
    tx_hash = '0x789'
    receipt = {'status': 1, 'transactionHash': tx_hash}

    mock_web3.eth.send_transaction.return_value.hex.return_value = tx_hash
    mock_web3.eth.wait_for_transaction_receipt.return_value = receipt

    # Submit transaction
    result_hash, result_receipt = await transaction_manager.submit_transaction(
        chain_id, mock_web3, tx
    )

    assert result_hash == tx_hash
    assert result_receipt == receipt
    assert tx_hash in transaction_manager._pending_transactions


@pytest.mark.asyncio
async def test_submit_transaction_missing_from(transaction_manager, mock_web3):
    """Test submitting transaction without 'from' address."""
    chain_id = "test_chain"
    tx = {'to': '0x456', 'value': 1000}  # Missing 'from'

    with pytest.raises(TransactionError) as exc_info:
        await transaction_manager.submit_transaction(chain_id, mock_web3, tx)

    assert "missing 'from' address" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_transaction_failure(transaction_manager, mock_web3):
    """Test submitting a failing transaction."""
    chain_id = "test_chain"
    tx = {'from': '0x123', 'to': '0x456', 'value': 1000}
    tx_hash = '0x789'
    receipt = {'status': 0, 'transactionHash': tx_hash}  # Failed transaction

    mock_web3.eth.send_transaction.return_value.hex.return_value = tx_hash
    mock_web3.eth.wait_for_transaction_receipt.return_value = receipt

    with pytest.raises(TransactionError) as exc_info:
        await transaction_manager.submit_transaction(chain_id, mock_web3, tx)

    assert "Transaction failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_transaction_status(transaction_manager, mock_web3):
    """Test getting transaction status."""
    chain_id = "test_chain"
    tx_hash = '0x789'
    tx = {
        'blockNumber': 100,
        'from': '0x123',
        'to': '0x456',
        'value': 1000,
        'gasPrice': 20000000000
    }
    receipt = {'status': 1}

    mock_web3.eth.get_transaction.return_value = tx
    mock_web3.eth.get_transaction_receipt.return_value = receipt
    mock_web3.eth.block_number = 105


    # Get status
    status = await transaction_manager.get_transaction_status(
        chain_id, mock_web3, tx_hash
    )

    assert status['hash'] == tx_hash
    assert status['chain_id'] == chain_id
    assert status['block_number'] == 100
    assert status['from'] == '0x123'
    assert status['to'] == '0x456'
    assert status['value'] == 1000
    assert status['gas_price'] == 20000000000
    assert status['status'] == 1
    assert status['confirmations'] == 5


@pytest.mark.asyncio
async def test_create_transaction_batch(transaction_manager):
    """Test creating a transaction batch."""
    batch_id = "test_batch"
    chain_id = "test_chain"
    transactions = [
        {'from': '0x123', 'to': '0x456', 'value': 1000},
        {'from': '0x789', 'to': '0xabc', 'value': 2000}
    ]

    # Create batch
    await transaction_manager.create_transaction_batch(
        batch_id, chain_id, transactions
    )

    assert batch_id in transaction_manager._transaction_batches
    assert len(transaction_manager._transaction_batches[batch_id]) == 2


@pytest.mark.asyncio
async def test_submit_transaction_batch(transaction_manager, mock_web3):
    """Test submitting a transaction batch."""
    batch_id = "test_batch"
    chain_id = "test_chain"
    transactions = [
        {'from': '0x123', 'to': '0x456', 'value': 1000},
        {'from': '0x789', 'to': '0xabc', 'value': 2000}
    ]
    tx_hash = '0x789'
    receipt = {'status': 1, 'transactionHash': tx_hash}

    mock_web3.eth.send_transaction.return_value.hex.return_value = tx_hash
    mock_web3.eth.wait_for_transaction_receipt.return_value = receipt

    # Create and submit batch
    await transaction_manager.create_transaction_batch(
        batch_id, chain_id, transactions
    )
    results = await transaction_manager.submit_transaction_batch(
        chain_id, mock_web3, batch_id
    )

    assert len(results) == 2
    for result in results:
        assert result[0] == tx_hash
        assert result[1] == receipt


@pytest.mark.asyncio
async def test_submit_transaction_batch_parallel(transaction_manager, mock_web3):
    """Test submitting a transaction batch in parallel."""
    batch_id = "test_batch"
    chain_id = "test_chain"
    transactions = [
        {'from': '0x123', 'to': '0x456', 'value': 1000},
        {'from': '0x789', 'to': '0xabc', 'value': 2000}
    ]
    tx_hash = '0x789'
    receipt = {'status': 1, 'transactionHash': tx_hash}

    mock_web3.eth.send_transaction.return_value.hex.return_value = tx_hash
    mock_web3.eth.wait_for_transaction_receipt.return_value = receipt

    # Create and submit batch in parallel
    await transaction_manager.create_transaction_batch(
        batch_id, chain_id, transactions
    )
    results = await transaction_manager.submit_transaction_batch(
        chain_id, mock_web3, batch_id, parallel=True
    )

    assert len(results) == 2
    for result in results:
        assert result[0] == tx_hash
        assert result[1] == receipt
