"""
Tests for the cluster management system.
"""
import asyncio
import pytest
from uuid import UUID
from typing import Dict, Set

from genesis_replicator.scalability.cluster_manager import ClusterManager, NodeInfo

async def test_register_node(cluster_manager: ClusterManager, test_node_info: NodeInfo):
    """Test node registration."""
    node_id = await cluster_manager.register_node(
        test_node_info.host,
        test_node_info.port,
        test_node_info.capabilities
    )
    assert isinstance(node_id, UUID)

    node_info = await cluster_manager.get_node_info(node_id)
    assert node_info is not None
    assert node_info.host == test_node_info.host
    assert node_info.port == test_node_info.port
    assert node_info.capabilities == test_node_info.capabilities

async def test_unregister_node(cluster_manager: ClusterManager, test_node_info: NodeInfo):
    """Test node unregistration."""
    node_id = await cluster_manager.register_node(
        test_node_info.host,
        test_node_info.port,
        test_node_info.capabilities
    )

    await cluster_manager.unregister_node(node_id)
    node_info = await cluster_manager.get_node_info(node_id)
    assert node_info is None

async def test_update_node_status(cluster_manager: ClusterManager, test_node_info: NodeInfo):
    """Test node status updates."""
    node_id = await cluster_manager.register_node(
        test_node_info.host,
        test_node_info.port,
        test_node_info.capabilities
    )

    await cluster_manager.update_node_status(node_id, "busy", 0.8)
    node_info = await cluster_manager.get_node_info(node_id)
    assert node_info.status == "busy"
    assert node_info.load == 0.8

async def test_heartbeat_mechanism(cluster_manager: ClusterManager, test_nodes: Dict[UUID, NodeInfo]):
    """Test heartbeat mechanism and dead node detection."""
    registered_nodes = []

    # Register multiple nodes
    for node_info in test_nodes.values():
        node_id = await cluster_manager.register_node(
            node_info.host,
            node_info.port,
            node_info.capabilities
        )
        registered_nodes.append(node_id)

    # Update status for some nodes
    for node_id in registered_nodes[:-1]:
        await cluster_manager.update_node_status(node_id, "active", 0.5)

    # Wait for heartbeat check
    await asyncio.sleep(35)  # Longer than heartbeat timeout

    # Check if last node was removed
    assert await cluster_manager.get_node_info(registered_nodes[-1]) is None

    # Other nodes should still be present
    for node_id in registered_nodes[:-1]:
        assert await cluster_manager.get_node_info(node_id) is not None

async def test_optimal_node_selection(cluster_manager: ClusterManager, test_nodes: Dict[UUID, NodeInfo]):
    """Test optimal node selection based on capabilities and load."""
    registered_nodes = []

    # Register multiple nodes
    for node_info in test_nodes.values():
        node_id = await cluster_manager.register_node(
            node_info.host,
            node_info.port,
            node_info.capabilities
        )
        registered_nodes.append(node_id)

    # Update different loads
    loads = [0.8, 0.3, 0.6, 0.9]
    for node_id, load in zip(registered_nodes, loads):
        await cluster_manager.update_node_status(node_id, "active", load)

    # Test node selection
    optimal_node = await cluster_manager.get_optimal_node({"compute"})
    assert optimal_node in registered_nodes

    node_info = await cluster_manager.get_node_info(optimal_node)
    assert "compute" in node_info.capabilities
    assert node_info.load <= 0.8  # Should prefer less loaded nodes
