"""
Tests for the load balancing system.
"""
import pytest
from uuid import UUID

from genesis_replicator.scalability.load_balancer import LoadBalancer

async def test_add_remove_node(load_balancer: LoadBalancer, test_node_info):
    """Test adding and removing nodes."""
    await load_balancer.add_node(test_node_info.node_id, test_node_info)
    await load_balancer.update_node_load(test_node_info.node_id, 0.5)

    optimal_node = await load_balancer.get_optimal_node(test_node_info.capabilities)
    assert optimal_node == test_node_info.node_id

    await load_balancer.remove_node(test_node_info.node_id)
    optimal_node = await load_balancer.get_optimal_node(test_node_info.capabilities)
    assert optimal_node is None

async def test_load_distribution(load_balancer: LoadBalancer, test_nodes):
    """Test load distribution across nodes."""
    # Add all test nodes
    for node_id, node_info in test_nodes.items():
        await load_balancer.add_node(node_id, node_info)

    # Update loads
    loads = [0.2, 0.4, 0.6, 0.8]
    for (node_id, _), load in zip(test_nodes.items(), loads):
        await load_balancer.update_node_load(node_id, load)

    # Test optimal node selection
    optimal_node = await load_balancer.get_optimal_node({"compute"})
    assert optimal_node is not None

    # Should select least loaded node with required capabilities
    cluster_load = await load_balancer.get_cluster_load()
    assert 0.4 < cluster_load < 0.6  # Average load should be around 0.5

async def test_capability_based_selection(load_balancer: LoadBalancer, test_nodes):
    """Test node selection based on capabilities."""
    # Add all test nodes
    for node_id, node_info in test_nodes.items():
        await load_balancer.add_node(node_id, node_info)
        await load_balancer.update_node_load(node_id, 0.5)

    # Test different capability requirements
    compute_node = await load_balancer.get_optimal_node({"compute"})
    assert compute_node is not None
    assert "compute" in test_nodes[compute_node].capabilities

    storage_node = await load_balancer.get_optimal_node({"storage"})
    assert storage_node is not None
    assert "storage" in test_nodes[storage_node].capabilities

    # Test multiple capabilities
    compute_storage_node = await load_balancer.get_optimal_node({"compute", "storage"})
    assert compute_storage_node is not None
    assert "compute" in test_nodes[compute_storage_node].capabilities
    assert "storage" in test_nodes[compute_storage_node].capabilities
