"""
Tests for the blockchain chain manager.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from genesis_replicator.foundation_services.exceptions import ChainConnectionError
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager


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
async def test_chain_initialization(chain_manager):
    """Test chain manager initialization."""
    assert chain_manager is not None
    assert await chain_manager.is_running() is True


@pytest.mark.asyncio
async def test_invalid_chain_configuration(chain_manager):
    """Test invalid chain configuration."""
    invalid_config = {
        "invalid_chain": {
            "rpc_url": "",  # Invalid URL
            "chain_id": -1  # Invalid chain ID
        }
    }

    with pytest.raises(ChainConnectionError):
        await chain_manager.configure(invalid_config)


@pytest.mark.asyncio
async def test_chain_connection_error(chain_manager, mock_web3):
    """Test chain connection error handling."""
    mock_web3.is_connected = AsyncMock(return_value=False)

    with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        with pytest.raises(ChainConnectionError):
            await chain_manager.configure({
                "test_chain": {
                    "rpc_url": "http://localhost:8545",
                    "chain_id": 1
                }
            })
