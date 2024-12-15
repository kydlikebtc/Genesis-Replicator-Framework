"""
Tests for BNB Chain protocol adapter.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from web3 import Web3, AsyncWeb3
from web3.types import Wei
from web3.providers import AsyncHTTPProvider

from genesis_replicator.foundation_services.blockchain_integration.protocols.bnb_chain import (
    BNBChainAdapter,
)
from genesis_replicator.foundation_services.blockchain_integration.exceptions import ChainConnectionError

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
    mock.eth.chain_id = AsyncMock(return_value=56)  # BNB Chain mainnet
    mock.eth.get_balance = AsyncMock(return_value=Wei(1000000))
    mock.eth.gas_price = AsyncMock(return_value=Wei(5000000000))
    mock.eth.estimate_gas = AsyncMock(return_value=Wei(21000))
    mock.eth.get_transaction_receipt = AsyncMock(return_value={
        'status': 1,
        'transactionHash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        'blockNumber': 1000,
        'gasUsed': 21000
    })
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        'timestamp': 1234567890
    })
    mock.eth.send_transaction = AsyncMock(
        return_value='0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    )
    mock.eth.contract = MagicMock()
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = MagicMock(side_effect=lambda addr: len(addr) == 42 and addr.startswith('0x'))
    return mock

@pytest.fixture
async def bnb_adapter(event_loop):
    """Create a BNB Chain adapter instance."""
    adapter = BNBChainAdapter()
    mock = MagicMock()
    mock.eth = MagicMock()
    mock.eth.chain_id = AsyncMock(return_value=56)
    mock.is_connected = AsyncMock(return_value=True)

    with patch.object(AsyncWeb3, '__new__', return_value=mock):
        await adapter.configure_web3('http://localhost:8545')
        yield adapter
        await adapter.close()

@pytest.mark.asyncio
async def test_chain_configuration(bnb_adapter, web3_mock):
    """Test chain configuration."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        await bnb_adapter.configure_web3('http://localhost:8545')
        assert await bnb_adapter.web3.eth.chain_id == 56
        assert bnb_adapter.native_currency == "BNB"
        assert bnb_adapter.block_time == 3

@pytest.mark.asyncio
async def test_web3_configuration(bnb_adapter, web3_mock):
    """Test Web3 configuration."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        await bnb_adapter.configure_web3('http://localhost:8545')
        assert bnb_adapter.web3 is not None
        chain_id = await bnb_adapter.web3.eth.chain_id
        assert chain_id == 56

@pytest.mark.asyncio
async def test_validate_address(bnb_adapter, web3_mock):
    """Test address validation."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        valid_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        invalid_address = "0xinvalid"

        assert await bnb_adapter.validate_address(valid_address)
        assert not await bnb_adapter.validate_address(invalid_address)

@pytest.mark.asyncio
async def test_get_gas_price(bnb_adapter, web3_mock):
    """Test gas price retrieval."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        gas_price = await bnb_adapter.get_gas_price()
        assert isinstance(gas_price, Wei)
        assert gas_price == 5000000000

@pytest.mark.asyncio
async def test_get_block(bnb_adapter, web3_mock):
    """Test block retrieval."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        block = await bnb_adapter.get_block('latest')
        assert isinstance(block, dict)
        assert block['number'] == 1000
        assert block['hash'].startswith('0x')
        assert block['timestamp'] == 1234567890

@pytest.mark.asyncio
async def test_estimate_gas(bnb_adapter, web3_mock):
    """Test gas estimation."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        tx_params = {
            'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
            'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
            'value': Wei(100000),
        }
        gas = await bnb_adapter.estimate_gas(tx_params)
        assert isinstance(gas, Wei)
        assert gas == 21000

@pytest.mark.asyncio
async def test_send_transaction_validation(bnb_adapter, web3_mock):
    """Test transaction validation."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        tx_params = {
            'gas': Wei(31_000_000),  # Exceeds max gas limit
            'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
            'value': Wei(100000),
        }
        with pytest.raises(ValueError, match="Gas limit exceeds maximum allowed"):
            await bnb_adapter.send_transaction(tx_params)

@pytest.mark.asyncio
async def test_get_balance_validation(bnb_adapter, web3_mock):
    """Test balance validation."""
    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        invalid_address = "0xinvalid"
        with pytest.raises(ValueError, match="Invalid address"):
            await bnb_adapter.get_balance(invalid_address)

@pytest.mark.asyncio
async def test_chain_connection_error():
    """Test chain connection error handling."""
    adapter = BNBChainAdapter()
    mock = AsyncMock()
    mock.is_connected = AsyncMock(return_value=False)
    with patch.object(AsyncWeb3, '__new__', return_value=mock):
        with pytest.raises(ChainConnectionError):
            await adapter.configure_web3('http://invalid:8545')
