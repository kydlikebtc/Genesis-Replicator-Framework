"""
Pytest fixtures for scalability tests.
"""
import asyncio
import pytest
from typing import AsyncGenerator, Dict, Set
from uuid import UUID, uuid4

from genesis_replicator.scalability.cluster_manager import ClusterManager, NodeInfo
from genesis_replicator.scalability.load_balancer import LoadBalancer
from genesis_replicator.scalability.state_manager import StateManager
from genesis_replicator.scalability.resource_optimizer import ResourceOptimizer

@pytest.fixture
async def cluster_manager() -> AsyncGenerator[ClusterManager, None]:
    """Fixture for ClusterManager instance."""
    manager = ClusterManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.fixture
async def load_balancer() -> AsyncGenerator[LoadBalancer, None]:
    """Fixture for LoadBalancer instance."""
    balancer = LoadBalancer()
    await balancer.start()
    yield balancer
    await balancer.stop()

@pytest.fixture
async def state_manager() -> AsyncGenerator[StateManager, None]:
    """Fixture for StateManager instance."""
    manager = StateManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.fixture
async def resource_optimizer() -> AsyncGenerator[ResourceOptimizer, None]:
    """Fixture for ResourceOptimizer instance."""
    optimizer = ResourceOptimizer()
    await optimizer.start()
    yield optimizer
    await optimizer.stop()

@pytest.fixture
def test_node_info() -> NodeInfo:
    """Fixture for test node information."""
    return NodeInfo(
        node_id=uuid4(),
        host="localhost",
        port=8000,
        capabilities={"compute", "storage"}
    )

@pytest.fixture
def test_nodes() -> Dict[UUID, NodeInfo]:
    """Fixture for multiple test nodes."""
    nodes = {}
    capabilities = [
        {"compute", "storage"},
        {"compute", "memory"},
        {"storage", "network"},
        {"compute", "network"}
    ]

    for i, caps in enumerate(capabilities):
        node_id = uuid4()
        nodes[node_id] = NodeInfo(
            node_id=node_id,
            host=f"node-{i}.local",
            port=8000 + i,
            capabilities=caps
        )

    return nodes
