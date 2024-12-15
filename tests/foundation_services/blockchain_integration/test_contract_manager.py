"""
Tests for the contract manager module.
"""
import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.protocols.ethereum import EthereumAdapter
from genesis_replicator.foundation_services.blockchain_integration.exceptions import (
    ChainConnectionError,
    ConfigurationError,
    ContractError
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for each test case."""
    logger.debug("Setting up event loop")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    logger.debug("Cleaning up event loop")
    loop.close()
    asyncio.set_event_loop(None)

@pytest.fixture
async def web3_mock():
    """Create a mock Web3 instance with proper async connection handling."""
    # Create base mock
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
        'timestamp': 1234567890,
        'hash': '0x1234567890abcdef'
    })
    mock.eth.send_transaction = AsyncMock(return_value='0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')

    # Contract-specific mocks
    contract_mock = AsyncMock(spec=AsyncContract)
    contract_mock.functions = AsyncMock()
    contract_mock.functions.test = AsyncMock(return_value=AsyncMock(return_value="test_result"))
    contract_mock.functions.balanceOf = AsyncMock(return_value=AsyncMock(return_value=100))
    contract_mock.functions.test_var = AsyncMock(return_value=AsyncMock(return_value="test_value"))

    # Mock events
    mock_event = AsyncMock()
    mock_event_log = MagicMock()
    mock_event_log.args = {"param1": "value1"}
    mock_event_log.blockNumber = 1
    mock_event_log.transactionHash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    mock_event_log.logIndex = 0
    mock_event_log.blockHash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    mock_event.get_logs = AsyncMock(return_value=[mock_event_log])
    contract_mock.events = AsyncMock()
    contract_mock.events.TestEvent = mock_event
    contract_mock.events.Transfer = mock_event

    mock.eth.contract = AsyncMock(return_value=contract_mock)
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = AsyncMock(return_value=True)

    # Mock provider
    mock_provider = AsyncMock(spec=AsyncHTTPProvider)
    mock_provider.is_connected = AsyncMock(return_value=True)
    mock.provider = mock_provider

    return mock

@pytest.fixture
def chain_manager(event_loop, web3_mock, request):
    """Create a ChainManager instance."""
    logger.debug("Creating chain manager instance")

    manager = ChainManager()
    event_loop.run_until_complete(manager.start())

    # Create mock protocol adapter
    mock_adapter = AsyncMock()
    mock_adapter.web3 = web3_mock
    mock_adapter.configure_web3 = AsyncMock(return_value=None)
    mock_adapter.validate_connection = AsyncMock(return_value=True)
    mock_adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    mock_adapter.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock_adapter.get_contract = AsyncMock(return_value=web3_mock.eth.contract())
    mock_adapter.deploy_contract = AsyncMock(return_value={
        'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'abi': [],
        'bytecode': '0x'
    })
    mock_adapter.validate_contract = AsyncMock(return_value=True)
    mock_adapter.get_contract_events = AsyncMock(return_value=[{
        'event': 'TestEvent',
        'args': {'param1': 'value1'},
        'blockNumber': 1,
        'transactionHash': '0x1234'
    }])
    mock_adapter.get_contract_state = AsyncMock(return_value={'test_var': 'test_value'})
    mock_adapter.call_contract_method = AsyncMock(return_value='test_result')

    # Register protocol adapter
    event_loop.run_until_complete(manager.register_protocol_adapter("ethereum", mock_adapter))

    config = {
        "ethereum": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1,
            "protocol": "ethereum"
        }
    }
    event_loop.run_until_complete(manager.configure(config))

    def cleanup():
        logger.debug("Cleaning up chain manager")
        event_loop.run_until_complete(manager.stop())
        logger.debug("Chain manager cleanup complete")

    request.addfinalizer(cleanup)
    return manager

@pytest.fixture
def contract_manager(event_loop, chain_manager, request):
    """Create a ContractManager instance."""
    logger.debug("Creating contract manager instance")
    manager = ContractManager(chain_manager)
    event_loop.run_until_complete(manager.start())

    # Store event monitoring tasks for cleanup
    manager._event_tasks = set()

    def cleanup():
        logger.debug("Cleaning up contract manager")
        # Cancel all event monitoring tasks
        for task in manager._event_tasks:
            task.cancel()
            try:
                event_loop.run_until_complete(task)
            except asyncio.CancelledError:
                pass
        event_loop.run_until_complete(manager.stop())
        logger.debug("Contract manager cleanup complete")

    request.addfinalizer(cleanup)
    return manager

@pytest.mark.asyncio
async def test_contract_deployment(contract_manager, web3_mock):
    """Test contract deployment."""
    logger.debug("Starting contract deployment test")
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]
    contract_bytecode = "0x123456"

    with patch('web3.AsyncWeb3', return_value=web3_mock):
        contract_address = await contract_manager.deploy_contract(
            "test_contract",
            contract_abi,
            contract_bytecode,
            chain_id="ethereum"
        )

    assert contract_address is not None
    web3_mock.eth.contract.assert_called()
    logger.debug("Contract deployment test complete")

@pytest.mark.asyncio
async def test_contract_interaction(contract_manager, web3_mock):
    """Test contract interaction."""
    logger.debug("Starting contract interaction test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]

    with patch('web3.AsyncWeb3', return_value=web3_mock):
        await contract_manager.register_contract(
            "test_contract",
            contract_address,
            contract_abi,
            chain_id="ethereum"
        )
        result = await contract_manager.call_contract_method(
            contract_address,
            "test",
            [],
            chain_id="ethereum"
        )

    assert result == "test_result"
    logger.debug("Contract interaction test complete")

@pytest.mark.asyncio
async def test_contract_event_monitoring(contract_manager, web3_mock):
    """Test contract event monitoring."""
    logger.debug("Starting contract event monitoring test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [
        {
            "type": "event",
            "name": "TestEvent",
            "inputs": [
                {"name": "param1", "type": "string", "indexed": False}
            ]
        }
    ]

    events = []
    event_task = None

    async def event_callback(event):
        events.append(event)

    with patch('web3.AsyncWeb3', return_value=web3_mock):
        await contract_manager.register_contract(
            "test_contract",
            contract_address,
            contract_abi,
            chain_id="ethereum"
        )

        # Create event monitoring task
        event_task = asyncio.create_task(
            contract_manager.monitor_events(
                "ethereum",
                contract_address,
                "TestEvent",
                from_block=0,
                to_block=100
            ).__aiter__().__anext__()
        )
        contract_manager._event_tasks.add(event_task)

        try:
            event = await asyncio.wait_for(event_task, timeout=5.0)
            events.append(event)
        except asyncio.TimeoutError:
            logger.error("Event monitoring timed out")
            raise
        finally:
            if event_task and not event_task.done():
                event_task.cancel()
                try:
                    await event_task
                except (asyncio.CancelledError, StopAsyncIteration):
                    pass

    assert len(events) == 1
    assert events[0]["event"] == "TestEvent"
    assert events[0]["args"]["param1"] == "value1"
    assert events[0]["block_number"] == 1
    assert events[0]["transaction_hash"].startswith("0x")  # Verify hex format
    assert events[0]["chain_id"] == "ethereum"
    logger.debug("Contract event monitoring test complete")

@pytest.mark.asyncio
async def test_contract_validation(contract_manager):
    """Test contract validation."""
    logger.debug("Starting contract validation test")
    with pytest.raises(ContractError, match="Invalid contract parameters"):
        await contract_manager.deploy_contract(
            "",  # Invalid contract_id
            [],  # Empty ABI
            "",  # Empty bytecode
            chain_id="ethereum"
        )
    logger.debug("Contract validation test complete")

@pytest.mark.asyncio
async def test_contract_state_management(contract_manager, web3_mock):
    """Test contract state management."""
    logger.debug("Starting contract state management test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test_var", "inputs": [], "outputs": []}]

    with patch('web3.AsyncWeb3', return_value=web3_mock):
        await contract_manager.register_contract(
            "test_contract",
            contract_address,
            contract_abi,
            chain_id="ethereum"
        )
        state = await contract_manager.get_contract_state(
            contract_address,
            "test_var",
            chain_id="ethereum"
        )

    assert state == "test_value"
    logger.debug("Contract state management test complete")

@pytest.mark.asyncio
async def test_contract_error_handling(contract_manager, web3_mock):
    """Test contract error handling."""
    logger.debug("Starting contract error handling test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]

    # Test invalid contract address
    with pytest.raises(ContractError, match="Invalid contract address"):
        await contract_manager.call_contract_method(
            "invalid_address",
            "test",
            [],
            chain_id="ethereum"
        )

    # Test invalid chain ID
    with pytest.raises(ChainConnectionError, match="Chain not found"):
        await contract_manager.call_contract_method(
            contract_address,
            "test",
            [],
            chain_id="invalid_chain"
        )

    # Test contract creation failure
    with pytest.raises(ContractError, match="Contract creation failed"):
        web3_mock.eth.contract.side_effect = Exception("Contract creation failed")
        await contract_manager.deploy_contract(
            "test_contract",
            [],
            "0x",
            chain_id="ethereum"
        )

    # Test method execution failure
    with patch('web3.AsyncWeb3', return_value=web3_mock):
        await contract_manager.register_contract(
            "test_contract",
            contract_address,
            contract_abi,
            chain_id="ethereum"
        )
        with pytest.raises(ContractError, match="Contract method execution failed"):
            web3_mock.eth.contract().functions.test = AsyncMock(side_effect=Exception("Method execution failed"))
            await contract_manager.call_contract_method(
                contract_address,
                "test",
                [],
                chain_id="ethereum"
            )

    logger.debug("Contract error handling test complete")
