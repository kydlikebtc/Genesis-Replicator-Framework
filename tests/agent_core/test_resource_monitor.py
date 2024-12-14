"""
Tests for the Resource Monitor implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from genesis_replicator.agent_core.resource_monitor import ResourceMonitor

@pytest.fixture
async def resource_monitor():
    """Create a new ResourceMonitor instance for testing."""
    monitor = ResourceMonitor()
    await monitor.start()
    yield monitor
    await monitor.stop()

@pytest.mark.asyncio
async def test_resource_tracking():
    """Test resource usage tracking."""
    monitor = ResourceMonitor()
    await monitor.start()

    # Mock system metrics
    mock_metrics = {
        "cpu_percent": 50.0,
        "memory_percent": 60.0,
        "disk_usage": 70.0
    }

    with patch.object(monitor, '_get_system_metrics', return_value=mock_metrics):
        metrics = await monitor.get_current_metrics()
        assert metrics["cpu_percent"] == 50.0
        assert metrics["memory_percent"] == 60.0
        assert metrics["disk_usage"] == 70.0

    await monitor.stop()

@pytest.mark.asyncio
async def test_resource_thresholds():
    """Test resource threshold monitoring."""
    monitor = ResourceMonitor()
    await monitor.start()

    alerts = []
    async def alert_callback(metric, value, threshold):
        alerts.append((metric, value, threshold))

    # Set thresholds and register callback
    monitor.set_threshold("cpu_percent", 80.0, alert_callback)
    monitor.set_threshold("memory_percent", 90.0, alert_callback)

    # Mock high resource usage
    mock_metrics = {
        "cpu_percent": 85.0,
        "memory_percent": 95.0
    }

    with patch.object(monitor, '_get_system_metrics', return_value=mock_metrics):
        await monitor._check_thresholds()
        await asyncio.sleep(0.1)  # Allow async processing

    assert len(alerts) == 2
    assert alerts[0][0] == "cpu_percent"
    assert alerts[1][0] == "memory_percent"

    await monitor.stop()

@pytest.mark.asyncio
async def test_resource_history():
    """Test resource usage history tracking."""
    monitor = ResourceMonitor()
    await monitor.start()

    # Mock metrics over time
    mock_metrics_1 = {"cpu_percent": 50.0}
    mock_metrics_2 = {"cpu_percent": 60.0}

    with patch.object(monitor, '_get_system_metrics') as mock_get:
        mock_get.side_effect = [mock_metrics_1, mock_metrics_2]

        await monitor._update_metrics()
        await monitor._update_metrics()

        history = monitor.get_metrics_history("cpu_percent")
        assert len(history) == 2
        assert history[0] == 50.0
        assert history[1] == 60.0

    await monitor.stop()

@pytest.mark.asyncio
async def test_agent_resource_tracking():
    """Test per-agent resource tracking."""
    monitor = ResourceMonitor()
    await monitor.start()

    # Register agent for tracking
    agent_id = "test_agent"
    await monitor.register_agent(agent_id)

    # Mock agent metrics
    mock_metrics = {
        "cpu_usage": 30.0,
        "memory_usage": 100_000_000
    }

    with patch.object(monitor, '_get_agent_metrics', return_value=mock_metrics):
        metrics = await monitor.get_agent_metrics(agent_id)
        assert metrics["cpu_usage"] == 30.0
        assert metrics["memory_usage"] == 100_000_000

    await monitor.stop()

@pytest.mark.asyncio
async def test_resource_optimization():
    """Test resource optimization suggestions."""
    monitor = ResourceMonitor()
    await monitor.start()

    # Mock system state
    mock_metrics = {
        "cpu_percent": 90.0,
        "memory_percent": 95.0,
        "disk_usage": 85.0
    }

    with patch.object(monitor, '_get_system_metrics', return_value=mock_metrics):
        suggestions = await monitor.get_optimization_suggestions()
        assert len(suggestions) > 0
        assert any("CPU" in s for s in suggestions)
        assert any("memory" in s for s in suggestions)

    await monitor.stop()

@pytest.mark.asyncio
async def test_resource_limits():
    """Test resource limit enforcement."""
    monitor = ResourceMonitor()
    await monitor.start()

    agent_id = "test_agent"
    await monitor.register_agent(agent_id)

    # Set resource limits
    limits = {
        "cpu_percent": 50.0,
        "memory_mb": 1024
    }
    await monitor.set_agent_limits(agent_id, limits)

    # Mock excessive resource usage
    mock_metrics = {
        "cpu_usage": 60.0,
        "memory_usage": 2 * 1024 * 1024 * 1024  # 2GB
    }

    with patch.object(monitor, '_get_agent_metrics', return_value=mock_metrics):
        violations = await monitor.check_agent_limits(agent_id)
        assert len(violations) == 2
        assert "cpu_percent" in violations
        assert "memory_mb" in violations

    await monitor.stop()
