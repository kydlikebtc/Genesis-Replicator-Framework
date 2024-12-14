"""
Load testing for the monitoring system.
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from genesis_replicator.monitoring.metrics_collector import MetricsCollector
from genesis_replicator.monitoring.health_checker import HealthChecker, HealthCheck
from genesis_replicator.monitoring.alert_manager import AlertManager, AlertSeverity

async def test_high_volume_metrics(metrics_collector, component_metrics):
    """Test metrics collection under high load."""
    start_time = time.time()

    # Simulate high volume of metrics
    tasks = []
    for i in range(10000):
        component_metrics.component_id = f"component_{i}"
        tasks.append(
            metrics_collector.record_component_metrics(
                f"component_{i}",
                component_metrics
            )
        )

    # Record metrics concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        await asyncio.gather(*tasks)

    duration = time.time() - start_time
    assert duration < 5.0  # Should handle 10k metrics in under 5 seconds

async def test_concurrent_health_checks(health_checker):
    """Test health checker under concurrent load."""
    # Create multiple health checks
    for i in range(100):
        health_checker.register_check(
            HealthCheck(
                name=f"check_{i}",
                check_fn=lambda: True,
                interval=1,
                timeout=1.0,
                dependencies=[]
            )
        )

    start_time = time.time()
    await health_checker.start()
    await asyncio.sleep(2)

    # Verify all checks executed
    results = health_checker.get_system_health()
    assert len(results) == 100
    duration = time.time() - start_time
    assert duration < 3.0  # Should complete all checks in under 3 seconds

async def test_alert_storm_handling(alert_manager):
    """Test alert manager under alert storm conditions."""
    start_time = time.time()

    # Generate alert storm
    tasks = []
    for i in range(1000):
        tasks.append(
            alert_manager.create_alert(
                title=f"Storm Alert {i}",
                description="Test Alert Storm",
                severity=AlertSeverity.WARNING,
                source="test_load"
            )
        )

    # Create alerts concurrently
    await asyncio.gather(*tasks)

    duration = time.time() - start_time
    assert duration < 2.0  # Should handle 1000 alerts in under 2 seconds

    # Verify alert processing
    active_alerts = alert_manager.get_active_alerts()
    assert len(active_alerts) == 1000

async def test_system_recovery(metrics_collector, health_checker, alert_manager, component_metrics):
    """Test system recovery under load."""
    # Simulate system under load
    await test_high_volume_metrics(metrics_collector, component_metrics)
    await test_concurrent_health_checks(health_checker)
    await test_alert_storm_handling(alert_manager)

    # Verify system stability
    assert metrics_collector._running
    assert len(health_checker.get_unhealthy_components()) == 0
    assert alert_manager.get_active_alerts() is not None
