"""
Tests for the blockchain chain manager.
"""
import asyncio
import pytest
import logging
import time
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.exceptions import ChainConnectionError
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    logger.debug("Setting up event loop")
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    logger.debug("Cleaning up event loop")
    loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    logger.debug("Creating mock Web3 instance")
    # Create base mock
    mock = AsyncMock()
    mock.__class__ = AsyncWeb3
    mock.eth = AsyncMock()

    # Configure eth mock methods with immediate returns
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.eth.get_block_number = AsyncMock(return_value=1000)
    mock.eth.get_balance = AsyncMock(return_value=1000000)
    mock.eth.get_transaction_count = AsyncMock(return_value=10)
    mock.eth.get_block = AsyncMock(return_value={'timestamp': int(time.time())})
    mock.eth.get_transaction = AsyncMock(return_value={'blockNumber': 1000})
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})

    # Configure Web3 instance methods with immediate returns
    async def quick_connect():
        return True
    async def quick_disconnect():
        return True
    async def quick_is_connected():
        return True

    mock.connect = AsyncMock(side_effect=quick_connect)
    mock.disconnect = AsyncMock(side_effect=quick_disconnect)
    mock.is_connected = AsyncMock(side_effect=quick_is_connected)

    # Mock provider
    mock_provider = AsyncMock(spec=AsyncHTTPProvider)
    mock_provider.is_connected = AsyncMock(return_value=True)
    mock.provider = mock_provider

    logger.debug("Mock Web3 instance created with async methods")
    return mock


@pytest.fixture
def chain_manager(event_loop, mock_web3, request):
    """Create a chain manager instance."""
    logger.debug("Creating chain manager instance")
    manager = ChainManager()

    # Create mock protocol adapter
    mock_adapter = AsyncMock()
    mock_adapter.web3 = mock_web3
    mock_adapter.configure_web3 = AsyncMock(return_value=None)
    mock_adapter.validate_connection = AsyncMock(return_value=True)
    mock_adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    mock_adapter.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock_adapter.get_contract = AsyncMock(return_value=mock_web3.eth.contract())
    mock_adapter.deploy_contract = AsyncMock(return_value={
        'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'abi': [],
        'bytecode': '0x'
    })

    logger.debug("Starting chain manager")
    event_loop.run_until_complete(manager.start())

    # Register ethereum protocol adapter
    logger.debug("Registering ethereum protocol adapter")
    event_loop.run_until_complete(manager.register_protocol_adapter('ethereum', mock_adapter))

    # Configure with test chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1,
            "protocol": "ethereum"
        }
    }

    logger.debug("Configuring chain manager with test chain")
    try:
        with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
            event_loop.run_until_complete(manager.configure(config))
            logger.debug("Chain manager configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure chain manager: {e}")
        raise

    async def cleanup():
        logger.debug("Starting chain manager cleanup")
        # Cancel all monitoring tasks
        for task in manager._status_monitors.values():
            logger.debug("Cancelling monitoring task")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        logger.debug("Stopping chain manager")
        await manager.stop()
        logger.debug("Chain manager cleanup complete")

    def sync_cleanup():
        event_loop.run_until_complete(cleanup())

    request.addfinalizer(sync_cleanup)
    return manager


@pytest.mark.asyncio
async def test_chain_initialization(chain_manager):
    """Test chain manager initialization."""
    logger.debug("Starting chain initialization test")
    assert chain_manager is not None

    logger.debug("Checking if chain manager is running")
    is_running = await chain_manager.is_running()
    assert is_running is True

    logger.debug("Chain initialization test complete")


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

    async with patch.object(AsyncWeb3, '__new__', return_value=mock_web3):
        with pytest.raises(ChainConnectionError):
            await chain_manager.configure({
                "test_chain": {
                    "rpc_url": "http://localhost:8545",
                    "chain_id": 1
                }
            })
