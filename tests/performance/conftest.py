"""
Test fixtures for performance tests.
"""
import pytest
import asyncio
from genesis_replicator.performance.memory_manager import MemoryManager
from genesis_replicator.performance.resource_optimizer import ResourceOptimizer
from genesis_replicator.performance.event_optimizer import EventOptimizer

@pytest.fixture
async def memory_manager():
    """Provide configured memory manager."""
    return MemoryManager(
        max_cache_size=1024 * 1024,  # 1MB for testing
        gc_threshold=0.8
    )

@pytest.fixture
async def resource_optimizer():
    """Provide configured resource optimizer."""
    return ResourceOptimizer(
        cpu_threshold=70.0,
        memory_threshold=75.0,
        disk_threshold=80.0
    )

@pytest.fixture
async def event_optimizer():
    """Provide configured event optimizer."""
    return EventOptimizer(
        max_batch_size=10,
        max_queue_size=100,
        processing_timeout=1.0
    )

@pytest.fixture
async def sample_event_processor():
    """Provide sample event processor."""
    async def processor(event_data):
        await asyncio.sleep(0.1)
        return event_data
    return processor
