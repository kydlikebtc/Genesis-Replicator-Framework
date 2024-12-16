"""
Tests for blockchain monitoring functionality.
"""
import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.monitoring.metrics_collector import MetricsCollector
from genesis_replicator.monitoring.health_checker import HealthChecker
from genesis_replicator.monitoring.alert_manager import AlertManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    logger.debug("Setting up event loop")
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    logger.debug("Cleaning up event loop")
    loop.close()
    asyncio.set_event_loop(None)

@pytest.fixture
def web3_mock():
    """Create a mock Web3 instance."""
    mock = MagicMock(spec=AsyncWeb3)
    mock.eth = MagicMock()
    mock.eth.chain_id = AsyncMock(return_value=1)
    mock.eth.get_balance = AsyncMock(return_value=1000000)
    mock.eth.gas_price = AsyncMock(return_value=20000000000)
    mock.eth.estimate_gas = AsyncMock(return_value=21000)
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'hash': '0x123...',
        'transactions': [{'hash': '0x456...'} for _ in range(10)]
    })
    mock.eth.send_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    mock.eth.contract = MagicMock()
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = AsyncMock(return_value=True)

    # Mock provider
    mock_provider = MagicMock()
    mock_provider.is_connected = AsyncMock(return_value=True)
    mock.provider = mock_provider

    return mock

@pytest.fixture
async def monitoring_system():
    """Create monitoring system components."""
    class AsyncMonitoringSystemContext:
        def __init__(self):
            self.metrics = None
            self.health = None
            self.alerts = None

        async def __aenter__(self):
            self.metrics = MetricsCollector()
            self.health = HealthChecker()
            self.alerts = AlertManager()

            await self.metrics.start()
            await self.health.start()
            await self.alerts.start()

            return {
                'metrics': self.metrics,
                'health': self.health,
                'alerts': self.alerts
            }

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.metrics:
                await self.metrics.stop()
            if self.health:
                await self.health.stop()
            if self.alerts:
                await self.alerts.stop()

    return AsyncMonitoringSystemContext()

@pytest.fixture
async def blockchain_system(web3_mock):
    """Create blockchain system components."""
    logger.debug("Setting up blockchain system")

    class AsyncBlockchainSystemContext:
        def __init__(self, web3_mock):
            self.web3_mock = web3_mock
            self.chain_manager = None
            self.contract_manager = None

        async def __aenter__(self):
            logger.debug("Starting blockchain system components")
            self.chain_manager = ChainManager()
            self.contract_manager = ContractManager(self.chain_manager)

            logger.debug("Starting chain manager")
            await self.chain_manager.start()
            logger.debug("Starting contract manager")
            await self.contract_manager.start()

            # Configure chain
            config = {
                "test_chain": {
                    "rpc_url": "http://localhost:8545",
                    "chain_id": 1
                }
            }

            # Create mock protocol adapter
            mock_adapter = MagicMock()
            mock_adapter.web3 = self.web3_mock
            mock_adapter.configure_web3 = AsyncMock(return_value=None)
            mock_adapter.validate_connection = AsyncMock(return_value=True)
            mock_adapter.execute_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
            mock_adapter.get_transaction_receipt = AsyncMock(return_value={'status': 1})
            mock_adapter.get_contract = MagicMock(return_value=self.web3_mock.eth.contract())

            # Register protocol adapter
            await self.chain_manager.register_protocol_adapter("ethereum", mock_adapter)

            with patch.object(AsyncWeb3, '__new__', return_value=self.web3_mock):
                await self.chain_manager.configure(config)
                await self.chain_manager.connect_chain("test_chain")

            return {
                'chain': self.chain_manager,
                'contract': self.contract_manager,
                'web3': self.web3_mock
            }

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            logger.debug("Cleaning up blockchain system")
            if self.contract_manager:
                await self.contract_manager.stop()
            if self.chain_manager:
                await self.chain_manager.stop()

    return AsyncBlockchainSystemContext(web3_mock)

@pytest.mark.asyncio
async def test_chain_metrics_collection(monitoring_system, blockchain_system):
    """Test chain metrics collection."""
    logger.debug("Starting chain metrics collection test")

    monitoring_ctx = await monitoring_system
    blockchain_ctx = await blockchain_system

    async with monitoring_ctx as monitoring, blockchain_ctx as blockchain:
        metrics = monitoring['metrics']
        chain_manager = blockchain['chain']

        # Start metrics collection
        await metrics.start_chain_metrics(chain_manager)
        await asyncio.sleep(0.1)  # Allow metrics collection

        # Verify metrics
        chain_metrics = await metrics.get_chain_metrics("test_chain")
        assert chain_metrics is not None
        assert 'block_height' in chain_metrics
        assert 'transaction_count' in chain_metrics
        assert 'gas_price' in chain_metrics

        # Stop metrics collection
        await metrics.stop_chain_metrics("test_chain")

@pytest.mark.asyncio
async def test_contract_metrics_collection(monitoring_system, blockchain_system):
    """Test contract metrics collection."""
    logger.debug("Starting contract metrics collection test")

    monitoring_ctx = await monitoring_system
    blockchain_ctx = await blockchain_system

    async with monitoring_ctx as monitoring, blockchain_ctx as blockchain:
        metrics = monitoring['metrics']
        contract_manager = blockchain['contract']

        # Deploy test contract
        contract_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]

        await contract_manager.register_contract(
            "test_contract",
            contract_address,
            contract_abi,
            chain_id="test_chain"
        )

        # Start metrics collection
        await metrics.start_contract_metrics(contract_manager, contract_address)
        await asyncio.sleep(0.1)  # Allow metrics collection

        # Verify metrics
        contract_metrics = await metrics.get_contract_metrics(contract_address)
        assert contract_metrics is not None
        assert 'method_calls' in contract_metrics
        assert 'gas_used' in contract_metrics

        # Stop metrics collection
        await metrics.stop_contract_metrics(contract_address)

@pytest.mark.asyncio
async def test_health_checking(monitoring_system, blockchain_system):
    """Test blockchain component health checking."""
    logger.debug("Starting health checking test")

    monitoring_ctx = await monitoring_system
    blockchain_ctx = await blockchain_system

    async with monitoring_ctx as monitoring, blockchain_ctx as blockchain:
        health = monitoring['health']
        chain_manager = blockchain['chain']

        try:
            async with asyncio.timeout(5.0):  # Add timeout to prevent hanging
                # Check chain health
                health_status = await health.check_chain_health("test_chain")
                assert health_status['status'] == 'healthy'
                assert 'last_check' in health_status
                assert 'response_time' in health_status

        except asyncio.TimeoutError:
            logger.error("Test timed out")
            raise
        finally:
            logger.debug("Cleaning up health checking test")

@pytest.mark.asyncio
async def test_alert_generation(monitoring_system, blockchain_system):
    """Test alert generation functionality."""
    logger.debug("Starting alert generation test")

    monitoring_ctx = await monitoring_system
    blockchain_ctx = await blockchain_system

    alerts_received = []

    async def alert_handler(alert):
        alerts_received.append(alert)

    async with monitoring_ctx as monitoring, blockchain_ctx as blockchain:
        alerts = monitoring['alerts']
        chain_manager = blockchain['chain']

        # Register alert handler
        await alerts.register_handler(alert_handler)

        # Trigger test alert conditions
        await alerts.set_chain_alert_threshold(
            "test_chain",
            "block_time",
            threshold=15  # seconds
        )

        # Simulate slow block time
        chain_manager._last_block_time = asyncio.get_event_loop().time() - 20

        # Wait for alert generation
        await asyncio.sleep(0.1)

        # Verify alerts
        assert len(alerts_received) > 0
        alert = alerts_received[0]
        assert alert['chain_id'] == "test_chain"
        assert alert['type'] == "block_time_exceeded"
        assert alert['severity'] == "warning"

        # Cleanup
        await alerts.unregister_handler(alert_handler)

@pytest.mark.asyncio
async def test_performance_monitoring(monitoring_system, blockchain_system):
    """Test performance monitoring functionality."""
    logger.debug("Starting performance monitoring test")

    monitoring_ctx = await monitoring_system
    blockchain_ctx = await blockchain_system

    async with monitoring_ctx as monitoring, blockchain_ctx as blockchain:
        metrics = monitoring['metrics']
        chain_manager = blockchain['chain']

        # Start performance monitoring
        await metrics.start_performance_monitoring(chain_manager)
        await asyncio.sleep(0.1)  # Allow monitoring

        # Simulate some transactions
        for _ in range(5):
            await chain_manager.execute_transaction(
                "test_chain",
                {
                    'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
                    'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
                    'value': 1000
                }
            )

        # Get performance metrics
        perf_metrics = await metrics.get_performance_metrics("test_chain")
        assert perf_metrics is not None
        assert 'transaction_latency' in perf_metrics
        assert 'throughput' in perf_metrics

        # Stop performance monitoring
        await metrics.stop_performance_monitoring("test_chain")

@pytest.mark.asyncio
async def test_resource_monitoring(monitoring_system, blockchain_system):
    """Test resource monitoring functionality."""
    logger.debug("Starting resource monitoring test")

    monitoring_ctx = await monitoring_system
    blockchain_ctx = await blockchain_system

    async with monitoring_ctx as monitoring, blockchain_ctx as blockchain:
        metrics = monitoring['metrics']
        chain_manager = blockchain['chain']

        # Start resource monitoring
        await metrics.start_resource_monitoring(chain_manager)
        await asyncio.sleep(0.1)  # Allow monitoring

        # Get resource metrics
        resource_metrics = await metrics.get_resource_metrics("test_chain")
        assert resource_metrics is not None
        assert 'memory_usage' in resource_metrics
        assert 'cpu_usage' in resource_metrics

        # Stop resource monitoring
        await metrics.stop_resource_monitoring("test_chain")
