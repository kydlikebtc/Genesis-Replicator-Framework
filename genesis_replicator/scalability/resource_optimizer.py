"""
Resource Optimizer implementation for Genesis Replicator Framework.

Handles vertical scaling and resource optimization.
"""

import asyncio
import logging
import psutil
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    """Container for resource usage metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Tuple[float, float]  # (bytes_sent, bytes_recv)
    timestamp: datetime = field(default_factory=datetime.now)

class ResourceOptimizer:
    """Manages vertical scaling and resource optimization."""

    def __init__(self):
        """Initialize the resource optimizer."""
        self._metrics_history: List[ResourceMetrics] = []
        self._optimization_task: Optional[asyncio.Task] = None
        self._thresholds = {
            'cpu_high': 80.0,
            'cpu_low': 20.0,
            'memory_high': 85.0,
            'memory_low': 30.0,
            'disk_high': 90.0
        }

    async def start(self) -> None:
        """Start the resource optimizer service."""
        logger.info("Starting resource optimizer service...")
        self._optimization_task = asyncio.create_task(self._optimization_loop())

    async def stop(self) -> None:
        """Stop the resource optimizer service."""
        logger.info("Stopping resource optimizer service...")
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass

    async def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource usage metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()

        metrics = ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            network_io=(net_io.bytes_sent, net_io.bytes_recv)
        )

        self._metrics_history.append(metrics)
        if len(self._metrics_history) > 100:  # Keep last 100 measurements
            self._metrics_history.pop(0)

        return metrics

    async def get_optimization_recommendations(self) -> Dict[str, str]:
        """Get resource optimization recommendations."""
        metrics = await self.get_current_metrics()
        recommendations = {}

        # CPU optimization
        if metrics.cpu_percent > self._thresholds['cpu_high']:
            recommendations['cpu'] = 'Consider scaling up CPU resources or optimizing CPU-intensive operations'
        elif metrics.cpu_percent < self._thresholds['cpu_low']:
            recommendations['cpu'] = 'Consider scaling down CPU resources to optimize costs'

        # Memory optimization
        if metrics.memory_percent > self._thresholds['memory_high']:
            recommendations['memory'] = 'Consider increasing memory allocation or implementing memory optimization'
        elif metrics.memory_percent < self._thresholds['memory_low']:
            recommendations['memory'] = 'Consider reducing memory allocation to optimize costs'

        # Disk optimization
        if metrics.disk_usage_percent > self._thresholds['disk_high']:
            recommendations['disk'] = 'Consider increasing disk space or implementing cleanup procedures'

        return recommendations

    async def _optimization_loop(self) -> None:
        """Internal loop for continuous resource optimization."""
        while True:
            try:
                metrics = await self.get_current_metrics()
                recommendations = await self.get_optimization_recommendations()

                if recommendations:
                    logger.info("Resource optimization recommendations:")
                    for resource, recommendation in recommendations.items():
                        logger.info(f"{resource}: {recommendation}")

                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def update_thresholds(self, thresholds: Dict[str, float]) -> None:
        """Update resource optimization thresholds."""
        self._thresholds.update(thresholds)
        logger.info("Updated resource optimization thresholds")
