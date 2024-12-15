"""
Tests for the blockchain chain manager protocol adapters.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3

from genesis_replicator.foundation_services.exceptions import ProtocolError
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.protocols.ethereum import EthereumAdapter
from genesis_replicator.foundation_services.blockchain_integration.protocols.bnb_chain import BNBChainAdapter


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
async def mock_web3():
    """Create a mock Web3 instance."""
    mock = MagicMock(spec=AsyncWeb3)
    mock.eth = MagicMock()
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.eth.get_balance = AsyncMock(return_value=1000000)
    mock.eth.gas_price = AsyncMock(return_value=20000000000)
    mock.eth.estimate_gas = AsyncMock(return_value=21000)
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'hash': '0x123',
        'transactions': []
    })
    mock.eth.send_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    mock.is_connected = AsyncMock(return_value=True)
    return mock


@pytest.fixture
async def chain_manager(event_loop, mock_web3):
    """Create a chain manager instance."""
    manager = ChainManager()
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


@pytest.mark.asyncio
async def test_register_protocol_adapter(chain_manager):
    """Test registering a protocol adapter."""
    adapter = EthereumAdapter()
    await chain_manager.register_protocol_adapter("ethereum", adapter)
    assert "ethereum" in chain_manager._protocol_adapters


@pytest.mark.asyncio
async def test_connect_with_protocol(chain_manager, mock_web3):
    """Test connecting to a chain with a protocol adapter."""
    adapter = EthereumAdapter()
    await chain_manager.register_protocol_adapter("ethereum", adapter)

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        await chain_manager.connect_to_chain("test_chain", "ethereum")
        assert await chain_manager.is_connected("test_chain") is True


@pytest.mark.asyncio
async def test_execute_transaction_with_protocol(chain_manager, mock_web3):
    """Test executing a transaction with a protocol adapter."""
    adapter = EthereumAdapter()
    await chain_manager.register_protocol_adapter("ethereum", adapter)

    tx = {
        'from': '0x123',
        'to': '0x456',
        'value': 1000
    }

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        tx_hash = await chain_manager.execute_transaction("test_chain", tx)
        assert tx_hash is not None
