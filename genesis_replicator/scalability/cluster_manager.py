"""
Cluster Manager implementation for Genesis Replicator Framework.

Handles agent clustering, node management, and cluster coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .load_balancer import LoadBalancer
from .state_manager import StateManager

logger = logging.getLogger(__name__)

@dataclass
class NodeInfo:
    """Information about a node in the cluster."""
    node_id: UUID
    host: str
    port: int
    capabilities: Set[str] = field(default_factory=set)
    load: float = 0.0
    status: str = "active"
    last_heartbeat: float = field(default_factory=lambda: asyncio.get_event_loop().time())

class ClusterManager:
    """Manages agent clustering and node coordination."""

    def __init__(self):
        """Initialize the cluster manager."""
        self.nodes: Dict[UUID, NodeInfo] = {}
        self.load_balancer = LoadBalancer()
        self.state_manager = StateManager()
        self._node_id = uuid4()
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the cluster manager services."""
        logger.info("Starting cluster manager services...")
        await self.load_balancer.start()
        await self.state_manager.start()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Stop the cluster manager services."""
        logger.info("Stopping cluster manager services...")
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        await self.load_balancer.stop()
        await self.state_manager.stop()

    async def register_node(self, host: str, port: int, capabilities: Set[str]) -> UUID:
        """Register a new node in the cluster."""
        node_id = uuid4()
        node_info = NodeInfo(
            node_id=node_id,
            host=host,
            port=port,
            capabilities=capabilities
        )
        self.nodes[node_id] = node_info
        await self.load_balancer.add_node(node_id, node_info)
        logger.info(f"Registered new node: {node_id}")
        return node_id

    async def unregister_node(self, node_id: UUID) -> None:
        """Unregister a node from the cluster."""
        if node_id in self.nodes:
            await self.load_balancer.remove_node(node_id)
            del self.nodes[node_id]
            logger.info(f"Unregistered node: {node_id}")

    async def get_node_info(self, node_id: UUID) -> Optional[NodeInfo]:
        """Get information about a specific node."""
        return self.nodes.get(node_id)

    async def update_node_status(self, node_id: UUID, status: str, load: float) -> None:
        """Update the status and load of a node."""
        if node_id in self.nodes:
            self.nodes[node_id].status = status
            self.nodes[node_id].load = load
            self.nodes[node_id].last_heartbeat = asyncio.get_event_loop().time()
            await self.load_balancer.update_node_load(node_id, load)

    async def get_optimal_node(self, required_capabilities: Set[str]) -> Optional[UUID]:
        """Get the optimal node for a given set of capabilities."""
        return await self.load_balancer.get_optimal_node(required_capabilities)

    async def _heartbeat_loop(self) -> None:
        """Internal heartbeat loop to monitor node health."""
        while True:
            try:
                current_time = asyncio.get_event_loop().time()
                dead_nodes = []

                for node_id, info in self.nodes.items():
                    if current_time - info.last_heartbeat > 30:  # 30 seconds timeout
                        dead_nodes.append(node_id)

                for node_id in dead_nodes:
                    logger.warning(f"Node {node_id} appears to be dead, unregistering")
                    await self.unregister_node(node_id)

                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(1)  # Brief pause on error
