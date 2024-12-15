"""
Health checking system for Genesis Replicator Framework.

This module provides health check functionality for system components,
including status monitoring, dependency checks, and health reporting.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Container for health check configuration."""
    name: str
    check_fn: Callable[[], bool]
    interval: int
    timeout: float
    dependencies: List[str]

@dataclass
class HealthResult:
    """Container for health check results."""
    check_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any]

class HealthChecker:
    """Manages health checks for system components."""

    def __init__(self):
        """Initialize the health checker."""
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_results: Dict[str, HealthResult] = {}
        self._running = False
        self._check_tasks: Dict[str, asyncio.Task] = {}

    def register_check(self, health_check: HealthCheck):
        """Register a new health check.

        Args:
            health_check: Health check configuration
        """
        self.health_checks[health_check.name] = health_check
        self.health_results[health_check.name] = HealthResult(
            check_name=health_check.name,
            status=HealthStatus.UNKNOWN,
            message="Health check not yet run",
            timestamp=datetime.now(),
            details={}
        )

    async def start(self):
        """Start all registered health checks."""
        if self._running:
            return
        self._running = True
        for check_name, check in self.health_checks.items():
            self._check_tasks[check_name] = asyncio.create_task(
                self._run_health_check(check_name)
            )

    async def stop(self):
        """Stop all health checks."""
        self._running = False
        for task in self._check_tasks.values():
            task.cancel()
        await asyncio.gather(*self._check_tasks.values(), return_exceptions=True)
        self._check_tasks.clear()

    async def _run_health_check(self, check_name: str):
        """Run a specific health check continuously.

        Args:
            check_name: Name of the health check to run
        """
        check = self.health_checks[check_name]
        while self._running:
            try:
                is_healthy = await asyncio.wait_for(
                    asyncio.to_thread(check.check_fn),
                    timeout=check.timeout
                )
                status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
                message = "Health check passed" if is_healthy else "Health check failed"
            except asyncio.TimeoutError:
                status = HealthStatus.DEGRADED
                message = f"Health check timed out after {check.timeout} seconds"
            except Exception as e:
                status = HealthStatus.UNHEALTHY
                message = f"Health check error: {str(e)}"

            self.health_results[check_name] = HealthResult(
                check_name=check_name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                details={"last_check_time": datetime.now().isoformat()}
            )

            await asyncio.sleep(check.interval)

    def get_component_health(self, component_name: str) -> Optional[HealthResult]:
        """Get the health status of a specific component.

        Args:
            component_name: Name of the component

        Returns:
            Health check result for the component if it exists
        """
        return self.health_results.get(component_name)

    def get_system_health(self) -> Dict[str, HealthResult]:
        """Get the health status of all components.

        Returns:
            Dictionary mapping component names to their health results
        """
        return self.health_results.copy()

    def is_system_healthy(self) -> bool:
        """Check if the entire system is healthy.

        Returns:
            True if all components are healthy, False otherwise
        """
        return all(
            result.status == HealthStatus.HEALTHY
            for result in self.health_results.values()
        )

    def get_unhealthy_components(self) -> List[str]:
        """Get a list of unhealthy components.

        Returns:
            List of component names that are not healthy
        """
        return [
            name for name, result in self.health_results.items()
            if result.status != HealthStatus.HEALTHY
        ]
