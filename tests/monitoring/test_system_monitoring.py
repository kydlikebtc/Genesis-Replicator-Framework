"""
System monitoring validation tests.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from genesis_replicator.monitoring.metrics_collector import MetricsCollector
from genesis_replicator.monitoring.health_checker import HealthChecker
from genesis_replicator.monitoring.alert_manager import AlertManager
from genesis_replicator.monitoring.monitoring_config import MonitoringConfig

@pytest.fixture
async def monitoring_system():
    """Set up monitoring system components."""
    config = MonitoringConfig()
    metrics_collector = MetricsCollector(config)
    health_checker = HealthChecker(config)
    alert_manager = AlertManager(config)

    await metrics_collector.start()
    await health_checker.start()
    await alert_manager.start()

    yield {
        "metrics": metrics_collector,
        "health": health_checker,
        "alerts": alert_manager,
        "config": config
    }

    await metrics_collector.stop()
    await health_checker.stop()
    await alert_manager.stop()

@pytest.mark.monitoring
@pytest.mark.asyncio
async def test_metrics_collection(monitoring_system):
    """Test system metrics collection."""
    metrics = monitoring_system["metrics"]

    # Collect system metrics
    system_metrics = await metrics.collect_system_metrics()

    # Verify required metrics
    assert "cpu_usage" in system_metrics
    assert "memory_usage" in system_metrics
    assert "disk_usage" in system_metrics
    assert "network_io" in system_metrics

    # Verify metric values
    assert 0 <= system_metrics["cpu_usage"] <= 100
    assert 0 <= system_metrics["memory_usage"] <= 100
    assert 0 <= system_metrics["disk_usage"] <= 100
    assert "rx_bytes" in system_metrics["network_io"]
    assert "tx_bytes" in system_metrics["network_io"]

@pytest.mark.monitoring
@pytest.mark.asyncio
async def test_health_checking(monitoring_system):
    """Test health checking functionality."""
    health = monitoring_system["health"]

    # Check overall system health
    health_status = await health.check_system_health()

    # Verify health check components
    assert "status" in health_status
    assert "components" in health_status
    assert "timestamp" in health_status

    # Verify component health checks
    components = health_status["components"]
    assert "database" in components
    assert "blockchain" in components
    assert "ai_models" in components
    assert "event_system" in components

    # Verify health status format
    for component in components.values():
        assert "status" in component
        assert "message" in component
        assert "last_check" in component

@pytest.mark.monitoring
@pytest.mark.asyncio
async def test_alert_generation(monitoring_system):
    """Test alert generation and management."""
    alerts = monitoring_system["alerts"]
    metrics = monitoring_system["metrics"]

    # Simulate high CPU usage
    mock_metrics = {
        "cpu_usage": 95,
        "memory_usage": 50,
        "disk_usage": 60
    }

    # Register alert handlers
    test_alerts = []
    async def alert_handler(alert):
        test_alerts.append(alert)

    alerts.register_handler(alert_handler)

    # Trigger alert evaluation
    await alerts.evaluate_metrics(mock_metrics)
    await asyncio.sleep(0.1)  # Allow for alert processing

    # Verify alert generation
    assert len(test_alerts) > 0
    alert = test_alerts[0]
    assert alert["severity"] == "high"
    assert "CPU usage" in alert["message"]
    assert alert["timestamp"] is not None

@pytest.mark.monitoring
@pytest.mark.asyncio
async def test_metric_aggregation(monitoring_system):
    """Test metric aggregation and statistics."""
    metrics = monitoring_system["metrics"]

    # Generate test metrics
    test_metrics = []
    for _ in range(10):
        metric = {
            "cpu_usage": 50 + _ * 5,
            "memory_usage": 60 + _ * 3,
            "timestamp": datetime.now() - timedelta(minutes=_)
        }
        test_metrics.append(metric)
        await metrics.record_metrics(metric)

    # Get aggregated metrics
    aggregated = await metrics.get_aggregated_metrics(
        window_minutes=15
    )

    # Verify aggregation
    assert "cpu_usage" in aggregated
    assert "avg" in aggregated["cpu_usage"]
    assert "max" in aggregated["cpu_usage"]
    assert "min" in aggregated["cpu_usage"]
    assert 50 <= aggregated["cpu_usage"]["avg"] <= 95

@pytest.mark.monitoring
@pytest.mark.asyncio
async def test_monitoring_integration(monitoring_system):
    """Test monitoring system integration."""
    metrics = monitoring_system["metrics"]
    health = monitoring_system["health"]
    alerts = monitoring_system["alerts"]

    # Simulate system activity
    async def generate_activity():
        for _ in range(5):
            # Record metrics
            await metrics.record_metrics({
                "cpu_usage": 70 + _ * 5,
                "memory_usage": 80,
                "disk_usage": 75
            })

            # Check health
            await health.check_system_health()

            # Short delay
            await asyncio.sleep(0.1)

    # Run activity generation
    await generate_activity()

    # Verify monitoring data
    metrics_data = await metrics.get_recent_metrics()
    health_data = await health.get_health_history()
    alerts_data = await alerts.get_recent_alerts()

    # Verify data consistency
    assert len(metrics_data) >= 5
    assert len(health_data) >= 5
    assert isinstance(alerts_data, list)

@pytest.mark.monitoring
@pytest.mark.asyncio
async def test_recovery_monitoring(monitoring_system):
    """Test monitoring during system recovery."""
    health = monitoring_system["health"]
    alerts = monitoring_system["alerts"]

    # Simulate component failure
    await health.record_component_failure("database", "Connection lost")

    # Verify failure detection
    health_status = await health.check_system_health()
    assert health_status["components"]["database"]["status"] == "unhealthy"

    # Simulate recovery
    await health.record_component_recovery("database", "Connection restored")

    # Verify recovery detection
    health_status = await health.check_system_health()
    assert health_status["components"]["database"]["status"] == "healthy"

    # Check recovery alerts
    alerts_data = await alerts.get_recent_alerts()
    recovery_alerts = [a for a in alerts_data if "recovered" in a["message"].lower()]
    assert len(recovery_alerts) > 0
