"""
Tests for the state management system.
"""
import pytest
from uuid import uuid4

from genesis_replicator.scalability.state_manager import StateManager

async def test_state_operations(state_manager: StateManager):
    """Test basic state operations."""
    node_id = uuid4()
    test_key = "test_key"
    test_value = {"data": "test"}

    # Set state
    await state_manager.set_state(test_key, test_value, node_id)

    # Get state
    stored_value = await state_manager.get_state(test_key)
    assert stored_value == test_value

    # Check version
    version = await state_manager.get_version(test_key)
    assert version == 1

    # Update state
    new_value = {"data": "updated"}
    await state_manager.set_state(test_key, new_value, node_id)
    assert await state_manager.get_version(test_key) == 2


async def test_state_consistency(state_manager: StateManager):
    """Test state consistency verification."""
    node_id = uuid4()
    test_key = "test_key"
    test_value = {"data": "test"}

    await state_manager.set_state(test_key, test_value, node_id)

    # Verify consistency with same value
    assert await state_manager.verify_consistency(test_key, test_value)

    # Verify consistency with different value
    different_value = {"data": "different"}
    assert not await state_manager.verify_consistency(test_key, different_value)

async def test_replica_management(state_manager: StateManager):
    """Test replica management."""
    node_id = uuid4()
    test_key = "test_key"
    test_value = {"data": "test"}

    # Set state with replica
    await state_manager.set_state(test_key, test_value, node_id)

    # Remove replica
    await state_manager.remove_replica(node_id)

    # State should still exist
    assert await state_manager.get_state(test_key) == test_value
