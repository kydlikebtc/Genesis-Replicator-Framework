"""
Tests for the health checking system.
"""
import pytest
import asyncio
from genesis_replicator.monitoring.health_checker import (
    HealthChecker, HealthStatus, HealthCheck
)

async def test_health_check_registration(health_checker, mock_health_check):
    """Test health check registration."""
    health_checker.register_check(mock_health_check)
    result = health_checker.get_component_health("test_check")
    assert result is not None
    assert result.status == HealthStatus.UNKNOWN

async def test_health_check_execution(health_checker, mock_health_check):
    """Test health check execution."""
    health_checker.register_check(mock_health_check)
    await health_checker.start()
    await asyncio.sleep(2)

    result = health_checker.get_component_health("test_check")
    assert result.status == HealthStatus.HEALTHY

async def test_health_check_timeout():
    """Test health check timeout handling."""
    async def slow_check():
        await asyncio.sleep(2)
        return True

    checker = HealthCheck(
        name="slow_check",
        check_fn=slow_check,
        interval=1,
        timeout=1.0,
        dependencies=[]
    )

    health_checker = HealthChecker()
    health_checker.register_check(checker)
    await health_checker.start()
    await asyncio.sleep(2)

    result = health_checker.get_component_health("slow_check")
    assert result.status == HealthStatus.DEGRADED

async def test_dependency_verification(health_checker):
    """Test health check dependency verification."""
    async def dependent_check():
        return True

    primary = HealthCheck(
        name="primary",
        check_fn=lambda: True,
        interval=1,
        timeout=1.0,
        dependencies=[]
    )

    dependent = HealthCheck(
        name="dependent",
        check_fn=dependent_check,
        interval=1,
        timeout=1.0,
        dependencies=["primary"]
    )

    health_checker.register_check(primary)
    health_checker.register_check(dependent)
    await health_checker.start()
    await asyncio.sleep(2)

    assert health_checker.get_component_health("primary").status == HealthStatus.HEALTHY
    assert health_checker.get_component_health("dependent").status == HealthStatus.HEALTHY

async def test_recovery_procedure(health_checker):
    """Test health check recovery handling."""
    failing_count = 0

    def failing_then_recovering():
        nonlocal failing_count
        failing_count += 1
        return failing_count > 3  # Recover after 3 failures

    check = HealthCheck(
        name="recovery_test",
        check_fn=failing_then_recovering,
        interval=1,
        timeout=1.0,
        dependencies=[]
    )

    health_checker.register_check(check)
    await health_checker.start()

    # Wait for initial failures
    await asyncio.sleep(2)
    assert health_checker.get_component_health("recovery_test").status == HealthStatus.UNHEALTHY

    # Wait for recovery
    await asyncio.sleep(2)
    assert health_checker.get_component_health("recovery_test").status == HealthStatus.HEALTHY
