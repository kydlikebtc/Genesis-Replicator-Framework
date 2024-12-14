"""
Load Balancer implementation for Genesis Replicator Framework.

Handles load distribution and balancing across cluster nodes.
"""

import asyncio
import logging
from typing import Dict, Optional, Set
from uuid import UUID
import heapq

logger = logging.getLogger(__name__)

class LoadBalancer:
    """Manages load distribution across cluster nodes."""

    def __init__(self):
        """Initialize the load balancer."""
        self._node_loads: Dict[UUID, float] = {}
        self._node_capabilities: Dict[UUID, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the load balancer service."""
        logger.info("Starting load balancer service...")

    async def stop(self) -> None:
        """Stop the load balancer service."""
        logger.info("Stopping load balancer service...")

    async def add_node(self, node_id: UUID, node_info) -> None:
        """Add a new node to the load balancer."""
        async with self._lock:
            self._node_loads[node_id] = 0.0
            self._node_capabilities[node_id] = node_info.capabilities
            logger.info(f"Added node {node_id} to load balancer")

    async def remove_node(self, node_id: UUID) -> None:
        """Remove a node from the load balancer."""
        async with self._lock:
            self._node_loads.pop(node_id, None)
            self._node_capabilities.pop(node_id, None)
            logger.info(f"Removed node {node_id} from load balancer")

    async def update_node_load(self, node_id: UUID, load: float) -> None:
        """Update the load value for a node."""
        async with self._lock:
            if node_id in self._node_loads:
                self._node_loads[node_id] = load
                logger.debug(f"Updated load for node {node_id}: {load}")

    async def get_optimal_node(self, required_capabilities: Set[str]) -> Optional[UUID]:
        """Get the optimal node based on load and capabilities."""
        async with self._lock:
            eligible_nodes = []

            for node_id, capabilities in self._node_capabilities.items():
                if required_capabilities.issubset(capabilities):
                    load = self._node_loads.get(node_id, float('inf'))
                    heapq.heappush(eligible_nodes, (load, node_id))

            if eligible_nodes:
                _, node_id = heapq.heappop(eligible_nodes)
                logger.debug(f"Selected optimal node {node_id}")
                return node_id

            logger.warning("No eligible nodes found for required capabilities")
            return None

    async def get_cluster_load(self) -> float:
        """Get the average load across all nodes."""
        async with self._lock:
            if not self._node_loads:
                return 0.0
            return sum(self._node_loads.values()) / len(self._node_loads)
