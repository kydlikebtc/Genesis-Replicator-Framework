"""
Test fixtures for the monitoring system.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from genesis_replicator.monitoring.metrics_collector import (
    MetricsCollector, SystemMetrics, ComponentMetrics
)
from genesis_replicator.monitoring.health_checker import (
    HealthChecker, HealthCheck, HealthStatus
)
from genesis_replicator.monitoring.alert_manager import (
    AlertManager, AlertHandler, AlertSeverity, Alert
)
from genesis_replicator.monitoring.monitoring_config import (
    MonitoringConfig, MetricsConfig, HealthCheckConfig, AlertConfig
)

@pytest.fixture
def test_metrics_config():
    """Fixture for test metrics configuration."""
    return MetricsConfig(
        collection_interval=1,
        retention_period=60,
        max_entries=10,
        enabled_metrics=["cpu", "memory", "disk"]
    )

@pytest.fixture
def test_health_config():
    """Fixture for test health check configuration."""
    return HealthCheckConfig(
        check_interval=1,
        timeout=1.0,
        retry_count=1,
        retry_delay=1
    )

@pytest.fixture
def test_alert_config():
    """Fixture for test alert configuration."""
    return AlertConfig(
        notification_channels=["test"],
        severity_thresholds={
            "cpu_usage": 90.0,
            "memory_usage": 90.0,
            "disk_usage": 90.0,
            "error_rate": 0.1
        },
        aggregation_window=10,
        cooldown_period=30
    )

class TestAlertHandler(AlertHandler):
    """Test implementation of alert handler."""

    def __init__(self):
        self.alerts: List[Alert] = []

    async def handle_alert(self, alert: Alert):
        """Store alert for testing."""
        self.alerts.append(alert)

@pytest.fixture
def test_alert_handler():
    """Fixture for test alert handler."""
    return TestAlertHandler()

@pytest.fixture
async def metrics_collector():
    """Fixture for metrics collector."""
    collector = MetricsCollector(collection_interval=1)
    await collector.start()
    yield collector
    await collector.stop()

@pytest.fixture
def mock_health_check():
    """Fixture for mock health check function."""
    async def check_fn() -> bool:
        return True
    return HealthCheck(
        name="test_check",
        check_fn=check_fn,
        interval=1,
        timeout=1.0,
        dependencies=[]
    )

@pytest.fixture
async def health_checker():
    """Fixture for health checker."""
    checker = HealthChecker()
    yield checker
    await checker.stop()

@pytest.fixture
async def alert_manager():
    """Fixture for alert manager."""
    return AlertManager()

@pytest.fixture
def monitoring_config(tmp_path):
    """Fixture for monitoring configuration."""
    config_path = tmp_path / "test_monitoring_config.json"
    return MonitoringConfig(str(config_path))

@pytest.fixture
def component_metrics():
    """Fixture for test component metrics."""
    return ComponentMetrics(
        component_id="test_component",
        operation_count=100,
        error_count=5,
        latency=0.1,
        custom_metrics={"test_metric": 42.0},
        timestamp=datetime.now()
    )

@pytest.fixture
def system_metrics():
    """Fixture for test system metrics."""
    return SystemMetrics(
        cpu_usage=50.0,
        memory_usage=60.0,
        disk_usage=70.0,
        network_io={
            "bytes_sent": 1000,
            "bytes_recv": 2000
        },
        timestamp=datetime.now()
    )
