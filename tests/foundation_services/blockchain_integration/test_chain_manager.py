"""
Tests for the Chain Manager implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager

@pytest.fixture
async def chain_manager():
    """Create a new ChainManager instance for testing."""
    manager = ChainManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_chain_initialization():
    """Test chain manager initialization."""
    manager = ChainManager()
    await manager.start()

    assert manager.is_running()
    assert manager.get_supported_chains() == ["ethereum"]  # Default chain

    await manager.stop()
    assert not manager.is_running()

@pytest.mark.asyncio
async def test_chain_connection():
    """Test connecting to blockchain network."""
    manager = ChainManager()
    await manager.start()

    # Test connection to Ethereum network
    connected = await manager.connect_chain("ethereum")
    assert connected
    assert manager.is_connected("ethereum")

    # Test connection to unsupported chain
    with pytest.raises(ValueError):
        await manager.connect_chain("unsupported_chain")

    await manager.stop()

@pytest.mark.asyncio
async def test_block_sync():
    """Test block synchronization."""
    manager = ChainManager()
    await manager.start()
    await manager.connect_chain("ethereum")

    # Mock block data
    mock_block = {
        "number": 1000,
        "hash": "0x123...",
        "transactions": []
    }

    with patch.object(manager, '_fetch_block', return_value=mock_block):
        block = await manager.get_block(1000)
        assert block["number"] == 1000
        assert block["hash"] == "0x123..."

    await manager.stop()

@pytest.mark.asyncio
async def test_transaction_monitoring():
    """Test transaction monitoring functionality."""
    manager = ChainManager()
    await manager.start()
    await manager.connect_chain("ethereum")

    transactions = []
    async def transaction_callback(tx):
        transactions.append(tx)

    # Register transaction monitor
    await manager.monitor_transactions(transaction_callback)

    # Simulate incoming transaction
    mock_tx = {
        "hash": "0x456...",
        "from": "0x789...",
        "to": "0xabc...",
        "value": 1000000000000000000
    }

    # Trigger mock transaction event
    await manager._process_transaction(mock_tx)
    await asyncio.sleep(0.1)  # Allow async processing

    assert len(transactions) == 1
    assert transactions[0]["hash"] == "0x456..."

    await manager.stop()

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling during chain operations."""
    manager = ChainManager()
    await manager.start()

    # Test handling of connection error
    with patch.object(manager, '_establish_connection', side_effect=Exception("Connection failed")):
        with pytest.raises(Exception) as exc_info:
            await manager.connect_chain("ethereum")
        assert str(exc_info.value) == "Connection failed"

    await manager.stop()

@pytest.mark.asyncio
async def test_chain_configuration():
    """Test chain configuration management."""
    manager = ChainManager()

    # Test configuration loading
    config = {
        "ethereum": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1,
            "sync_interval": 15
        }
    }

    await manager.configure(config)
    assert manager.get_chain_config("ethereum")["chain_id"] == 1
    assert manager.get_chain_config("ethereum")["sync_interval"] == 15

    # Test invalid configuration
    with pytest.raises(ValueError):
        await manager.configure({"invalid_chain": {}})

@pytest.mark.asyncio
async def test_multi_chain_support():
    """Test support for multiple chains."""
    manager = ChainManager()
    await manager.start()

    # Configure multiple chains
    config = {
        "ethereum": {"chain_id": 1},
        "polygon": {"chain_id": 137}
    }

    await manager.configure(config)
    chains = manager.get_supported_chains()

    assert "ethereum" in chains
    assert "polygon" in chains
    assert len(chains) == 2

    await manager.stop()
