"""
Tests for BNB Chain protocol implementation.
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from genesis_replicator.foundation_services.blockchain_integration.protocols.bnb_chain import BNBChainAdapter
from genesis_replicator.foundation_services.blockchain_integration.batch_processor import BatchProcessor
from genesis_replicator.foundation_services.exceptions import (
    BlockchainError,
    ChainConnectionError,
    ContractError
)

@pytest.fixture
async def bnb_chain_adapter():
    """Create BNB Chain adapter instance for testing."""
    adapter = BNBChainAdapter()
    await adapter.initialize()
    yield adapter
    await adapter.cleanup()

@pytest.fixture
async def web3_mock():
    """Create Web3 mock for BNB Chain testing."""
    mock = AsyncMock()
    mock.__class__ = AsyncWeb3
    eth_mock = AsyncMock()

    # Setup eth mock methods
    eth_mock.chain_id = AsyncMock(return_value=56)  # BNB Chain ID
    eth_mock.gas_price = AsyncMock(return_value=5000000000)  # 5 Gwei
    eth_mock.estimate_gas = AsyncMock(return_value=21000)
    eth_mock.get_block = AsyncMock(return_value={
        'number': 1000,
        'timestamp': 1234567890,
        'hash': '0x123...',
        'transactions': []
    })

    mock.eth = eth_mock
    return mock

@pytest.mark.asyncio
async def test_bnb_chain_gas_estimation(bnb_chain_adapter, web3_mock):
    """Test BNB Chain-specific gas estimation with buffers."""
    # Test gas limit estimation with 10% buffer
    tx = {
        'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'value': 1000000000000000  # 0.001 BNB
    }

    base_gas = await web3_mock.eth.estimate_gas(tx)
    buffered_gas = await bnb_chain_adapter.estimate_gas_limit(web3_mock, tx)

    assert buffered_gas == int(base_gas * 1.1)  # Verify 10% buffer

    # Test gas price estimation with 5% buffer
    base_price = await web3_mock.eth.gas_price
    buffered_price = await bnb_chain_adapter.estimate_gas_price(web3_mock)

    assert buffered_price == int(base_price * 1.05)  # Verify 5% buffer

@pytest.mark.asyncio
async def test_bnb_chain_transaction_batch(bnb_chain_adapter, web3_mock):
    """Test BNB Chain transaction batch processing."""
    processor = BatchProcessor()

    # Configure batch processor for BNB Chain
    await processor.configure_chain(
        chain_id=56,  # BNB Chain ID
        batch_size=50,  # BNB Chain optimal batch size
        batch_interval=0.1,
        max_retries=3
    )

    # Create test transactions
    transactions = []
    for i in range(10):
        tx = {
            'to': f'0x{i:040x}',
            'value': 1000000000000000,  # 0.001 BNB
            'gas': 21000,
            'maxFeePerGas': 5000000000,  # 5 Gwei
            'maxPriorityFeePerGas': 2000000000  # 2 Gwei
        }
        transactions.append(tx)

    # Process transactions
    results = []
    for tx in transactions:
        await processor.add_transaction(tx)

    async for result in processor.process_batch():
        results.append(result)

    assert len(results) == 10

@pytest.mark.asyncio
async def test_bnb_chain_event_monitoring(bnb_chain_adapter, web3_mock):
    """Test BNB Chain event monitoring capabilities."""
    contract_address = "0x0000000000000000000000000000000000000000"
    event_name = "Transfer"

    # Mock event data
    events = [
        {
            'event': 'Transfer',
            'args': {
                'from': '0x123...',
                'to': '0x456...',
                'value': 1000000000000000000
            },
            'blockNumber': 1000,
            'transactionHash': '0x789...',
            'logIndex': 0
        }
    ]

    with patch.object(bnb_chain_adapter, '_get_events', return_value=events):
        monitored_events = []
        async for event in bnb_chain_adapter.monitor_events(
            web3_mock,
            contract_address,
            event_name,
            from_block=900
        ):
            monitored_events.append(event)
            if len(monitored_events) >= len(events):
                break

        assert len(monitored_events) == 1
        assert monitored_events[0]['event'] == 'Transfer'
        assert monitored_events[0]['blockNumber'] == 1000

@pytest.mark.asyncio
async def test_bnb_chain_error_handling(bnb_chain_adapter, web3_mock):
    """Test BNB Chain-specific error handling."""
    # Test network error handling
    with patch.object(web3_mock.eth, 'chain_id', side_effect=Web3Exception("Network error")):
        with pytest.raises(ChainConnectionError):
            await bnb_chain_adapter.validate_chain_connection(web3_mock)

    # Test gas estimation error
    with patch.object(web3_mock.eth, 'estimate_gas', side_effect=Web3Exception("Gas estimation failed")):
        with pytest.raises(BlockchainError):
            await bnb_chain_adapter.estimate_gas_limit(web3_mock, {
                'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
                'value': 1000000000000000
            })

@pytest.mark.asyncio
async def test_bnb_chain_performance(bnb_chain_adapter, web3_mock):
    """Test BNB Chain performance under load."""
    processor = BatchProcessor()

    # Configure for high throughput
    await processor.configure_chain(
        chain_id=56,
        batch_size=100,
        batch_interval=0.05,
        max_retries=3
    )

    # Generate large number of transactions
    transactions = []
    for i in range(1000):
        tx = {
            'to': f'0x{i:040x}',
            'value': 1000000000000000,
            'gas': 21000,
            'maxFeePerGas': 5000000000,
            'maxPriorityFeePerGas': 2000000000
        }
        transactions.append(tx)

    # Process in parallel
    start_time = asyncio.get_event_loop().time()

    tasks = []
    for tx in transactions:
        task = asyncio.create_task(processor.add_transaction(tx))
        tasks.append(task)

    await asyncio.gather(*tasks)

    processed = []
    async for result in processor.process_batch():
        processed.append(result)
        if len(processed) >= len(transactions):
            break

    end_time = asyncio.get_event_loop().time()
    processing_time = end_time - start_time

    assert len(processed) == len(transactions)
    assert processing_time < 30  # Should process 1000 tx in under 30 seconds
