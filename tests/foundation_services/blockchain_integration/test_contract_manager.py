"""
Tests for the contract manager module.
"""
import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.protocols.ethereum import EthereumAdapter
from genesis_replicator.foundation_services.blockchain_integration.protocols.base import BaseProtocolAdapter
from genesis_replicator.foundation_services.blockchain_integration.exceptions import (
    ChainConnectionError,
    ChainConfigError,
    ContractError
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
async def web3_mock():
    """Create a mock Web3 instance."""
    mock = AsyncMock(spec=AsyncWeb3)
    mock.eth = AsyncMock()

    # Mock contract
    contract_mock = AsyncMock(spec=AsyncContract)
    contract_mock.functions = AsyncMock()
    contract_mock.functions.test = AsyncMock()
    contract_mock.functions.test.call = AsyncMock(return_value="test_result")
    contract_mock.functions.test_var = AsyncMock()
    contract_mock.functions.test_var.call = AsyncMock(return_value="test_value")

    # Mock events
    contract_mock.events = AsyncMock()
    contract_mock.events.TestEvent = AsyncMock()
    contract_mock.events.TestEvent.create_filter = AsyncMock()
    filter_mock = AsyncMock()
    filter_mock.get_all_entries = AsyncMock(return_value=[{
        "args": {"param1": "value1"},
        "event": "TestEvent",
        "blockNumber": 1,
        "transactionHash": "0x1234"
    }])
    contract_mock.events.TestEvent.create_filter.return_value = filter_mock

    # Set up contract creation mock
    mock.eth.contract = AsyncMock(return_value=contract_mock)
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_code = AsyncMock(return_value='0x123456')
    mock.is_connected = AsyncMock(return_value=True)
    mock.provider = AsyncMock(spec=AsyncHTTPProvider)
    mock.provider.is_connected = AsyncMock(return_value=True)

    return mock

@pytest.fixture
async def chain_manager(web3_mock):
    """Create a ChainManager instance."""
    logger.debug("Creating chain manager instance")

    class AsyncChainManagerContext:
        def __init__(self, web3_mock):
            self.web3_mock = web3_mock
            self.manager = None

        async def __aenter__(self):
            # Await the web3_mock before using it
            self.web3_mock = await self.web3_mock

            self.manager = ChainManager()
            await self.manager.initialize()

            # Create mock protocol adapter that inherits from BaseProtocolAdapter
            class MockAdapter(BaseProtocolAdapter):
                def __init__(self, web3_mock):
                    super().__init__()
                    self.web3 = web3_mock
                    self._initialized = False

                async def configure_web3(self, provider_url):
                    return self.web3

                async def validate_connection(self):
                    return True

                async def connect(self, credentials):
                    """Connect to the chain and add to connection pool."""
                    self.web3 = await self.configure_web3(credentials['rpc_url'])
                    # Add connection to pool
                    if not hasattr(self, '_connection_pool'):
                        self._connection_pool = {}
                    if credentials['chain_id'] not in self._connection_pool:
                        self._connection_pool[credentials['chain_id']] = []
                    self._connection_pool[credentials['chain_id']].append(self.web3)
                    return True

                async def execute_transaction(self, *args, **kwargs):
                    return bytes.fromhex('1234')

                async def get_transaction_receipt(self, *args, **kwargs):
                    return {'status': 1}

                async def get_contract(self, *args, **kwargs):
                    return self.web3.eth.contract()

                async def deploy_contract(self, *args, **kwargs):
                    return {
                        'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
                        'abi': [],
                        'bytecode': '0x'
                    }

                async def validate_contract(self, *args, **kwargs):
                    return True

                async def get_contract_events(self, *args, **kwargs):
                    return [{
                        'event': 'TestEvent',
                        'args': {'param1': 'value1'},
                        'blockNumber': 1,
                        'transactionHash': '0x1234'
                    }]

                async def get_contract_state(self, *args, **kwargs):
                    return {'test_var': 'test_value'}

                async def call_contract_method(self, *args, **kwargs):
                    return 'test_result'

                async def estimate_gas(self, *args, **kwargs):
                    return 100000

                async def get_balance(self, *args, **kwargs):
                    return 1000000000000000000  # 1 ETH in wei

                async def get_block(self, *args, **kwargs):
                    return {
                        'number': 1,
                        'hash': '0x1234',
                        'timestamp': 1234567890
                    }

                async def get_gas_price(self, *args, **kwargs):
                    return 20000000000  # 20 gwei

                async def send_transaction(self, *args, **kwargs):
                    return '0x1234567890abcdef'

                async def validate_address(self, address):
                    return True

            # Create mock adapter with web3_mock
            mock_adapter = MockAdapter(self.web3_mock)

            # Register protocol adapter
            await self.manager.register_protocol_adapter("ethereum", mock_adapter)

            config = {
                "ethereum": {
                    "rpc_url": "http://localhost:8545",
                    "chain_id": 1,
                    "protocol": "ethereum"
                }
            }
            await self.manager.configure(config)

            return self.manager

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.manager:
                await self.manager.cleanup()

    return AsyncChainManagerContext(web3_mock)

@pytest.fixture
async def contract_manager(chain_manager, web3_mock):
    """Create a contract manager instance."""
    class AsyncContractManagerContext:
        def __init__(self, chain_manager, web3_mock):
            self.chain_manager = chain_manager
            self.web3_mock = web3_mock
            self.manager = None

        async def __aenter__(self):
            # Initialize chain manager context
            chain_manager_ctx = await self.chain_manager
            async with chain_manager_ctx as chain_mgr:
                # Create and initialize contract manager
                self.manager = ContractManager(chain_mgr)
                await self.manager.start()
                return self.manager

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.manager:
                await self.manager.cleanup()

    return AsyncContractManagerContext(chain_manager, web3_mock)

@pytest.mark.asyncio
async def test_contract_deployment(contract_manager, web3_mock):
    """Test contract deployment."""
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = []
    contract_bytecode = "0x"

    ctx = await contract_manager
    async with ctx as manager:
        with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
            result = await manager.deploy_contract(
                "test_contract",
                contract_abi,
                contract_bytecode,
                chain_id="ethereum"
            )

            assert result['address'] == contract_address
            assert result['abi'] == contract_abi
            assert result['bytecode'] == contract_bytecode

@pytest.mark.asyncio
async def test_contract_interaction(contract_manager, web3_mock):
    """Test contract interaction."""
    logger.debug("Starting contract interaction test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]

    ctx = await contract_manager
    async with ctx as manager:
        with patch('web3.AsyncWeb3', return_value=web3_mock):
            await manager.register_contract(
                "test_contract",
                contract_address,
                contract_abi,
                chain_id="ethereum"
            )
            result = await manager.call_contract_method(
                contract_address,
                "test",
                [],
                chain_id="ethereum"
            )
            assert result == "test_result"

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

    ctx = await contract_manager
    async with ctx as manager:
        try:
            with patch('web3.AsyncWeb3', return_value=web3_mock):
                await manager.register_contract(
                    "test_contract",
                    contract_address,
                    contract_abi,
                    chain_id="ethereum"
                )

                event_task = asyncio.create_task(
                    manager.monitor_events(
                        "ethereum",
                        contract_address,
                        "TestEvent",
                        callback=event_callback,
                        from_block=0,
                        to_block=100
                    )
                )

                await asyncio.sleep(0.1)  # Allow event processing
                assert len(events) > 0  # Should have received events
        finally:
            if event_task and not event_task.done():
                event_task.cancel()
                try:
                    await event_task
                except asyncio.CancelledError:
                    pass

@pytest.mark.asyncio
async def test_contract_validation(contract_manager):
    """Test contract validation."""
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = []

    ctx = await contract_manager
    async with ctx as manager:
        result = await manager.validate_contract(
            contract_address,
            chain_id="ethereum"
        )
        assert result is True

@pytest.mark.asyncio
async def test_contract_state_management(contract_manager, web3_mock):
    """Test contract state management."""
    logger.debug("Starting contract state management test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test_var", "inputs": [], "outputs": []}]

    ctx = await contract_manager
    async with ctx as manager:
        with patch('web3.AsyncWeb3', return_value=web3_mock):
            await manager.register_contract(
                "test_contract",
                contract_address,
                contract_abi,
                chain_id="ethereum"
            )

            state = await manager.get_contract_state(
                contract_address,
                chain_id="ethereum"
            )
            assert state == {"test_var": "test_value"}

@pytest.mark.asyncio
async def test_contract_error_handling(contract_manager, web3_mock):
    """Test contract error handling."""
    logger.debug("Starting contract error handling test")
    contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]

    ctx = await contract_manager
    async with ctx as manager:
        # Test invalid contract address
        with pytest.raises(ContractError, match="Invalid contract address"):
            await manager.call_contract_method(
                "invalid_address",
                "test",
                [],
                chain_id="ethereum"
            )

        # Test invalid chain ID
        with pytest.raises(ChainConnectionError, match="Chain not found"):
            await manager.call_contract_method(
                contract_address,
                "test",
                [],
                chain_id="invalid_chain"
            )

        # Test contract creation failure
        with pytest.raises(ContractError, match="Contract creation failed"):
            web3_mock.eth.contract.side_effect = Exception("Contract creation failed")
            await manager.deploy_contract(
                "test_contract",
                [],
                "0x",
                chain_id="ethereum"
            )

        # Test method execution failure
        with patch('web3.AsyncWeb3', return_value=web3_mock):
            await manager.register_contract(
                "test_contract",
                contract_address,
                contract_abi,
                chain_id="ethereum"
            )
            with pytest.raises(ContractError, match="Contract method execution failed"):
                web3_mock.eth.contract().functions.test.call.side_effect = Exception("Method execution failed")
                await manager.call_contract_method(
                    contract_address,
                    "test",
                    [],
                    chain_id="ethereum"
                )

    logger.debug("Contract error handling test complete")
