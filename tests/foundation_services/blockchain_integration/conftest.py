"""
Global test configuration and fixtures for blockchain integration tests.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from web3 import AsyncWeb3, Web3
from web3.providers.async_base import AsyncBaseProvider
from web3.types import Wei, TxParams

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager
from genesis_replicator.foundation_services.blockchain_integration.transaction_manager import TransactionManager
from genesis_replicator.foundation_services.blockchain_integration.protocols.base import BaseProtocolAdapter

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Original isinstance to preserve Python's built-in behavior
original_isinstance = isinstance

def patched_isinstance(obj, classinfo):
    """
    Patched isinstance that handles Web3 type checking properly.
    """
    # Handle tuple of types
    if original_isinstance(classinfo, tuple):
        return any(patched_isinstance(obj, t) for t in classinfo)

    # Special case for Web3 instances and mocks
    if classinfo in (AsyncWeb3,):
        # Check if object has the necessary Web3 attributes and is a mock
        if asyncio.iscoroutine(obj):
            return False
        if original_isinstance(obj, (MagicMock)):
            return hasattr(obj, 'eth') and hasattr(obj, 'provider')
        return original_isinstance(obj, classinfo)

    # Special case for BaseProtocolAdapter
    if classinfo == BaseProtocolAdapter:
        # Check if object is a subclass or instance of BaseProtocolAdapter
        if original_isinstance(obj, type):
            return issubclass(obj, BaseProtocolAdapter)
        return original_isinstance(obj, BaseProtocolAdapter)

    # Handle mock objects
    if original_isinstance(obj, (MagicMock)) and hasattr(classinfo, '__name__'):
        # Check if the mock was created with the correct spec
        if hasattr(obj, '_mock_spec'):
            return classinfo == obj._mock_spec
        if hasattr(obj, '_spec_class'):
            return classinfo == obj._spec_class
        return False

    # For all other cases, use original isinstance
    return original_isinstance(obj, classinfo)

@pytest.fixture(scope="session", autouse=True)
def patch_isinstance():
    """Patch isinstance for Web3 type checking."""
    with patch('builtins.isinstance', patched_isinstance):
        yield

@pytest.fixture(scope="function")
def event_loop():
    """Create new event loop for each test."""
    logger = logging.getLogger(__name__)
    logger.debug("Creating new event loop")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    logger.debug("Closing event loop")
    loop.close()

@pytest.fixture
async def base_web3_mock():
    """Create a base Web3 mock for testing."""
    mock_provider = AsyncMock(spec=AsyncBaseProvider)
    mock_provider.make_request = AsyncMock(return_value={"result": "0x0"})

    w3 = AsyncWeb3(mock_provider)
    w3.eth.chain_id = 1
    w3.eth.default_account = "0x" + "0" * 40

    # Mock common Web3 methods
    w3.eth.get_balance = AsyncMock(return_value=1000000000000000000)
    w3.eth.get_transaction_count = AsyncMock(return_value=0)
    w3.eth.get_gas_price = AsyncMock(return_value=20000000000)
    w3.eth.estimate_gas = AsyncMock(return_value=21000)
    w3.eth.send_raw_transaction = AsyncMock(return_value=b'0x1234')
    w3.eth.wait_for_transaction_receipt = AsyncMock(return_value={
        'status': 1,
        'transactionHash': '0x1234',
        'blockNumber': 1000,
        'gasUsed': 21000
    })
    w3.eth.get_transaction = AsyncMock(return_value={
        'hash': '0x1234',
        'blockNumber': 1000,
        'from': '0x' + '0' * 40,
        'to': '0x' + '0' * 40,
        'value': 0
    })

    return w3

class MockProtocolAdapter(BaseProtocolAdapter):
    """Mock protocol adapter for testing."""
    def __init__(self):
        super().__init__()
        logger.debug("Initializing MockProtocolAdapter")
        self.web3 = None
        self.chain_id = None
        self.native_currency = "ETH"
        self.block_time = 15  # Average Ethereum block time
        self._initialized = False
        self._running = False
        self._mock_block_number = 1000
        self._mock_gas_price = 20000000000

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            raise RuntimeError("Adapter not initialized. Call configure_web3 first.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
        return None

    async def configure_web3(self, provider_url: str) -> AsyncWeb3:
        """Configure web3 instance."""
        logger.debug(f"Configuring web3 for provider {provider_url}")

        # Immediately raise ConnectionError for non-mock URLs
        if not provider_url.startswith('mock://'):
            logger.error(f"Connection failed to non-mock URL: {provider_url}")
            raise ConnectionError(f"Failed to connect to provider: {provider_url}")

        class MockProvider(AsyncBaseProvider):
            async def make_request(self_provider, method: str, params: List[Any]) -> Any:
                if method == "eth_chainId":
                    return {"result": hex(1)}  # Default to mainnet chain ID
                elif method == "eth_accounts":
                    return {"result": ["0x" + "0" * 40]}  # Default account
                elif method == "net_version":
                    return {"result": "1"}  # Mainnet
                elif method == "eth_blockNumber":
                    return {"result": hex(self._mock_block_number)}
                elif method == "eth_gasPrice":
                    return {"result": hex(self._mock_gas_price)}
                elif method == "eth_syncing":
                    return {"result": False}
                elif method == "eth_getBalance":
                    return {"result": hex(1000000000000000000)}  # 1 ETH
                elif method == "eth_getTransactionCount":
                    return {"result": hex(1)}
                elif method == "eth_getBlockByNumber":
                    return {
                        "result": {
                            "number": hex(self._mock_block_number),
                            "hash": "0x" + "0" * 64,
                            "parentHash": "0x" + "0" * 64,
                            "timestamp": hex(int(time.time())),
                            "gasLimit": hex(30000000),
                            "gasUsed": hex(21000),
                        }
                    }
                elif method == "eth_getCode":
                    return {"result": "0x"}
                elif method == "eth_call":
                    return {"result": "0x0000000000000000000000000000000000000000000000000000000000000001"}
                else:
                    logger.warning(f"Unhandled method in mock provider: {method}")
                    return {"result": None}

        try:
            provider = MockProvider()
            self.web3 = AsyncWeb3(provider)
            self.web3.eth.default_account = "0x" + "0" * 40
            self._initialized = True
            self._running = True
            return self.web3
        except Exception as e:
            logger.error(f"Failed to configure Web3: {e}")
            raise ConnectionError(f"Failed to connect to provider: {e}")

    async def get_test_web3(self) -> AsyncWeb3:
        """Get a mock Web3 instance for testing."""
        logger.debug("Creating test Web3 instance")
        if not self._initialized:
            await self.configure_web3("mock://localhost:8545")
        return self.web3

    async def connect(self, provider_url: str) -> AsyncWeb3:
        """Connect to provider.

        Args:
            provider_url: Provider URL

        Returns:
            AsyncWeb3: Connected Web3 instance
        """
        logger.debug(f"Connecting to provider {provider_url}")
        self.web3 = await self.configure_web3(provider_url)
        return self.web3

    async def estimate_gas(self, tx_params: TxParams) -> Wei:
        """Mock gas estimation."""
        return Wei(21000)

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Mock transaction receipt."""
        return {
            'status': 1,
            'transactionHash': tx_hash,
            'blockNumber': 1000,
            'gasUsed': 21000
        }

    async def send_transaction(self, tx_params: TxParams) -> str:
        """Mock send transaction."""
        return "0x" + "0" * 64

    async def validate_address(self, address: str) -> bool:
        """Mock address validation."""
        return True

    async def get_balance(self, address: str) -> Wei:
        """Mock get balance."""
        return Wei(1000000000000000000)

    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Mock get block."""
        return {
            'number': block_identifier if isinstance(block_identifier, int) else 1000,
            'timestamp': int(time.time()),
            'hash': "0x" + "0" * 64,
            'parentHash': "0x" + "0" * 64,
        }

    async def get_gas_price(self) -> Wei:
        """Mock get gas price."""
        return Wei(20000000000)

    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        self._running = False
        self.web3 = None

@pytest.fixture
async def base_protocol_adapter(event_loop):
    """Create a base protocol adapter for testing."""
    logger = logging.getLogger(__name__)
    logger.debug("Creating base protocol adapter")

    from genesis_replicator.foundation_services.blockchain_integration.protocols.ethereum import EthereumAdapter
    from web3 import AsyncWeb3, AsyncHTTPProvider
    from web3.types import RPCResponse
    import json

    class MockProvider(AsyncHTTPProvider):
        async def make_request(self, method, params):
            logger.debug(f"Mock provider received request: {method} with params {params}")
            responses = {
                "web3_clientVersion": {"result": "EthereumMock/v0.1.0"},
                "eth_chainId": {"result": "0x1"},  # Chain ID 1
                "eth_gasPrice": {"result": "0x4a817c800"},  # 20 Gwei
                "eth_blockNumber": {"result": "0x1"},
                "eth_getBalance": {"result": "0x0"},
                "eth_getTransactionCount": {"result": "0x0"},
                "eth_estimateGas": {"result": "0x5208"},  # 21000 gas
                "eth_call": {"result": "0x"},
                "eth_sendRawTransaction": {"result": "0x" + "0" * 64},  # Dummy tx hash
            }

            if method in responses:
                return RPCResponse({"id": 0, "jsonrpc": "2.0", **responses[method]})
            logger.warning(f"Unhandled method in mock provider: {method}")
            return RPCResponse({"id": 0, "jsonrpc": "2.0", "result": None})

    adapter = EthereumAdapter()  # Use default chain_id=1
    try:
        logger.debug("Configuring adapter with mock web3")
        web3 = AsyncWeb3()
        web3.provider = MockProvider("http://localhost:8545")
        adapter.web3 = web3
        logger.debug("Adapter configured successfully")
        yield adapter
    except Exception as e:
        logger.error(f"Error configuring protocol adapter: {e}")
        raise
    finally:
        logger.debug("Cleaning up protocol adapter")
        try:
            if hasattr(adapter, 'cleanup'):
                await adapter.cleanup()
        except Exception as e:
            logger.error(f"Error during adapter cleanup: {e}")
            # Don't re-raise cleanup errors to avoid masking the original error

@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def chain_manager(event_loop, base_protocol_adapter):
    """Create a chain manager instance for testing."""
    logger = logging.getLogger(__name__)
    logger.debug("Creating chain manager instance")

    class AsyncChainManagerContext:
        def __init__(self):
            self.manager = None

        async def __aenter__(self):
            logger.debug("Creating chain manager instance")
            self.manager = ChainManager()

            logger.debug("Initializing chain manager")
            try:
                await self.manager.initialize()
                logger.debug("Registering protocol adapter")

                # Get the actual adapter instance by awaiting the fixture
                adapter = await anext(base_protocol_adapter)
                await self.manager.register_protocol_adapter("ethereum", adapter)

                # Configure test chain
                logger.debug("Configuring test chain")
                config = {
                    'test_chain': {
                        'rpc_url': 'mock://localhost:8545',  # Changed to mock:// to match MockProtocolAdapter
                        'chain_id': 1,
                        'protocol': 'ethereum',
                        '_test_mode': True
                    }
                }
                await self.manager.configure(config)

                return self.manager
            except Exception as e:
                logger.error(f"Error in chain manager setup: {str(e)}")
                if self.manager:
                    await self.manager.cleanup()
                raise

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.manager:
                await self.manager.cleanup()

    # Create and return context manager
    return AsyncChainManagerContext()

@pytest.fixture
async def contract_manager(chain_manager, event_loop):
    """Create a contract manager instance for testing."""
    class AsyncContractManagerContext:
        def __init__(self, chain_manager):
            self.chain_manager = chain_manager
            self.manager = None

        async def __aenter__(self):
            chain_ctx = await self.chain_manager
            async with chain_ctx as chain_manager:
                self.manager = ContractManager(chain_manager)
                await self.manager.initialize()
                return self.manager

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.manager:
                await self.manager.cleanup()

    return AsyncContractManagerContext(chain_manager)

@pytest.fixture
async def sync_manager(chain_manager, event_loop):
    """Create a sync manager instance for testing."""
    class AsyncSyncManagerContext:
        def __init__(self, chain_manager):
            self.chain_manager = chain_manager
            self.manager = None

        async def __aenter__(self):
            chain_ctx = await self.chain_manager
            async with chain_ctx as chain_manager:
                self.manager = SyncManager(chain_manager)
                await self.manager.initialize()
                return self.manager

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.manager:
                await self.manager.cleanup()

    return AsyncSyncManagerContext(chain_manager)

@pytest.fixture
async def transaction_manager(chain_manager, event_loop):
    """Create a transaction manager instance for testing."""
    class AsyncTransactionManagerContext:
        def __init__(self, chain_manager):
            self.chain_manager = chain_manager
            self.manager = None

        async def __aenter__(self):
            chain_ctx = await self.chain_manager
            async with chain_ctx as chain_manager:
                self.manager = TransactionManager(chain_manager)
                await self.manager.initialize()
                return self.manager

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.manager:
                await self.manager.cleanup()

    return AsyncTransactionManagerContext(chain_manager)

@pytest.fixture
async def blockchain_system(chain_manager, contract_manager, sync_manager, transaction_manager, event_loop):
    """Create a complete blockchain system for testing."""
    class AsyncBlockchainSystemContext:
        def __init__(self, chain_manager, contract_manager, sync_manager, transaction_manager):
            self.chain_manager = chain_manager
            self.contract_manager = contract_manager
            self.sync_manager = sync_manager
            self.transaction_manager = transaction_manager

        async def __aenter__(self):
            chain_ctx = await self.chain_manager
            contract_ctx = await self.contract_manager
            sync_ctx = await self.sync_manager
            tx_ctx = await self.transaction_manager

            async with chain_ctx as chain_mgr, \
                      contract_ctx as contract_mgr, \
                      sync_ctx as sync_mgr, \
                      tx_ctx as tx_mgr:
                return {
                    'chain_manager': chain_mgr,
                    'contract_manager': contract_mgr,
                    'sync_manager': sync_mgr,
                    'transaction_manager': tx_mgr
                }

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Cleanup is handled by individual manager fixtures
            pass

    return AsyncBlockchainSystemContext(chain_manager, contract_manager, sync_manager, transaction_manager)
