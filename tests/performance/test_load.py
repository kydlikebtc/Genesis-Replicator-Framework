"""
Load testing and performance benchmarking.
"""
import pytest
import asyncio
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import statistics

from genesis_replicator.ai_module.model_registry import ModelRegistry
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.event_processing.event_batcher import EventBatcher
from genesis_replicator.caching.cache_manager import CacheManager
from genesis_replicator.monitoring.metrics_collector import MetricsCollector

@pytest.fixture
async def setup_components():
    """Set up components for load testing."""
    model_registry = ModelRegistry()
    chain_manager = ChainManager()
    event_batcher = EventBatcher()
    cache_manager = CacheManager()
    metrics_collector = MetricsCollector()

    await model_registry.initialize()
    await chain_manager.initialize()
    await event_batcher.start()
    await cache_manager.start()
    await metrics_collector.start()

    yield {
        "model_registry": model_registry,
        "chain_manager": chain_manager,
        "event_batcher": event_batcher,
        "cache_manager": cache_manager,
        "metrics_collector": metrics_collector
    }

    # Cleanup
    await model_registry.cleanup()
    await chain_manager.cleanup()
    await event_batcher.stop()
    await cache_manager.stop()
    await metrics_collector.stop()

async def generate_load(
    components: Dict[str, Any],
    request_count: int,
    concurrent_requests: int
) -> List[Dict[str, Any]]:
    """Generate load for testing."""
    metrics = []
    semaphore = asyncio.Semaphore(concurrent_requests)

    async def single_request():
        async with semaphore:
            start_time = time.time()
            try:
                # AI Model request
                await components["model_registry"].generate_text(
                    provider="test_provider",
                    prompt="Test prompt",
                    max_tokens=100
                )

                # Blockchain transaction
                await components["chain_manager"].send_transaction(
                    chain="test_chain",
                    to_address="0x123",
                    value=1000
                )

                # Event processing
                await components["event_batcher"].add_event(
                    "test_event",
                    {"data": "test"}
                )

                # Cache operation
                await components["cache_manager"].set(
                    "test_key",
                    "test_value"
                )

                end_time = time.time()
                return {
                    "success": True,
                    "latency": end_time - start_time
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "success": False,
                    "latency": end_time - start_time,
                    "error": str(e)
                }

    tasks = [single_request() for _ in range(request_count)]
    results = await asyncio.gather(*tasks)
    return results

def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance metrics."""
    latencies = [r["latency"] for r in results]
    success_count = sum(1 for r in results if r["success"])

    return {
        "total_requests": len(results),
        "successful_requests": success_count,
        "success_rate": success_count / len(results),
        "avg_latency": statistics.mean(latencies),
        "median_latency": statistics.median(latencies),
        "p95_latency": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
        "p99_latency": statistics.quantiles(latencies, n=100)[98],  # 99th percentile
        "min_latency": min(latencies),
        "max_latency": max(latencies)
    }

@pytest.mark.load_test
@pytest.mark.asyncio
async def test_system_load(setup_components):
    """Test system under various load conditions."""
    load_scenarios = [
        {"requests": 100, "concurrency": 10},
        {"requests": 500, "concurrency": 50},
        {"requests": 1000, "concurrency": 100}
    ]

    for scenario in load_scenarios:
        # Run load test
        results = await generate_load(
            setup_components,
            scenario["requests"],
            scenario["concurrency"]
        )

        # Calculate metrics
        metrics = calculate_metrics(results)

        # Assert performance requirements
        assert metrics["success_rate"] >= 0.95  # 95% success rate
        assert metrics["p95_latency"] <= 2.0    # 2 second p95 latency
        assert metrics["median_latency"] <= 1.0  # 1 second median latency

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_component_benchmarks(setup_components):
    """Benchmark individual components."""
    components = setup_components


    # AI Model benchmarks
    model_start = time.time()
    for _ in range(100):
        await components["model_registry"].generate_text(
            provider="test_provider",
            prompt="Benchmark test",
            max_tokens=50
        )
    model_time = time.time() - model_start
    assert model_time / 100 <= 0.5  # 500ms average

    # Blockchain benchmarks
    chain_start = time.time()
    for _ in range(100):
        await components["chain_manager"].get_transaction_status(
            "test_tx_hash"
        )
    chain_time = time.time() - chain_start
    assert chain_time / 100 <= 0.2  # 200ms average

    # Event processing benchmarks
    event_start = time.time()
    for i in range(1000):
        await components["event_batcher"].add_event(
            "benchmark_event",
            {"id": i}
        )
    event_time = time.time() - event_start
    assert event_time / 1000 <= 0.01  # 10ms average

    # Cache benchmarks
    cache_start = time.time()
    for i in range(10000):
        await components["cache_manager"].set(
            f"bench_key_{i}",
            f"bench_value_{i}"
        )
    cache_time = time.time() - cache_start
    assert cache_time / 10000 <= 0.001  # 1ms average

@pytest.mark.scalability
@pytest.mark.asyncio
async def test_system_scalability(setup_components):
    """Test system scalability under increasing load."""
    initial_requests = 100
    scale_factor = 2
    max_iterations = 5

    for i in range(max_iterations):
        requests = initial_requests * (scale_factor ** i)
        concurrency = max(10, requests // 10)

        # Run scaled load test
        results = await generate_load(
            setup_components,
            requests,
            concurrency
        )

        metrics = calculate_metrics(results)

        # Verify scalability requirements
        assert metrics["success_rate"] >= 0.90  # Allow slightly lower success rate under extreme load
        assert metrics["p99_latency"] <= 5.0    # 5 second p99 latency under load

        # Monitor resource usage
        resource_metrics = await setup_components["metrics_collector"].get_metrics()
        assert resource_metrics["cpu_usage"] <= 80  # CPU usage under 80%
        assert resource_metrics["memory_usage"] <= 85  # Memory usage under 85%
