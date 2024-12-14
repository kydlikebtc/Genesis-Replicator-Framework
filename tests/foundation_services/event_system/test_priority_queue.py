"""
Tests for the Priority Queue implementation.
"""
import pytest
import asyncio
from genesis_replicator.foundation_services.event_system.priority_queue import PriorityQueue

@pytest.fixture
def priority_queue():
    """Create a new PriorityQueue instance for testing."""
    return PriorityQueue()

@pytest.mark.asyncio
async def test_queue_ordering(priority_queue):
    """Test that items are dequeued in priority order."""
    await priority_queue.put("low", 3)
    await priority_queue.put("high", 1)
    await priority_queue.put("medium", 2)


    assert await priority_queue.get() == "high"
    assert await priority_queue.get() == "medium"
    assert await priority_queue.get() == "low"

@pytest.mark.asyncio
async def test_queue_empty(priority_queue):
    """Test behavior when queue is empty."""
    with pytest.raises(asyncio.QueueEmpty):
        priority_queue.get_nowait()

@pytest.mark.asyncio
async def test_queue_size(priority_queue):
    """Test queue size tracking."""
    assert priority_queue.empty()
    assert priority_queue.qsize() == 0

    await priority_queue.put("item1", 1)
    await priority_queue.put("item2", 2)

    assert not priority_queue.empty()
    assert priority_queue.qsize() == 2

@pytest.mark.asyncio
async def test_same_priority_ordering(priority_queue):
    """Test that items with same priority maintain FIFO order."""
    await priority_queue.put("first", 1)
    await priority_queue.put("second", 1)
    await priority_queue.put("third", 1)

    assert await priority_queue.get() == "first"
    assert await priority_queue.get() == "second"
    assert await priority_queue.get() == "third"

@pytest.mark.asyncio
async def test_priority_boundaries(priority_queue):
    """Test queue behavior with extreme priority values."""
    await priority_queue.put("lowest", float('inf'))
    await priority_queue.put("highest", float('-inf'))
    await priority_queue.put("normal", 0)

    assert await priority_queue.get() == "highest"
    assert await priority_queue.get() == "normal"
    assert await priority_queue.get() == "lowest"

@pytest.mark.asyncio
async def test_concurrent_operations(priority_queue):
    """Test concurrent put and get operations."""
    async def producer():
        await priority_queue.put("item1", 1)
        await priority_queue.put("item2", 2)
        await priority_queue.put("item3", 3)

    async def consumer():
        items = []
        for _ in range(3):
            item = await priority_queue.get()
            items.append(item)
        return items

    producer_task = asyncio.create_task(producer())
    consumer_task = asyncio.create_task(consumer())

    await producer_task
    items = await consumer_task

    assert items == ["item1", "item2", "item3"]
