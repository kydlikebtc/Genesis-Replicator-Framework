"""
Tests for the blockchain chain manager protocol adapters.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.exceptions import BlockchainError
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
    """Create a mock Web3 instance with proper async connection handling."""
    mock = AsyncMock()
    mock.__class__ = AsyncWeb3
    mock.eth = AsyncMock()
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.eth.get_balance = AsyncMock(return_value=1000000)
    mock.eth.gas_price = AsyncMock(return_value=20000000000)
    mock.eth.estimate_gas = AsyncMock(return_value=21000)
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'hash': '0x123',
        'transactions': [],
        'timestamp': 1234567890,
        'baseFeePerGas': 1000000000
    })
    mock.eth.send_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    mock.eth.contract = AsyncMock()
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = AsyncMock(return_value=True)

    # Mock provider
    mock_provider = AsyncMock(spec=AsyncHTTPProvider)
    mock_provider.is_connected = AsyncMock(return_value=True)
    mock.provider = mock_provider

    return mock


@pytest.fixture
async def chain_manager(mock_web3):
    """Create a chain manager instance."""
    manager = ChainManager()
    await manager.start()

    # Create mock protocol adapters
    ethereum_adapter = AsyncMock()
    ethereum_adapter.web3 = mock_web3
    ethereum_adapter.configure_web3 = AsyncMock(return_value=None)
    ethereum_adapter.validate_connection = AsyncMock(return_value=True)
    ethereum_adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    ethereum_adapter.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    ethereum_adapter.get_contract = AsyncMock(return_value=mock_web3.eth.contract())
    ethereum_adapter.deploy_contract = AsyncMock(return_value={
        'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'abi': [],
        'bytecode': '0x'
    })
    ethereum_adapter.is_connected = AsyncMock(return_value=True)

    bnb_adapter = AsyncMock()
    bnb_adapter.web3 = mock_web3
    bnb_adapter.configure_web3 = AsyncMock(return_value=None)
    bnb_adapter.validate_connection = AsyncMock(return_value=True)
    bnb_adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    bnb_adapter.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    bnb_adapter.get_contract = AsyncMock(return_value=mock_web3.eth.contract())
    bnb_adapter.deploy_contract = AsyncMock(return_value={
        'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'abi': [],
        'bytecode': '0x'
    })
    bnb_adapter.is_connected = AsyncMock(return_value=True)

    # Register protocol adapters
    await manager.register_protocol_adapter("ethereum", ethereum_adapter)
    await manager.register_protocol_adapter("bnb", bnb_adapter)

    # Configure with test chains
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1,
            "protocol": "ethereum"
        },
        "test_bnb": {
            "rpc_url": "http://localhost:8546",
            "chain_id": 56,
            "protocol": "bnb"
        }
    }

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        await manager.configure(config)

    yield manager

    # Cleanup
    for task in manager._status_monitors.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await manager.stop()


@pytest.mark.asyncio
async def test_register_protocol_adapter(chain_manager):
    """Test registering a protocol adapter."""
    adapter = AsyncMock()
    adapter.web3 = AsyncMock()
    adapter.web3.__class__ = AsyncWeb3
    adapter.configure_web3 = AsyncMock(return_value=None)
    adapter.validate_connection = AsyncMock(return_value=True)
    adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))

    await chain_manager.register_protocol_adapter("test_protocol", adapter)
    assert "test_protocol" in chain_manager._protocol_adapters


@pytest.mark.asyncio
async def test_connect_with_protocol(chain_manager, mock_web3):
    """Test connecting to a chain with a protocol adapter."""
    chain_id = "test_protocol_chain"
    protocol = "ethereum"

    # Configure chain with protocol
    config = {
        chain_id: {
            "rpc_url": "http://localhost:8547",
            "chain_id": 1,
            "protocol": protocol
        }
    }

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        await chain_manager.configure(config)
        assert chain_id in chain_manager._connections
        assert await chain_manager._get_connection(chain_id) is not None


@pytest.mark.asyncio
async def test_execute_transaction_with_protocol(chain_manager, mock_web3):
    """Test executing a transaction with a protocol adapter."""
    chain_id = "test_chain"
    tx = {
        'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'value': 1000,
        'gas': 21000,
        'gasPrice': 20000000000
    }

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        tx_hash = await chain_manager.execute_transaction(chain_id, tx)
        assert tx_hash is not None
        assert isinstance(tx_hash, bytes)
