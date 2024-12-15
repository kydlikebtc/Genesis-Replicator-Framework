"""
Circuit breaker implementation for fault tolerance.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    failed_requests: int = 0
    success_rate: float = 1.0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED

class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(
        self,
        failure_threshold: float = 0.5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 30.0
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failure rate threshold
            reset_timeout: Time before reset attempt
            half_open_timeout: Time in half-open state
        """
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_timeout = half_open_timeout
        self._circuits: Dict[str, CircuitStats] = {}
        self._lock = asyncio.Lock()
        self._reset_timers: Dict[str, asyncio.Task] = {}
        logger.info("Circuit breaker initialized")

    async def execute(
        self,
        circuit_id: str,
        operation: Callable[[], Awaitable[Any]]
    ) -> Any:
        """Execute operation with circuit breaker protection.

        Args:
            circuit_id: Circuit identifier
            operation: Async operation to execute

        Returns:
            Operation result

        Raises:
            RuntimeError: If circuit is open
        """
        async with self._lock:
            if circuit_id not in self._circuits:
                self._circuits[circuit_id] = CircuitStats()

            stats = self._circuits[circuit_id]

            # Check circuit state
            if stats.current_state == CircuitState.OPEN:
                if self._should_attempt_reset(stats):
                    stats.current_state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeError(f"Circuit {circuit_id} is open")

        try:
            # Execute operation
            result = await operation()

            # Update success stats
            async with self._lock:
                stats = self._circuits[circuit_id]
                stats.total_requests += 1
                stats.last_success = datetime.now()
                stats.success_rate = (stats.total_requests - stats.failed_requests) / stats.total_requests

                # Handle success in half-open state
                if stats.current_state == CircuitState.HALF_OPEN:
                    stats.current_state = CircuitState.CLOSED
                    if circuit_id in self._reset_timers:
                        self._reset_timers[circuit_id].cancel()

            return result

        except Exception as e:
            # Update failure stats
            async with self._lock:
                stats = self._circuits[circuit_id]
                stats.total_requests += 1
                stats.failed_requests += 1
                stats.last_failure = datetime.now()
                stats.success_rate = (stats.total_requests - stats.failed_requests) / stats.total_requests

                # Check if circuit should open
                if self._should_open_circuit(stats):
                    stats.current_state = CircuitState.OPEN
                    self._start_reset_timer(circuit_id)

            raise

    def _should_open_circuit(self, stats: CircuitStats) -> bool:
        """Check if circuit should open.

        Args:
            stats: Circuit statistics

        Returns:
            True if circuit should open
        """
        return (
            stats.total_requests >= 10 and  # Minimum sample size
            stats.success_rate < (1 - self._failure_threshold)
        )

    def _should_attempt_reset(self, stats: CircuitStats) -> bool:
        """Check if reset should be attempted.

        Args:
            stats: Circuit statistics

        Returns:
            True if reset should be attempted
        """
        if not stats.last_failure:
            return True

        elapsed = (datetime.now() - stats.last_failure).total_seconds()
        return elapsed >= self._reset_timeout

    def _start_reset_timer(self, circuit_id: str) -> None:
        """Start timer for circuit reset.

        Args:
            circuit_id: Circuit identifier
        """
        if circuit_id in self._reset_timers:
            self._reset_timers[circuit_id].cancel()

        async def timer():
            await asyncio.sleep(self._reset_timeout)
            async with self._lock:
                if circuit_id in self._circuits:
                    stats = self._circuits[circuit_id]
                    if stats.current_state == CircuitState.OPEN:
                        stats.current_state = CircuitState.HALF_OPEN

        self._reset_timers[circuit_id] = asyncio.create_task(timer())

    async def get_circuit_stats(
        self,
        circuit_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get circuit statistics.

        Args:
            circuit_id: Circuit identifier

        Returns:
            Circuit statistics if found
        """
        async with self._lock:
            if circuit_id not in self._circuits:
                return None

            stats = self._circuits[circuit_id]
            return {
                "total_requests": stats.total_requests,
                "failed_requests": stats.failed_requests,
                "success_rate": stats.success_rate,
                "current_state": stats.current_state.value,
                "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
                "last_success": stats.last_success.isoformat() if stats.last_success else None
            }

    async def reset_circuit(
        self,
        circuit_id: str
    ) -> None:
        """Manually reset circuit to closed state.

        Args:
            circuit_id: Circuit identifier
        """
        async with self._lock:
            if circuit_id in self._circuits:
                self._circuits[circuit_id] = CircuitStats()
                if circuit_id in self._reset_timers:
                    self._reset_timers[circuit_id].cancel()
                    del self._reset_timers[circuit_id]
