"""
Test BNB Chain protocol adapter.
"""
import pytest
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3
from web3.types import Wei

from genesis_replicator.foundation_services.blockchain_integration.protocols.base import BaseProtocolAdapter
from genesis_replicator.foundation_services.blockchain_integration.protocols.bnb_chain import BNBChainAdapter
from genesis_replicator.foundation_services.blockchain_integration.exceptions import ChainConnectionError

@pytest.fixture
async def bnb_adapter():
    """Create a BNB Chain adapter instance."""
    adapter = BNBChainAdapter()
    await adapter.start()
    return adapter

@pytest.mark.asyncio
async def test_chain_configuration(bnb_adapter):
    """Test BNB Chain configuration."""
    adapter = bnb_adapter
    assert isinstance(adapter, BaseProtocolAdapter)
    assert isinstance(adapter, BNBChainAdapter)

    config = {
        'rpc_url': 'https://bsc-dataseed.binance.org/',
        'chain_id': 56
    }
    await adapter.configure(config)
    assert adapter.chain_id == 56

@pytest.mark.asyncio
async def test_web3_configuration(bnb_adapter):
    """Test Web3 configuration for BNB Chain."""
    adapter = bnb_adapter
    assert isinstance(adapter, BaseProtocolAdapter)
    assert isinstance(adapter, BNBChainAdapter)

    web3 = AsyncMock(spec=AsyncWeb3)
    web3.eth = AsyncMock()
    web3.eth.chain_id = AsyncMock(return_value=56)
    web3.is_connected = AsyncMock(return_value=True)

    await adapter.configure_web3(web3)
    assert adapter._web3 is not None

@pytest.mark.asyncio
async def test_validate_address(bnb_adapter):
    """Test BNB Chain address validation."""
    adapter = bnb_adapter
    assert isinstance(adapter, BaseProtocolAdapter)
    assert isinstance(adapter, BNBChainAdapter)

    # Valid address
    valid_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    assert await adapter.validate_address(valid_address)

    # Invalid address
    invalid_address = "0xinvalid"
    assert not await adapter.validate_address(invalid_address)
