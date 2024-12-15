"""
Tests for event batcher.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from genesis_replicator.event_processing.event_batcher import EventBatcher, EventBatch

@pytest.fixture
async def event_batcher():
    batcher = EventBatcher(
        max_batch_size=5,
        max_wait_time=0.1,
        min_batch_size=2
    )
    yield batcher
    await batcher.stop()

@pytest.mark.asyncio
async def test_event_batching(event_batcher):
    # Create mock processor
    processed_batches = []
    async def processor(batch: EventBatch):
        processed_batches.append(batch)

    # Register processor
    await event_batcher.register_processor("test_event", processor)

    # Add events
    for i in range(7):
        await event_batcher.add_event(
            "test_event",
            {"id": i},
            priority=1,
            tags={"tag1"}
        )

    # Wait for processing
    await asyncio.sleep(0.2)

    # Verify batches
    assert len(processed_batches) == 2
    assert processed_batches[0].size == 5  # First batch (max size)
    assert processed_batches[1].size == 2  # Second batch (remaining)

@pytest.mark.asyncio
async def test_batch_timing(event_batcher):
    processed_batches = []
    async def processor(batch: EventBatch):
        processed_batches.append(batch)

    await event_batcher.register_processor("test_event", processor)

    # Add events below max_batch_size
    for i in range(3):
        await event_batcher.add_event("test_event", {"id": i})

    # Wait for max_wait_time
    await asyncio.sleep(0.2)

    # Verify batch was processed due to timeout
    assert len(processed_batches) == 1
    assert processed_batches[0].size == 3

@pytest.mark.asyncio
async def test_multiple_event_types(event_batcher):
    type1_batches = []
    type2_batches = []

    async def processor1(batch: EventBatch):
        type1_batches.append(batch)

    async def processor2(batch: EventBatch):
        type2_batches.append(batch)

    await event_batcher.register_processor("type1", processor1)
    await event_batcher.register_processor("type2", processor2)

    # Add events of different types
    for i in range(3):
        await event_batcher.add_event("type1", {"id": i})
        await event_batcher.add_event("type2", {"id": i})

    # Wait for processing
    await asyncio.sleep(0.2)

    # Verify separate processing
    assert len(type1_batches) == 1
    assert len(type2_batches) == 1

@pytest.mark.asyncio
async def test_batch_stats(event_batcher):
    async def processor(batch: EventBatch):
        pass

    await event_batcher.register_processor("test_event", processor)

    # Add some events
    for i in range(3):
        await event_batcher.add_event("test_event", {"id": i})

    # Get stats
    stats = await event_batcher.get_batch_stats()

    assert "total_batches" in stats
    assert "pending_events" in stats
    assert "event_types" in stats
    assert "test_event" in stats["event_types"]
