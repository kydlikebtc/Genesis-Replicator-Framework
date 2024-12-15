"""
Global test configuration and fixtures for blockchain integration tests.
"""
import pytest
import asyncio
import inspect
import logging
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from web3 import AsyncWeb3, Web3
from web3.providers import AsyncHTTPProvider
from web3.contract import AsyncContract

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager
from genesis_replicator.foundation_services.blockchain_integration.transaction_manager import TransactionManager

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
    if classinfo in (AsyncWeb3, Web3):
        # Check if object has the necessary Web3 attributes and is a mock
        if asyncio.iscoroutine(obj):
            return False
        if original_isinstance(obj, (AsyncMock, Mock, MagicMock)):
            return hasattr(obj, 'eth') and hasattr(obj, 'provider')
        return original_isinstance(obj, classinfo)

    # Handle mock objects
    if original_isinstance(obj, (AsyncMock, Mock, MagicMock)) and hasattr(classinfo, '__name__'):
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
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)

@pytest.fixture
async def base_web3_mock():
    """Create a base Web3 mock instance that other fixtures can build upon."""
    mock = AsyncMock(spec=AsyncWeb3)
    mock.eth = AsyncMock()
    mock.eth.chain_id = 1
    mock.eth.get_block_number = AsyncMock(return_value=1000)
    mock.eth.get_balance = AsyncMock(return_value=1000000)
    mock.eth.get_transaction_count = AsyncMock(return_value=10)
    mock.eth.get_code = AsyncMock(return_value="0x123456")
    mock.eth.get_transaction_receipt = AsyncMock(return_value={
        'status': 1,
        'transactionHash': '0x1234',
        'blockNumber': 1000,
        'gasUsed': 21000
    })
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'timestamp': 1234567890,
        'hash': '0x1234',
        'transactions': []
    })

    # Configure Web3 instance methods
    mock.is_connected = AsyncMock(return_value=True)
    mock.provider = AsyncMock(spec=AsyncHTTPProvider)
    mock.provider.is_connected = AsyncMock(return_value=True)

    # Add contract-related mocks
    contract_mock = AsyncMock(spec=AsyncContract)
    contract_mock.functions = AsyncMock()
    contract_mock.events = AsyncMock()
    mock.eth.contract = AsyncMock(return_value=contract_mock)

    return mock

@pytest.fixture
async def base_protocol_adapter(base_web3_mock):
    """Create a base protocol adapter mock that other fixtures can build upon."""
    adapter = AsyncMock()
    adapter.web3 = await base_web3_mock
    adapter.configure_web3 = AsyncMock()
    adapter.validate_connection = AsyncMock(return_value=True)
    adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    adapter.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    adapter.get_contract = AsyncMock(return_value=(await base_web3_mock).eth.contract())
    adapter.deploy_contract = AsyncMock(return_value={
        'address': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'abi': [],
        'bytecode': '0x'
    })
    return adapter

@pytest.fixture
async def chain_manager(base_protocol_adapter):
    """Create a chain manager instance."""
    logger.debug("Creating chain manager instance")
    manager = ChainManager()
    await manager.initialize()

    # Register ethereum protocol adapter
    logger.debug("Registering ethereum protocol adapter")
    await manager.register_protocol_adapter('ethereum', await base_protocol_adapter)

    # Configure with test chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1,
            "protocol": "ethereum"
        }
    }

    logger.debug("Configuring chain manager with test chain")
    await manager.configure(config)
    logger.debug("Chain manager configured successfully")

    yield manager

    # Cleanup
    logger.debug("Cleaning up chain manager")
    await manager.cleanup()
    logger.debug("Chain manager cleanup complete")

@pytest.fixture
async def contract_manager(chain_manager):
    """Create a contract manager instance."""
    logger.debug("Creating contract manager instance")
    manager = ContractManager(await chain_manager)
    await manager.initialize()
    yield manager
    await manager.cleanup()

@pytest.fixture
async def sync_manager(chain_manager):
    """Create a sync manager instance."""
    logger.debug("Creating sync manager instance")
    manager = SyncManager(await chain_manager)
    await manager.initialize()
    yield manager
    await manager.cleanup()

@pytest.fixture
async def transaction_manager(chain_manager):
    """Create a transaction manager instance."""
    logger.debug("Creating transaction manager instance")
    manager = TransactionManager(await chain_manager)
    await manager.initialize()
    yield manager
    await manager.cleanup()

@pytest.fixture
async def blockchain_system(chain_manager, contract_manager, sync_manager, transaction_manager):
    """Create a complete blockchain system with all managers."""
    system = {
        'chain_manager': await chain_manager,
        'contract_manager': await contract_manager,
        'sync_manager': await sync_manager,
        'transaction_manager': await transaction_manager
    }
    yield system
