"""
Integration tests for the scalability system components.
"""
import asyncio
import pytest
from typing import Dict, Set
from uuid import UUID

from genesis_replicator.scalability.cluster_manager import ClusterManager, NodeInfo
from genesis_replicator.scalability.load_balancer import LoadBalancer
from genesis_replicator.scalability.state_manager import StateManager
from genesis_replicator.scalability.resource_optimizer import ResourceOptimizer

async def test_full_scaling_workflow(
    cluster_manager: ClusterManager,
    load_balancer: LoadBalancer,
    state_manager: StateManager,
    resource_optimizer: ResourceOptimizer,
    test_nodes: Dict[UUID, NodeInfo]
):
    """Test complete scaling workflow with all components."""
    # Register nodes and verify cluster formation
    registered_nodes = []
    for node_info in test_nodes.values():
        node_id = await cluster_manager.register_node(
            node_info.host,
            node_info.port,
            node_info.capabilities
        )
        registered_nodes.append(node_id)

    # Simulate load changes and verify balancing
    loads = [0.3, 0.5, 0.7, 0.9]
    for node_id, load in zip(registered_nodes, loads):
        await cluster_manager.update_node_status(node_id, "active", load)

    # Verify load balancer response
    optimal_node = await cluster_manager.get_optimal_node({"compute"})
    assert optimal_node in registered_nodes
    node_info = await cluster_manager.get_node_info(optimal_node)
    assert node_info.load <= 0.7  # Should prefer less loaded nodes

    # Test state replication
    test_state = {"key": "value"}
    await state_manager.set_state("test_key", test_state, optimal_node)
    assert await state_manager.get_state("test_key") == test_state

    # Verify resource optimization
    metrics = await resource_optimizer.get_current_metrics()
    recommendations = await resource_optimizer.get_optimization_recommendations()
    assert isinstance(recommendations, dict)

async def test_failover_recovery(
    cluster_manager: ClusterManager,
    state_manager: StateManager,
    test_nodes: Dict[UUID, NodeInfo]
):
    """Test system recovery after node failures."""
    # Register initial nodes
    registered_nodes = []
    for node_info in test_nodes.values():
        node_id = await cluster_manager.register_node(
            node_info.host,
            node_info.port,
            node_info.capabilities
        )
        registered_nodes.append(node_id)

    # Set up initial state
    test_states = {
        f"key_{i}": {"data": f"value_{i}"}
        for i in range(len(registered_nodes))
    }

    # Distribute state across nodes
    for node_id, (key, value) in zip(registered_nodes, test_states.items()):
        await state_manager.set_state(key, value, node_id)

    # Simulate node failure
    failed_node = registered_nodes[0]
    await cluster_manager.unregister_node(failed_node)

    # Verify state preservation
    for key, value in test_states.items():
        assert await state_manager.get_state(key) == value

    # Verify cluster rebalancing
    remaining_nodes = registered_nodes[1:]
    for node_id in remaining_nodes:
        assert await cluster_manager.get_node_info(node_id) is not None
