"""
Tests for the Ethereum protocol adapter.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from web3 import Web3, AsyncWeb3
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.blockchain_integration.protocols.ethereum import EthereumAdapter
from genesis_replicator.foundation_services.blockchain_integration.exceptions import ChainConnectionError, ConfigurationError

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
    mock.eth.get_transaction_receipt = AsyncMock(return_value={
        'status': 1,
        'transactionHash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        'blockNumber': 1000,
        'gasUsed': 21000
    })
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'timestamp': 1234567890,
        'hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    })
    mock.eth.send_transaction = AsyncMock(
        return_value='0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    )
    mock.eth.contract = MagicMock()
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = MagicMock(return_value=True)
    return mock

@pytest.fixture
async def ethereum_adapter(event_loop):
    """Create an Ethereum adapter instance."""
    adapter = EthereumAdapter()
    mock = MagicMock()
    mock.eth = MagicMock()
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.is_connected = AsyncMock(return_value=True)

    with patch.object(AsyncWeb3, '__new__', return_value=mock):
        await adapter.configure_web3('http://localhost:8545')
        yield adapter
        await adapter.close()

@pytest.mark.asyncio
async def test_web3_configuration(ethereum_adapter, web3_mock):
    """Test Web3 configuration."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        await ethereum_adapter.configure_web3('http://localhost:8545')
        assert ethereum_adapter.web3 is not None
        assert await ethereum_adapter.web3.eth.chain_id == 1

@pytest.mark.asyncio
async def test_validate_address(ethereum_adapter, web3_mock):
    """Test address validation."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        valid = await ethereum_adapter.validate_address('0x742d35Cc6634C0532925a3b844Bc454e4438f44e')
        assert valid is True

@pytest.mark.asyncio
async def test_get_balance(ethereum_adapter, web3_mock):
    """Test balance retrieval."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        balance = await ethereum_adapter.get_balance('0x742d35Cc6634C0532925a3b844Bc454e4438f44e')
        assert balance == 1000000

@pytest.mark.asyncio
async def test_get_gas_price(ethereum_adapter, web3_mock):
    """Test gas price retrieval."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        gas_price = await ethereum_adapter.get_gas_price()
        assert gas_price == 20000000000

@pytest.mark.asyncio
async def test_estimate_gas(ethereum_adapter, web3_mock):
    """Test gas estimation."""
    tx = {
        'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'value': 1000000
    }
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        gas = await ethereum_adapter.estimate_gas(tx)
        assert gas == 21000

@pytest.mark.asyncio
async def test_send_transaction(ethereum_adapter, web3_mock):
    """Test transaction sending."""
    tx = {
        'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'value': 1000000
    }
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        tx_hash = await ethereum_adapter.send_transaction(tx)
        assert tx_hash.startswith('0x')
        assert len(tx_hash) == 66  # Standard Ethereum transaction hash length

@pytest.mark.asyncio
async def test_get_transaction_receipt(ethereum_adapter, web3_mock):
    """Test transaction receipt retrieval."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        receipt = await ethereum_adapter.get_transaction_receipt(
            '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
        )
        assert receipt['status'] == 1
        assert receipt['transactionHash'].startswith('0x')
        assert receipt['blockNumber'] == 1000

@pytest.mark.asyncio
async def test_get_block(ethereum_adapter, web3_mock):
    """Test block retrieval."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        block = await ethereum_adapter.get_block(1000)
        assert block['number'] == 1000
        assert block['hash'].startswith('0x')
        assert 'timestamp' in block

@pytest.mark.asyncio
async def test_configuration_error():
    """Test configuration error handling."""
    adapter = EthereumAdapter()
    with pytest.raises(ConfigurationError):
        await adapter.configure_web3('')

@pytest.mark.asyncio
async def test_chain_connection_error():
    """Test chain connection error handling."""
    adapter = EthereumAdapter()
    mock = AsyncMock()
    mock.is_connected = AsyncMock(return_value=False)
    with patch.object(AsyncWeb3, '__new__', return_value=mock):
        with pytest.raises(ChainConnectionError):
            await adapter.configure_web3('http://localhost:8545')
