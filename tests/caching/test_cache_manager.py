"""
Tests for cache manager.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from genesis_replicator.caching.cache_manager import CacheManager

@pytest.fixture
async def cache_manager():
    manager = CacheManager(
        max_size=10,
        default_ttl=60,
        cleanup_interval=1
    )
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_cache_basic_operations(cache_manager):
    # Test set and get
    await cache_manager.set("key1", "value1")
    value = await cache_manager.get("key1")
    assert value == "value1"

    # Test default value
    value = await cache_manager.get("nonexistent", "default")
    assert value == "default"

@pytest.mark.asyncio
async def test_cache_ttl(cache_manager):
    # Test TTL expiration
    await cache_manager.set("key1", "value1", ttl=1)
    value = await cache_manager.get("key1")
    assert value == "value1"

    # Wait for expiration
    await asyncio.sleep(2)
    value = await cache_manager.get("key1")
    assert value is None

@pytest.mark.asyncio
async def test_cache_tags(cache_manager):
    # Test tag-based operations
    await cache_manager.set("key1", "value1", tags={"tag1"})
    await cache_manager.set("key2", "value2", tags={"tag1"})
    await cache_manager.set("key3", "value3", tags={"tag2"})

    # Invalidate by tag
    await cache_manager.invalidate_by_tag("tag1")

    assert await cache_manager.get("key1") is None
    assert await cache_manager.get("key2") is None
    assert await cache_manager.get("key3") == "value3"

@pytest.mark.asyncio
async def test_cache_size_limit(cache_manager):
    # Test size limit enforcement
    for i in range(15):  # More than max_size
        await cache_manager.set(f"key{i}", f"value{i}")

    # Verify size limit
    stats = await cache_manager.get_stats()
    assert stats["total_entries"] <= 10

@pytest.mark.asyncio
async def test_cache_stats(cache_manager):
    # Generate some cache activity
    await cache_manager.set("key1", "value1", tags={"tag1"})
    await cache_manager.get("key1")
    await cache_manager.get("key1")

    # Get stats
    stats = await cache_manager.get_stats()
    assert "total_entries" in stats
    assert "access_stats" in stats
    assert stats["total_tags"] == 1
    assert stats["access_stats"]["total_hits"] == 2

@pytest.mark.asyncio
async def test_cache_cleanup(cache_manager):
    # Add entries with short TTL
    await cache_manager.set("key1", "value1", ttl=1)
    await cache_manager.set("key2", "value2", ttl=1)

    # Wait for cleanup
    await asyncio.sleep(2)

    # Verify cleanup
    stats = await cache_manager.get_stats()
    assert stats["expired_entries"] == 0
    assert await cache_manager.get("key1") is None
    assert await cache_manager.get("key2") is None

@pytest.mark.asyncio
async def test_cache_concurrent_access():
    # Test concurrent access
    manager = CacheManager(max_size=100)
    await manager.start()

    async def worker(i: int):
        await manager.set(f"key{i}", f"value{i}")
        await manager.get(f"key{i}")

    # Run concurrent operations
    tasks = [worker(i) for i in range(50)]
    await asyncio.gather(*tasks)

    # Verify results
    stats = await manager.get_stats()
    assert stats["total_entries"] == 50

    await manager.stop()
