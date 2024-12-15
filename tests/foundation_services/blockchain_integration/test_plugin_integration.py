"""
Plugin system integration tests for blockchain components.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.plugin_system.plugin_manager import PluginManager
from genesis_replicator.plugin_system.plugin_interface import BlockchainPlugin


class TestBlockchainPlugin(BlockchainPlugin):
    """Test plugin implementation."""
    def __init__(self):
        self.name = "test_plugin"
        self.version = "1.0.0"
        self.chain_id = "test_chain"
        self.initialized = False
        self.events = []

    async def initialize(self, context):
        self.initialized = True
        return True

    async def process_block(self, block_data):
        self.events.append(("block", block_data))
        return True

    async def process_transaction(self, tx_data):
        self.events.append(("transaction", tx_data))
        return True

    async def cleanup(self):
        self.events = []
        return True


@pytest.fixture
async def managers():
    """Create manager instances for testing."""
    chain_manager = ChainManager()
    contract_manager = ContractManager()
    plugin_manager = PluginManager()

    await chain_manager.start()
    await plugin_manager.start()

    yield {
        'chain': chain_manager,
        'contract': contract_manager,
        'plugin': plugin_manager
    }

    await chain_manager.stop()
    await plugin_manager.stop()


@pytest.mark.asyncio
async def test_plugin_block_processing(managers):
    """Test plugin integration with block processing."""
    chain_manager = managers['chain']
    plugin_manager = managers['plugin']

    # Create and register test plugin
    test_plugin = TestBlockchainPlugin()
    await plugin_manager.register_plugin(test_plugin)

    # Configure chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1
        }
    }
    await chain_manager.configure(config)

    # Mock block data
    mock_block = {
        "number": 1000,
        "hash": "0x123...",
        "transactions": []
    }

    # Process block through plugin
    with patch.object(chain_manager, '_fetch_block', return_value=mock_block):
        await chain_manager.process_block(test_plugin.chain_id, mock_block)
        await asyncio.sleep(0.1)  # Allow async processing

    # Verify plugin processed the block
    assert len(test_plugin.events) == 1
    assert test_plugin.events[0][0] == "block"
    assert test_plugin.events[0][1] == mock_block


@pytest.mark.asyncio
async def test_plugin_transaction_processing(managers):
    """Test plugin integration with transaction processing."""
    chain_manager = managers['chain']
    plugin_manager = managers['plugin']

    # Create and register test plugin
    test_plugin = TestBlockchainPlugin()
    await plugin_manager.register_plugin(test_plugin)

    # Configure chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1
        }
    }
    await chain_manager.configure(config)

    # Mock transaction
    mock_tx = {
        "hash": "0x456...",
        "from": "0x789...",
        "to": "0xabc...",
        "value": 1000000000000000000
    }

    # Process transaction through plugin
    await chain_manager.process_transaction(test_plugin.chain_id, mock_tx)
    await asyncio.sleep(0.1)  # Allow async processing

    # Verify plugin processed the transaction
    assert len(test_plugin.events) == 1
    assert test_plugin.events[0][0] == "transaction"
    assert test_plugin.events[0][1] == mock_tx


@pytest.mark.asyncio
async def test_plugin_contract_integration(managers):
    """Test plugin integration with contract operations."""
    contract_manager = managers['contract']
    plugin_manager = managers['plugin']

    # Create and register test plugin
    test_plugin = TestBlockchainPlugin()
    await plugin_manager.register_plugin(test_plugin)

    # Mock contract deployment
    contract_address = "0x789..."
    abi = [{"type": "function", "name": "test"}]
    bytecode = "0x123456"

    with patch.object(contract_manager, '_deploy_contract') as mock_deploy:
        mock_deploy.return_value = contract_address

        # Deploy contract through plugin system
        address = await contract_manager.deploy_contract(
            test_plugin.chain_id,
            AsyncMock(spec=AsyncWeb3),
            abi,
            bytecode,
            []
        )

        assert address == contract_address
        mock_deploy.assert_called_once()


@pytest.mark.asyncio
async def test_plugin_lifecycle(managers):
    """Test plugin lifecycle integration."""
    plugin_manager = managers['plugin']

    # Create test plugin
    test_plugin = TestBlockchainPlugin()

    # Test plugin registration
    await plugin_manager.register_plugin(test_plugin)
    assert test_plugin.initialized

    # Test plugin cleanup
    await plugin_manager.unregister_plugin(test_plugin.name)
    assert len(test_plugin.events) == 0


@pytest.mark.asyncio
async def test_plugin_error_handling(managers):
    """Test error handling in plugin integration."""
    chain_manager = managers['chain']
    plugin_manager = managers['plugin']

    # Create plugin that raises an error
    class ErrorPlugin(TestBlockchainPlugin):
        async def process_block(self, block_data):
            raise Exception("Plugin error")

    error_plugin = ErrorPlugin()
    await plugin_manager.register_plugin(error_plugin)

    # Mock block data
    mock_block = {
        "number": 1000,
        "hash": "0x123...",
        "transactions": []
    }

    # Process block and verify error handling
    with patch.object(chain_manager, '_fetch_block', return_value=mock_block):
        # Should not raise exception due to error handling
        await chain_manager.process_block(error_plugin.chain_id, mock_block)
