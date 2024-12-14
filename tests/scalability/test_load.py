"""
Load testing for the scalability system.
"""
import asyncio
import pytest
from typing import Dict, List
from uuid import UUID, uuid4
import time

from genesis_replicator.scalability.cluster_manager import ClusterManager, NodeInfo
from genesis_replicator.scalability.load_balancer import LoadBalancer
from genesis_replicator.scalability.state_manager import StateManager

async def test_concurrent_node_operations(cluster_manager: ClusterManager):
    """Test handling of concurrent node registrations and updates."""
    node_count = 100
    nodes = []

    async def register_and_update():
        node_id = await cluster_manager.register_node(
            f"test-{uuid4()}.local",
            8000,
            {"compute", "storage"}
        )
        nodes.append(node_id)
        for _ in range(5):  # Multiple updates per node
            await cluster_manager.update_node_status(
                node_id,
                "active",
                0.5
            )
            await asyncio.sleep(0.01)

    # Create multiple concurrent registration tasks
    tasks = [register_and_update() for _ in range(node_count)]
    await asyncio.gather(*tasks)

    # Verify all nodes were registered
    assert len(nodes) == node_count
    for node_id in nodes:
        info = await cluster_manager.get_node_info(node_id)
        assert info is not None


async def test_state_replication_under_load(state_manager: StateManager):
    """Test state management under heavy load."""
    operation_count = 1000
    node_id = uuid4()

    async def state_operation(i: int):
        key = f"test_key_{i}"
        value = {"data": f"test_value_{i}"}
        await state_manager.set_state(key, value, node_id)
        stored_value = await state_manager.get_state(key)
        assert stored_value == value
        assert await state_manager.verify_consistency(key, value)

    # Create multiple concurrent state operations
    start_time = time.time()
    tasks = [state_operation(i) for i in range(operation_count)]
    await asyncio.gather(*tasks)
    end_time = time.time()

    # Calculate and log performance metrics
    duration = end_time - start_time
    ops_per_second = operation_count / duration
    print(f"State operations per second: {ops_per_second:.2f}")

async def test_load_balancer_performance(
    load_balancer: LoadBalancer,
    test_nodes: Dict[UUID, NodeInfo]
):
    """Test load balancer performance under high request volume."""
    request_count = 10000

    # Register test nodes
    for node_id, node_info in test_nodes.items():
        await load_balancer.add_node(node_id, node_info)
        await load_balancer.update_node_load(node_id, 0.5)

    async def request_optimal_node():
        return await load_balancer.get_optimal_node({"compute"})

    # Measure performance under load
    start_time = time.time()
    tasks = [request_optimal_node() for _ in range(request_count)]
    results = await asyncio.gather(*tasks)
    end_time = time.time()

    # Verify results and calculate metrics
    assert all(node_id is not None for node_id in results)
    duration = end_time - start_time
    requests_per_second = request_count / duration
    print(f"Load balancer requests per second: {requests_per_second:.2f}")

@pytest.mark.benchmark
async def test_system_scalability_benchmark(
    cluster_manager: ClusterManager,
    load_balancer: LoadBalancer,
    state_manager: StateManager
):
    """Benchmark overall system scalability."""
    node_count = 50
    operations_per_node = 100
    total_operations = node_count * operations_per_node

    # Setup initial nodes
    nodes = []
    for i in range(node_count):
        node_id = await cluster_manager.register_node(
            f"bench-node-{i}.local",
            8000 + i,
            {"compute", "storage"}
        )
        nodes.append(node_id)
        await cluster_manager.update_node_status(node_id, "active", 0.5)

    async def mixed_operations(node_id: UUID, operation_count: int):
        for i in range(operation_count):
            # Mix of different operations
            await load_balancer.get_optimal_node({"compute"})
            await state_manager.set_state(
                f"bench_key_{node_id}_{i}",
                {"data": f"value_{i}"},
                node_id
            )
            await cluster_manager.update_node_status(
                node_id,
                "active",
                0.5 + (i % 5) * 0.1
            )

    # Run benchmark
    start_time = time.time()
    tasks = [
        mixed_operations(node_id, operations_per_node)
        for node_id in nodes
    ]
    await asyncio.gather(*tasks)
    end_time = time.time()

    # Calculate and report metrics
    duration = end_time - start_time
    ops_per_second = total_operations / duration
    print(f"System benchmark results:")
    print(f"Total operations: {total_operations}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Operations per second: {ops_per_second:.2f}")
    print(f"Average operation time: {(duration / total_operations) * 1000:.2f} ms")
