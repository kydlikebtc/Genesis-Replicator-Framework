"""
Integration tests for the monitoring system.
"""
import pytest
import asyncio
from genesis_replicator.monitoring.metrics_collector import MetricsCollector
from genesis_replicator.monitoring.health_checker import (
    HealthChecker, HealthCheck, HealthStatus
)
from genesis_replicator.monitoring.alert_manager import (
    AlertManager, AlertSeverity, AlertStatus
)
from genesis_replicator.monitoring.monitoring_config import MonitoringConfig

async def test_metrics_to_alerts_flow(
    metrics_collector,
    health_checker,
    alert_manager,
    monitoring_config,
    component_metrics
):
    """Test flow from metrics collection to alert generation."""
    # Configure alert thresholds
    monitoring_config.update_alert_config(
        severity_thresholds={"error_rate": 0.01}
    )

    # Record metrics with high error rate
    component_metrics.error_count = 1000
    component_metrics.operation_count = 1000
    metrics_collector.record_component_metrics(
        "test_component",
        component_metrics
    )

    # Create health check based on metrics
    def check_error_rate():
        metrics = metrics_collector.get_component_metrics("test_component")
        if not metrics:
            return True
        error_rate = metrics[-1].error_count / metrics[-1].operation_count
        return error_rate < monitoring_config.alert_config.severity_thresholds["error_rate"]

    health_checker.register_check(
        HealthCheck(
            name="error_rate_check",
            check_fn=check_error_rate,
            interval=1,
            timeout=1.0,
            dependencies=[]
        )
    )

    # Start health checking
    await health_checker.start()
    await asyncio.sleep(2)

    # Verify alert generation
    result = health_checker.get_component_health("error_rate_check")
    assert result.status == HealthStatus.UNHEALTHY

    alerts = alert_manager.get_alerts_by_severity(AlertSeverity.ERROR)
    assert len(alerts) > 0
    assert "error_rate" in alerts[0].description.lower()

async def test_monitoring_system_startup(
    metrics_collector,
    health_checker,
    alert_manager,
    monitoring_config
):
    """Test monitoring system startup sequence."""
    # Start all components
    await metrics_collector.start()
    await health_checker.start()

    # Verify system initialization
    assert metrics_collector._running
    assert health_checker._running
    assert len(alert_manager.get_active_alerts()) == 0

    # Verify configuration loaded
    assert monitoring_config.metrics_config.collection_interval > 0
    assert monitoring_config.health_check_config.check_interval > 0

async def test_monitoring_system_shutdown(
    metrics_collector,
    health_checker,
    alert_manager
):
    """Test monitoring system shutdown sequence."""
    # Start components
    await metrics_collector.start()
    await health_checker.start()

    # Shutdown components
    await metrics_collector.stop()
    await health_checker.stop()

    # Verify shutdown
    assert not metrics_collector._running
    assert not health_checker._running

    # Verify final alert status
    active_alerts = alert_manager.get_active_alerts()
    for alert in active_alerts:
        assert alert.status != AlertStatus.NEW

async def test_monitoring_system_recovery(
    metrics_collector,
    health_checker,
    alert_manager,
    component_metrics
):
    """Test monitoring system recovery procedures."""
    # Simulate component failure
    component_metrics.error_count = 1000
    metrics_collector.record_component_metrics(
        "failing_component",
        component_metrics
    )

    # Register recovery check
    recovery_count = 0
    def recovery_check():
        nonlocal recovery_count
        recovery_count += 1
        return recovery_count > 2  # Recover after 2 attempts

    health_checker.register_check(
        HealthCheck(
            name="recovery_check",
            check_fn=recovery_check,
            interval=1,
            timeout=1.0,
            dependencies=[]
        )
    )

    # Start monitoring
    await health_checker.start()
    await asyncio.sleep(1)

    # Verify initial failure
    result = health_checker.get_component_health("recovery_check")
    assert result.status == HealthStatus.UNHEALTHY

    # Wait for recovery
    await asyncio.sleep(3)
    result = health_checker.get_component_health("recovery_check")
    assert result.status == HealthStatus.HEALTHY

    # Verify recovery alerts
    alerts = alert_manager.get_alerts_by_status(AlertStatus.RESOLVED)
    assert len(alerts) > 0
