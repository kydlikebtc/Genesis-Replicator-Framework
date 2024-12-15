"""
Tests for the resource optimization system.
"""
import pytest
from datetime import datetime

from genesis_replicator.scalability.resource_optimizer import ResourceOptimizer, ResourceMetrics

async def test_metrics_collection(resource_optimizer: ResourceOptimizer):
    """Test resource metrics collection."""
    metrics = await resource_optimizer.get_current_metrics()

    assert isinstance(metrics, ResourceMetrics)
    assert 0 <= metrics.cpu_percent <= 100
    assert 0 <= metrics.memory_percent <= 100
    assert 0 <= metrics.disk_usage_percent <= 100
    assert len(metrics.network_io) == 2
    assert isinstance(metrics.timestamp, datetime)

async def test_optimization_recommendations(resource_optimizer: ResourceOptimizer):
    """Test resource optimization recommendations."""
    # Update thresholds for testing
    await resource_optimizer.update_thresholds({
        'cpu_high': 50.0,
        'cpu_low': 10.0,
        'memory_high': 50.0,
        'memory_low': 10.0,
        'disk_high': 50.0
    })

    recommendations = await resource_optimizer.get_optimization_recommendations()
    assert isinstance(recommendations, dict)

    # Verify recommendation format
    for resource, recommendation in recommendations.items():
        assert isinstance(resource, str)
        assert isinstance(recommendation, str)

async def test_threshold_updates(resource_optimizer: ResourceOptimizer):
    """Test updating optimization thresholds."""
    new_thresholds = {
        'cpu_high': 90.0,
        'cpu_low': 30.0,
        'memory_high': 95.0,
        'memory_low': 40.0,
        'disk_high': 95.0
    }

    await resource_optimizer.update_thresholds(new_thresholds)

    # Get recommendations with new thresholds
    recommendations = await resource_optimizer.get_optimization_recommendations()
    assert isinstance(recommendations, dict)
