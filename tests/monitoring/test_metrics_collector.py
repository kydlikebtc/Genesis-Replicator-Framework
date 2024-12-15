"""
Tests for the metrics collection system.
"""
import pytest
from datetime import datetime, timedelta
import asyncio
from genesis_replicator.monitoring.metrics_collector import MetricsCollector, ComponentMetrics

async def test_metrics_collection(metrics_collector, component_metrics):
    """Test basic metrics collection functionality."""
    # Record component metrics
    metrics_collector.record_component_metrics("test_component", component_metrics)

    # Verify metrics were recorded
    stored_metrics = metrics_collector.get_component_metrics("test_component")
    assert len(stored_metrics) == 1
    assert stored_metrics[0].component_id == "test_component"
    assert stored_metrics[0].operation_count == 100

async def test_system_metrics_collection(metrics_collector):
    """Test system metrics collection."""
    # Wait for metrics collection
    await asyncio.sleep(2)

    # Verify system metrics
    metrics = metrics_collector.get_system_metrics()
    assert len(metrics) > 0
    assert isinstance(metrics[0].cpu_usage, float)
    assert isinstance(metrics[0].memory_usage, float)
    assert isinstance(metrics[0].disk_usage, float)

async def test_metrics_filtering(metrics_collector, component_metrics):
    """Test metrics filtering by time range."""
    start_time = datetime.now()
    await asyncio.sleep(1)

    metrics_collector.record_component_metrics("test_component", component_metrics)

    end_time = datetime.now()
    future_time = end_time + timedelta(hours=1)

    # Test filtering
    filtered_metrics = metrics_collector.get_component_metrics(
        "test_component",
        start_time=start_time,
        end_time=end_time
    )
    assert len(filtered_metrics) == 1

    # Test future filtering
    future_metrics = metrics_collector.get_component_metrics(
        "test_component",
        start_time=end_time,
        end_time=future_time
    )
    assert len(future_metrics) == 0

async def test_metrics_trimming(metrics_collector, component_metrics):
    """Test metrics trimming functionality."""
    # Record more than max entries
    for _ in range(1100):
        metrics_collector.record_component_metrics("test_component", component_metrics)

    # Verify trimming
    stored_metrics = metrics_collector.get_component_metrics("test_component")
    assert len(stored_metrics) == 1000  # Default max_entries

async def test_performance_benchmarking(metrics_collector, component_metrics):
    """Test metrics collection performance."""
    start_time = datetime.now()

    # Simulate high load
    for _ in range(1000):
        metrics_collector.record_component_metrics("test_component", component_metrics)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Performance assertions
    assert duration < 1.0  # Should handle 1000 metrics in under 1 second
