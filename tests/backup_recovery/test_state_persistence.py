"""
Tests for the state persistence manager.
"""
import pytest
import asyncio
import json
from pathlib import Path

async def test_state_save_load(state_manager, sample_state):
    """Test saving and loading state."""
    component = "test_component"

    # Save state
    success = await state_manager.save_state(component, sample_state)
    assert success is True

    # Load state
    loaded_state = await state_manager.load_state(component)
    assert loaded_state == sample_state

async def test_state_cache(state_manager, sample_state):
    """Test state caching behavior."""
    component = "test_component"

    # Save state
    await state_manager.save_state(component, sample_state)

    # Load from cache
    cached_state = await state_manager.load_state(component)
    assert cached_state == sample_state

    # Clear cache
    await state_manager.clear_cache()


    # Load from disk
    disk_state = await state_manager.load_state(component)
    assert disk_state == sample_state

async def test_state_deletion(state_manager, sample_state):
    """Test state deletion."""
    component = "test_component"

    # Save and verify state
    await state_manager.save_state(component, sample_state)
    assert await state_manager.load_state(component) == sample_state

    # Delete state
    success = await state_manager.delete_state(component)
    assert success is True

    # Verify deletion
    assert await state_manager.load_state(component) is None

async def test_list_components(state_manager, sample_state):
    """Test listing components with saved state."""
    components = ["component_a", "component_b", "component_c"]

    # Save state for multiple components
    for component in components:
        await state_manager.save_state(component, sample_state)

    # List components
    saved_components = await state_manager.list_components()
    assert set(saved_components) == set(components)

async def test_concurrent_state_access(state_manager, sample_state):
    """Test concurrent state access."""
    component = "test_component"

    # Concurrent save operations
    tasks = []
    for i in range(5):
        state = {**sample_state, "index": i}
        tasks.append(state_manager.save_state(component, state))

    await asyncio.gather(*tasks)

    # Verify final state
    final_state = await state_manager.load_state(component)
    assert final_state is not None
