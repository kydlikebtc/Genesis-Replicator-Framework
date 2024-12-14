"""
Metrics collection system for Genesis Replicator Framework.

This module handles collection, aggregation, and storage of system metrics
including resource utilization, performance metrics, and system statistics.
"""

import asyncio
import psutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SystemMetrics:
    """Container for system-level metrics."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    timestamp: datetime

@dataclass
class ComponentMetrics:
    """Container for component-specific metrics."""
    component_id: str
    operation_count: int
    error_count: int
    latency: float
    custom_metrics: Dict[str, Any]
    timestamp: datetime

class MetricsCollector:
    """Collects and manages system and component metrics."""

    def __init__(self, collection_interval: int = 60):
        """Initialize the metrics collector.

        Args:
            collection_interval: Interval in seconds between metric collections
        """
        self.collection_interval = collection_interval
        self.component_metrics: Dict[str, List[ComponentMetrics]] = {}
        self.system_metrics: List[SystemMetrics] = []
        self._running = False
        self._collection_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the metrics collection process."""
        if self._running:
            return
        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics())

    async def stop(self):
        """Stop the metrics collection process."""
        self._running = False
        if self._collection_task:
            await self._collection_task

    async def _collect_metrics(self):
        """Continuously collect system and component metrics."""
        while self._running:
            await self._collect_system_metrics()
            await asyncio.sleep(self.collection_interval)

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        metrics = SystemMetrics(
            cpu_usage=psutil.cpu_percent(),
            memory_usage=psutil.virtual_memory().percent,
            disk_usage=psutil.disk_usage('/').percent,
            network_io={
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv
            },
            timestamp=datetime.now()
        )
        self.system_metrics.append(metrics)
        self._trim_metrics()

    def record_component_metrics(self, component_id: str, metrics: ComponentMetrics):
        """Record metrics for a specific component.

        Args:
            component_id: Unique identifier for the component
            metrics: Component-specific metrics to record
        """
        if component_id not in self.component_metrics:
            self.component_metrics[component_id] = []
        self.component_metrics[component_id].append(metrics)
        self._trim_component_metrics(component_id)

    def _trim_metrics(self, max_entries: int = 1000):
        """Trim system metrics to prevent memory overflow."""
        if len(self.system_metrics) > max_entries:
            self.system_metrics = self.system_metrics[-max_entries:]

    def _trim_component_metrics(self, component_id: str, max_entries: int = 1000):
        """Trim component metrics to prevent memory overflow."""
        if len(self.component_metrics[component_id]) > max_entries:
            self.component_metrics[component_id] = \
                self.component_metrics[component_id][-max_entries:]

    def get_system_metrics(self,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> List[SystemMetrics]:
        """Get system metrics within the specified time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of system metrics within the time range
        """
        if not start_time and not end_time:
            return self.system_metrics

        filtered_metrics = [
            metric for metric in self.system_metrics
            if (not start_time or metric.timestamp >= start_time) and
               (not end_time or metric.timestamp <= end_time)
        ]
        return filtered_metrics

    def get_component_metrics(self,
                            component_id: str,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[ComponentMetrics]:
        """Get component metrics within the specified time range.

        Args:
            component_id: ID of the component
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of component metrics within the time range
        """
        if component_id not in self.component_metrics:
            return []

        metrics = self.component_metrics[component_id]
        if not start_time and not end_time:
            return metrics

        filtered_metrics = [
            metric for metric in metrics
            if (not start_time or metric.timestamp >= start_time) and
               (not end_time or metric.timestamp <= end_time)
        ]
        return filtered_metrics
