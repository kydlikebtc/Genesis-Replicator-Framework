"""
Monitoring system validation tests for blockchain components.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3

from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.monitoring.metrics_collector import MetricsCollector
from genesis_replicator.monitoring.health_checker import HealthChecker
from genesis_replicator.monitoring.alert_manager import AlertManager

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
    mock.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_block = AsyncMock(return_value={
        'number': 1000,
        'hash': '0x123...',
        'transactions': [{'hash': '0x456...'} for _ in range(10)]
    })
    mock.eth.send_transaction = AsyncMock(return_value=bytes.fromhex('1234'))
    mock.eth.contract = MagicMock()
    mock.is_connected = AsyncMock(return_value=True)
    mock.is_address = MagicMock(return_value=True)
    return mock

@pytest.fixture
async def monitoring_system(event_loop):
    """Create monitoring system components."""
    metrics = MetricsCollector()
    health = HealthChecker()
    alerts = AlertManager()

    await metrics.start()
    await health.start()
    await alerts.start()

    try:
        yield {
            'metrics': metrics,
            'health': health,
            'alerts': alerts
        }
    finally:
        await metrics.stop()
        await health.stop()
        await alerts.stop()

@pytest.fixture
async def blockchain_system(event_loop, web3_mock):
    """Create blockchain system components."""
    chain_manager = ChainManager()
    contract_manager = ContractManager()

    await chain_manager.start()
    await contract_manager.start()

    # Configure chain
    config = {
        "test_chain": {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1
        }
    }

    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        await chain_manager.configure(config)
        await chain_manager.connect_chain("test_chain")
        try:
            yield {
                'chain': chain_manager,
                'contract': contract_manager,
                'web3': web3_mock
            }
        finally:
            await contract_manager.stop()
            await chain_manager.stop()

@pytest.mark.asyncio
async def test_chain_metrics_collection(monitoring_system, blockchain_system):
    """Test collection of chain metrics."""
    metrics = monitoring_system['metrics']
    chain_manager = blockchain_system['chain']
    web3_mock = blockchain_system['web3']

    # Process block and collect metrics
    mock_block = {
        "number": 1000,
        "hash": "0x123...",
        "transactions": [{"hash": "0x456..."} for _ in range(10)]
    }

    with patch.object(chain_manager, '_fetch_block', return_value=mock_block):
        await chain_manager.process_block("test_chain", mock_block)
        await asyncio.sleep(0.1)  # Allow metric collection

        # Verify metrics
        chain_metrics = await metrics.get_chain_metrics("test_chain")
        assert chain_metrics['blocks_processed'] > 0
        assert chain_metrics['transactions_processed'] >= 10
        assert chain_metrics['last_block_number'] == 1000

@pytest.mark.asyncio
async def test_contract_metrics_collection(monitoring_system, blockchain_system):
    """Test collection of contract metrics."""
    metrics = monitoring_system['metrics']
    contract_manager = blockchain_system['contract']
    web3_mock = blockchain_system['web3']

    # Mock contract deployment
    contract_address = "0x123456"
    contract_abi = [{"type": "function", "name": "test"}]
    contract_bytecode = "0x123456"

    mock_contract = AsyncMock()
    mock_contract.functions.constructor().transact = AsyncMock(return_value=bytes.fromhex('123456'))
    web3_mock.eth.contract.return_value = mock_contract

    with patch.object(AsyncWeb3, '__new__', return_value=web3_mock):
        await contract_manager.deploy_contract(
            "test_contract",
            contract_abi,
            contract_bytecode,
            chain_id="test_chain"
        )
        await asyncio.sleep(0.1)  # Allow metric collection

        # Verify metrics
        contract_metrics = await metrics.get_contract_metrics(contract_address)
        assert contract_metrics['deployments'] > 0
        assert contract_metrics['method_calls'] == 0

@pytest.mark.asyncio
async def test_health_checking(monitoring_system, blockchain_system):
    """Test blockchain component health checking."""
    health = monitoring_system['health']
    chain_manager = blockchain_system['chain']

    # Check chain health
    health_status = await health.check_chain_health("test_chain")
    assert health_status['status'] == 'healthy'
    assert 'last_check' in health_status
    assert 'response_time' in health_status

@pytest.mark.asyncio
async def test_alert_generation(monitoring_system, blockchain_system):
    """Test alert generation for blockchain events."""
    alerts = monitoring_system['alerts']
    chain_manager = blockchain_system['chain']

    # Configure alert handler
    alerts_received = []
    async def alert_handler(alert):
        alerts_received.append(alert)

    await alerts.register_handler(alert_handler)

    # Simulate chain disconnection
    await chain_manager.configure({
        "test_chain": {
            "rpc_url": "invalid_url",
            "chain_id": 1
        }
    })

    # Try connecting to trigger alert
    try:
        await chain_manager.connect_chain("test_chain")
    except:
        pass

    await asyncio.sleep(0.1)  # Allow alert processing

    # Verify alert generation
    assert len(alerts_received) > 0
    assert any(alert['type'] == 'chain_connection_error' for alert in alerts_received)

@pytest.mark.asyncio
async def test_performance_monitoring(monitoring_system, blockchain_system):
    """Test monitoring of blockchain component performance."""
    metrics = monitoring_system['metrics']
    chain_manager = blockchain_system['chain']

    # Mock block processing with timing
    mock_block = {
        "number": 1000,
        "hash": "0x123...",
        "transactions": [{"hash": f"0x{i}..."} for i in range(100)]
    }

    with patch.object(chain_manager, '_fetch_block', return_value=mock_block):
        # Process blocks and measure performance
        for _ in range(10):
            await chain_manager.process_block("test_chain", mock_block)
        await asyncio.sleep(0.1)  # Allow metric collection

        # Verify performance metrics
        performance = await metrics.get_performance_metrics("test_chain")
        assert 'avg_block_processing_time' in performance
        assert 'avg_transaction_processing_time' in performance
        assert 'blocks_per_second' in performance

@pytest.mark.asyncio
async def test_resource_monitoring(monitoring_system, blockchain_system):
    """Test monitoring of resource usage by blockchain components."""
    metrics = monitoring_system['metrics']
    chain_manager = blockchain_system['chain']

    # Monitor resource usage during operations
    await metrics.start_resource_monitoring("test_chain")

    # Perform some operations
    mock_block = {"number": 1000, "hash": "0x123...", "transactions": []}
    with patch.object(chain_manager, '_fetch_block', return_value=mock_block):
        for _ in range(10):
            await chain_manager.process_block("test_chain", mock_block)

    await asyncio.sleep(0.1)  # Allow metric collection

    # Verify resource metrics
    resources = await metrics.get_resource_metrics("test_chain")
    assert 'memory_usage' in resources
    assert 'cpu_usage' in resources
    assert 'network_io' in resources
