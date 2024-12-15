"""
Tests for the contract manager module.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.exceptions import (
    ChainConnectionError,
    ConfigurationError,
    ContractError
)

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
def web3_mock():
    """Create a mock Web3 instance."""
    mock = MagicMock()
    mock.eth = MagicMock()
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
    contract_mock.functions = MagicMock()
    contract_mock.functions.test = MagicMock(return_value=AsyncMock(return_value="test_result"))
    contract_mock.functions.balanceOf = MagicMock(return_value=AsyncMock(return_value=100))
    contract_mock.functions.test_var = MagicMock(return_value=AsyncMock(return_value="test_value"))

    # Mock events
    mock_event = MagicMock()
    mock_event_log = MagicMock()
    mock_event_log.args = {"param1": "value1"}
    mock_event_log.blockNumber = 1
    mock_event_log.transactionHash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    mock_event_log.logIndex = 0
    mock_event_log.blockHash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    mock_event.get_logs = AsyncMock(return_value=[mock_event_log])
    contract_mock.events = MagicMock()
    contract_mock.events.TestEvent = mock_event
    contract_mock.events.Transfer = mock_event

    mock.eth.contract = MagicMock(return_value=contract_mock)
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = MagicMock(return_value=True)
    return mock

@pytest.fixture
async def chain_manager(event_loop):
    """Create a ChainManager instance."""
    manager = ChainManager()
    await manager.start()
    mock = MagicMock()
    mock.eth = MagicMock()
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.is_connected = AsyncMock(return_value=True)

    with patch.object(AsyncWeb3, '__new__', return_value=mock):
        config = {
            "ethereum": {
                "rpc_url": "http://localhost:8545",
                "chain_id": 1
            }
        }
        await manager.configure(config)
        try:
            yield manager
        finally:
            await manager.stop()

@pytest.fixture
async def contract_manager(event_loop, chain_manager):
    """Create a ContractManager instance."""
    manager = ContractManager(chain_manager)
    await manager.start()
    try:
        yield manager
    finally:
        await manager.stop()

@pytest.mark.asyncio
async def test_contract_deployment(contract_manager, web3_mock):
    """Test contract deployment."""
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]
    contract_bytecode = "0x123456"

    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        contract_address = await contract_manager.deploy_contract(
            "test_contract",
            contract_abi,
            contract_bytecode,
            chain_id="ethereum"
        )

    assert contract_address is not None
    web3_mock.eth.contract.assert_called()

@pytest.mark.asyncio
async def test_contract_interaction(contract_manager, web3_mock):
    """Test contract interaction."""
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]

    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
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

@pytest.mark.asyncio
async def test_contract_event_monitoring(contract_manager, web3_mock):
    """Test contract event monitoring."""
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
    async def event_callback(event):
        events.append(event)

    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        await contract_manager.register_contract(
            "test_contract",
            contract_address,
            contract_abi,
            chain_id="ethereum"
        )

        async for event in contract_manager.monitor_events(
            "ethereum",
            contract_address,
            "TestEvent",
            from_block=0,
            to_block=100
        ):
            events.append(event)
            break  # Only process one event for testing

    assert len(events) == 1
    assert events[0]["event"] == "TestEvent"
    assert events[0]["args"]["param1"] == "value1"
    assert events[0]["block_number"] == 1
    assert events[0]["transaction_hash"].startswith("0x")  # Verify hex format
    assert events[0]["chain_id"] == "ethereum"

@pytest.mark.asyncio
async def test_contract_validation(contract_manager):
    """Test contract validation."""
    with pytest.raises(ContractError, match="Invalid contract parameters"):
        await contract_manager.deploy_contract(
            "",  # Invalid contract_id
            [],  # Empty ABI
            "",  # Empty bytecode
            chain_id="ethereum"
        )

@pytest.mark.asyncio
async def test_contract_state_management(contract_manager, web3_mock):
    """Test contract state management."""
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test_var", "inputs": [], "outputs": []}]

    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
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

@pytest.mark.asyncio
async def test_contract_error_handling(contract_manager, web3_mock):
    """Test contract error handling."""
    web3_mock.eth.contract.side_effect = Exception("Contract creation failed")

    with pytest.raises(ContractError):
        await contract_manager.deploy_contract(
            "test_contract",
            [],
            "0x",
            chain_id="ethereum"
        )
