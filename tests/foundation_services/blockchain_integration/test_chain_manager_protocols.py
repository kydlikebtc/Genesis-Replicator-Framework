"""
Tests for Chain Manager protocol adapter integration.
"""
import pytest
from unittest.mock import Mock, AsyncMock

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.protocols.bnb_chain import BNBChainAdapter
from genesis_replicator.foundation_services.exceptions import ChainConnectionError, TransactionError

@pytest.fixture
async def chain_manager():
    manager = ChainManager()
    await manager.start()
    return manager

@pytest.mark.asyncio
async def test_register_protocol_adapter(chain_manager):
    adapter = BNBChainAdapter()
    await chain_manager.register_protocol_adapter("bnb", adapter)
    assert "bnb" in chain_manager._protocol_adapters

@pytest.mark.asyncio
async def test_connect_with_protocol(chain_manager):
    config = {
        "protocol": "bnb",
        "permissions": {"role": "admin"}
    }
    await chain_manager.connect_to_chain(
        "bnb-mainnet",
        "https://bsc-dataseed.binance.org/",
        **config
    )
    assert "bnb-mainnet" in chain_manager._connections

@pytest.mark.asyncio
async def test_execute_transaction_with_protocol(chain_manager):
    # Setup mock adapter
    mock_adapter = Mock(spec=BNBChainAdapter)
    mock_adapter.send_transaction = AsyncMock(return_value="0xtxhash")
    await chain_manager.register_protocol_adapter("bnb", mock_adapter)

    # Connect chain with protocol
    config = {
        "protocol": "bnb",
        "permissions": {"role": "admin"}
    }
    await chain_manager.connect_to_chain(
        "bnb-mainnet",
        "https://bsc-dataseed.binance.org/",
        **config
    )

    # Execute transaction
    tx = {
        "from": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "to": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "value": 1000000
    }
    tx_hash = await chain_manager.execute_transaction("bnb-mainnet", tx)
    assert tx_hash == "0xtxhash"
    mock_adapter.send_transaction.assert_called_once_with(tx)

@pytest.mark.asyncio
async def test_invalid_protocol(chain_manager):
    config = {
        "protocol": "invalid",
        "permissions": {"role": "admin"}
    }
    with pytest.raises(ChainConnectionError, match="Unsupported protocol"):
        await chain_manager.connect_to_chain(
            "invalid-chain",
            "https://invalid.url",
            **config
        )

@pytest.mark.asyncio
async def test_protocol_transaction_error(chain_manager):
    # Setup mock adapter that raises an error
    mock_adapter = Mock(spec=BNBChainAdapter)
    mock_adapter.send_transaction = AsyncMock(side_effect=Exception("Transaction failed"))
    await chain_manager.register_protocol_adapter("bnb", mock_adapter)

    # Connect chain with protocol
    config = {
        "protocol": "bnb",
        "permissions": {"role": "admin"}
    }
    await chain_manager.connect_to_chain(
        "bnb-mainnet",
        "https://bsc-dataseed.binance.org/",
        **config
    )

    # Execute transaction
    tx = {
        "from": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "to": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "value": 1000000
    }
    with pytest.raises(TransactionError, match="Transaction failed"):
        await chain_manager.execute_transaction("bnb-mainnet", tx)
