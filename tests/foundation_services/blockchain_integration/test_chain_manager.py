"""
Tests for the blockchain chain manager.
"""
import logging
import pytest

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.exceptions import (
    ChainConfigError,
    ChainConnectionError,
)
from genesis_replicator.foundation_services.blockchain_integration.protocols.ethereum import (
    EthereumAdapter,
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug logging for test execution
logger.debug("Loading test_chain_manager module")

@pytest.mark.asyncio
async def test_chain_initialization(chain_manager):
    """Test successful chain manager initialization."""
    logger.debug("Starting test_chain_initialization")
    try:
        ctx = await chain_manager
        async with ctx as manager:
            assert manager._initialized
            assert manager._running
            logger.debug("Chain manager initialization verified")
    except Exception as e:
        logger.error(f"test_chain_initialization failed: {e}")
        raise

@pytest.mark.asyncio
async def test_invalid_chain_config():
    """Test handling of invalid chain configuration."""
    logger.debug("Starting test_invalid_chain_config")

    async def run_test_case(config, error_msg, test_name):
        manager = None
        try:
            manager = ChainManager()
            await manager.initialize()

            # Register ethereum protocol adapter
            adapter = EthereumAdapter()
            await manager.register_protocol_adapter('ethereum', adapter)

            # Run the test
            await manager.configure(config)
            pytest.fail(f"Expected ChainConfigError in {test_name}")
        except ChainConfigError as e:
            assert str(e) == error_msg
            logger.debug(f"{test_name} passed")
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}")
            raise
        finally:
            if manager:
                try:
                    await manager.cleanup()
                except Exception as e:
                    logger.error(f"Error during cleanup in {test_name}: {e}")

    # Test missing RPC URL
    config_missing_rpc = {
        'test_chain': {
            'chain_id': 1,
            'protocol': 'ethereum'
        }
    }
    await run_test_case(
        config_missing_rpc,
        "missing required field: rpc_url",
        "missing RPC URL test"
    )

    # Test invalid chain ID
    config_invalid_chain_id = {
        'test_chain': {
            'rpc_url': 'http://localhost:8545',
            'chain_id': -1,
            'protocol': 'ethereum'
        }
    }
    await run_test_case(
        config_invalid_chain_id,
        "invalid chain ID: must be positive integer",
        "invalid chain ID test"
    )

    # Test unsupported protocol
    config_unsupported_protocol = {
        'test_chain': {
            'rpc_url': 'http://localhost:8545',
            'chain_id': 1,
            'protocol': 'unsupported'
        }
    }
    await run_test_case(
        config_unsupported_protocol,
        "unsupported protocol: unsupported",
        "unsupported protocol test"
    )

@pytest.mark.asyncio
async def test_connection_error():
    """Test handling of connection errors."""
    logger.debug("Starting test_connection_error")
    manager = None
    try:
        manager = ChainManager()
        await manager.initialize()
        # Register ethereum protocol adapter
        adapter = EthereumAdapter()
        await manager.register_protocol_adapter('ethereum', adapter)

        config = {
            'test_chain': {
                'rpc_url': 'http://nonexistent:8545',
                'chain_id': 1,
                'protocol': 'ethereum'
            }
        }
        # Configure should succeed but connection should fail
        await manager.configure(config)

        # Attempt to connect should return False
        success = await manager.connect_chain('test_chain')
        assert not success, "Expected connection to fail with nonexistent URL"
        logger.debug("Connection error test passed")
    except Exception as e:
        logger.error(f"Unexpected error in connection error test: {e}")
        raise
    finally:
        if manager:
            try:
                await manager.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup in connection error test: {e}")

@pytest.mark.asyncio
async def test_double_initialization():
    """Test double initialization handling."""
    logger.debug("Starting test_double_initialization")
    manager = None
    try:
        # Create and initialize first instance
        manager = ChainManager()
        await manager.initialize()
        assert manager._initialized
        assert manager._running

        await manager.initialize()
        pytest.fail("Expected ChainConfigError for double initialization")
    except ChainConfigError as e:
        assert str(e) == "already initialized"
        logger.debug("Double initialization test passed")
    except Exception as e:
        logger.error(f"Unexpected error in double initialization test: {e}")
        raise
    finally:
        if manager:
            try:
                await manager.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup in double initialization test: {e}")

@pytest.mark.asyncio
async def test_configure_without_init():
    """Test configuration without initialization."""
    logger.debug("Starting test_configure_without_init")
    manager = None
    try:
        manager = ChainManager()  # Explicitly not initialized
        config = {
            'test_chain': {
                'rpc_url': 'http://localhost:8545',
                'chain_id': 1,
                'protocol': 'ethereum'
            }
        }
        await manager.configure(config)
        pytest.fail("Expected ChainConfigError for uninitialized manager")
    except ChainConfigError as e:
        assert str(e) == "not initialized"
        logger.debug("Configure without init test passed")
    except Exception as e:
        logger.error(f"Unexpected error in configure without init test: {e}")
        raise
    finally:
        if manager:
            try:
                await manager.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup in configure without init test: {e}")
