"""
Resource Monitor Module

This module monitors and manages resource usage for agents in the Genesis Replicator Framework.
It tracks CPU, memory, and other resource utilization.
"""
from typing import Dict, Optional, Any, List
import logging
import psutil
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResourceUsage:
    """Data class for storing resource usage information"""
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    network_io: Dict[str, int]
    timestamp: datetime

class ResourceLimits:
    """Configuration class for resource limits"""
    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 80.0,
        max_disk_percent: float = 90.0
    ):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_disk_percent = max_disk_percent

class ResourceMonitor:
    """
    Monitors and manages resource usage for agents.

    Attributes:
        resource_usage (Dict): Current resource usage by agent
        resource_limits (Dict): Resource limits by agent
        monitoring_interval (int): Monitoring frequency in seconds
    """

    def __init__(self, monitoring_interval: int = 60):
        """
        Initialize the ResourceMonitor.

        Args:
            monitoring_interval (int): Monitoring frequency in seconds
        """
        self.resource_usage: Dict[str, ResourceUsage] = {}
        self.resource_limits: Dict[str, ResourceLimits] = {}
        self.monitoring_interval = monitoring_interval
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        logger.info("ResourceMonitor initialized")

    async def start_monitoring(self, agent_id: str) -> bool:
        """
        Start monitoring resources for an agent.

        Args:
            agent_id (str): Agent identifier

        Returns:
            bool: Success status
        """
        try:
            if agent_id in self.monitoring_tasks:
                logger.warning(f"Agent {agent_id} already being monitored")
                return False

            task = asyncio.create_task(self._monitor_agent(agent_id))
            self.monitoring_tasks[agent_id] = task
            logger.info(f"Started monitoring agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start monitoring agent {agent_id}: {str(e)}")
            return False

    async def stop_monitoring(self, agent_id: str) -> bool:
        """
        Stop monitoring resources for an agent.

        Args:
            agent_id (str): Agent identifier

        Returns:
            bool: Success status
        """
        try:
            if agent_id not in self.monitoring_tasks:
                return False

            task = self.monitoring_tasks.pop(agent_id)
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            self.resource_usage.pop(agent_id, None)
            logger.info(f"Stopped monitoring agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping monitoring for agent {agent_id}: {str(e)}")
            return False

    def set_resource_limits(
        self,
        agent_id: str,
        limits: ResourceLimits
    ) -> bool:
        """
        Set resource limits for an agent.

        Args:
            agent_id (str): Agent identifier
            limits (ResourceLimits): Resource limits configuration

        Returns:
            bool: Success status
        """
        try:
            self.resource_limits[agent_id] = limits
            logger.info(f"Resource limits set for agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set resource limits for agent {agent_id}: {str(e)}")
            return False

    def get_resource_usage(self, agent_id: str) -> Optional[ResourceUsage]:
        """
        Get current resource usage for an agent.

        Args:
            agent_id (str): Agent identifier

        Returns:
            Optional[ResourceUsage]: Current resource usage or None if not found
        """
        return self.resource_usage.get(agent_id)

    def check_resource_limits(self, agent_id: str) -> Dict[str, bool]:
        """
        Check if agent is within resource limits.

        Args:
            agent_id (str): Agent identifier

        Returns:
            Dict[str, bool]: Resource limit status for each resource type
        """
        try:
            if agent_id not in self.resource_usage or agent_id not in self.resource_limits:
                return {}

            usage = self.resource_usage[agent_id]
            limits = self.resource_limits[agent_id]

            return {
                "cpu": usage.cpu_percent <= limits.max_cpu_percent,
                "memory": usage.memory_percent <= limits.max_memory_percent,
                "disk": usage.disk_usage <= limits.max_disk_percent
            }

        except Exception as e:
            logger.error(f"Error checking resource limits for agent {agent_id}: {str(e)}")
            return {}

    async def _monitor_agent(self, agent_id: str) -> None:
        """
        Monitor resource usage for an agent.

        Args:
            agent_id (str): Agent identifier
        """
        try:
            while True:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()._asdict()

                usage = ResourceUsage(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_usage=disk.percent,
                    network_io={
                        "bytes_sent": network["bytes_sent"],
                        "bytes_recv": network["bytes_recv"]
                    },
                    timestamp=datetime.now()
                )

                self.resource_usage[agent_id] = usage

                # Check resource limits and log warnings
                if agent_id in self.resource_limits:
                    limits = self.resource_limits[agent_id]
                    if cpu_percent > limits.max_cpu_percent:
                        logger.warning(f"Agent {agent_id} CPU usage ({cpu_percent}%) exceeds limit")
                    if memory.percent > limits.max_memory_percent:
                        logger.warning(f"Agent {agent_id} memory usage ({memory.percent}%) exceeds limit")
                    if disk.percent > limits.max_disk_percent:
                        logger.warning(f"Agent {agent_id} disk usage ({disk.percent}%) exceeds limit")

                await asyncio.sleep(self.monitoring_interval)

        except asyncio.CancelledError:
            logger.info(f"Resource monitoring cancelled for agent {agent_id}")
            raise
        except Exception as e:
            logger.error(f"Error monitoring resources for agent {agent_id}: {str(e)}")
            raise
