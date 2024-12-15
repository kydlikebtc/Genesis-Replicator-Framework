"""
Tests for circuit breaker.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from genesis_replicator.event_processing.circuit_breaker import (
    CircuitBreaker,
    CircuitState
)

@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(
        failure_threshold=0.5,
        reset_timeout=0.1,
        half_open_timeout=0.05
    )

@pytest.mark.asyncio
async def test_successful_execution(circuit_breaker):
    async def operation():
        return "success"

    result = await circuit_breaker.execute("test_circuit", operation)
    assert result == "success"

    stats = await circuit_breaker.get_circuit_stats("test_circuit")
    assert stats["current_state"] == CircuitState.CLOSED.value
    assert stats["total_requests"] == 1
    assert stats["failed_requests"] == 0

@pytest.mark.asyncio
async def test_circuit_opening(circuit_breaker):
    failure_count = 0
    async def failing_operation():
        nonlocal failure_count
        failure_count += 1
        raise RuntimeError("Operation failed")

    # Generate failures
    for _ in range(10):
        try:
            await circuit_breaker.execute("test_circuit", failing_operation)
        except RuntimeError:
            pass

    stats = await circuit_breaker.get_circuit_stats("test_circuit")
    assert stats["current_state"] == CircuitState.OPEN.value
    assert stats["failed_requests"] == 10

    # Verify circuit rejects requests when open
    with pytest.raises(RuntimeError, match="Circuit test_circuit is open"):
        await circuit_breaker.execute("test_circuit", failing_operation)

@pytest.mark.asyncio
async def test_circuit_reset(circuit_breaker):
    async def failing_operation():
        raise RuntimeError("Operation failed")

    # Generate failures
    for _ in range(10):
        try:
            await circuit_breaker.execute("test_circuit", failing_operation)
        except RuntimeError:
            pass

    # Wait for reset timeout
    await asyncio.sleep(0.2)

    # Circuit should be half-open
    stats = await circuit_breaker.get_circuit_stats("test_circuit")
    assert stats["current_state"] == CircuitState.HALF_OPEN.value

    # Successful operation should close circuit
    async def success_operation():
        return "success"

    result = await circuit_breaker.execute("test_circuit", success_operation)
    assert result == "success"

    stats = await circuit_breaker.get_circuit_stats("test_circuit")
    assert stats["current_state"] == CircuitState.CLOSED.value

@pytest.mark.asyncio
async def test_manual_reset(circuit_breaker):
    async def failing_operation():
        raise RuntimeError("Operation failed")

    # Generate failures
    for _ in range(10):
        try:
            await circuit_breaker.execute("test_circuit", failing_operation)
        except RuntimeError:
            pass

    # Manually reset circuit
    await circuit_breaker.reset_circuit("test_circuit")

    stats = await circuit_breaker.get_circuit_stats("test_circuit")
    assert stats["current_state"] == CircuitState.CLOSED.value
    assert stats["total_requests"] == 0
    assert stats["failed_requests"] == 0
