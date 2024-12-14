"""
Tests for memory management.
"""
import pytest
import gc

async def test_memory_stats(memory_manager):
    """Test memory statistics collection."""
    stats = await memory_manager.get_memory_stats()
    assert stats.total > 0
    assert stats.available > 0
    assert stats.used > 0
    assert stats.cached >= 0

async def test_object_caching(memory_manager):
    """Test object caching."""
    test_obj = {"data": "test" * 1000}  # Create sizeable object
    success = await memory_manager.cache_object("test_key", test_obj)
    assert success is True


    cached_obj = await memory_manager.get_cached_object("test_key")
    assert cached_obj == test_obj

async def test_weak_reference_caching(memory_manager):
    """Test weak reference caching."""
    class TestObject:
        pass

    test_obj = TestObject()
    await memory_manager.cache_object("test_key", test_obj, weak=True)

    cached_obj = await memory_manager.get_cached_object("test_key")
    assert cached_obj is test_obj

    del test_obj
    gc.collect()

    cached_obj = await memory_manager.get_cached_object("test_key")
    assert cached_obj is None

async def test_cache_cleanup(memory_manager):
    """Test cache cleanup."""
    # Fill cache
    for i in range(1000):
        data = "test" * 1000  # 4KB per entry
        await memory_manager.cache_object(f"key_{i}", data)

    # Verify cleanup
    stats = await memory_manager.get_memory_stats()
    assert stats.cached > 0

    await memory_manager.clear_cache()
    stats = await memory_manager.get_memory_stats()
    assert memory_manager._cache_size == 0
