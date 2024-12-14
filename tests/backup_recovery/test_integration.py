"""
Integration tests for backup and recovery system.
"""
import pytest
import asyncio
from pathlib import Path
from genesis_replicator.backup_recovery.recovery_manager import RecoveryStatus

async def test_backup_restore_workflow(
    backup_manager,
    state_manager,
    recovery_manager,
    sample_state
):
    """Test complete backup and restore workflow."""
    # Save initial state
    component = "test_component"
    await state_manager.save_state(component, sample_state)

    # Create backup
    backup_id = await backup_manager.create_backup(["state"])

    # Delete state
    await state_manager.delete_state(component)
    assert await state_manager.load_state(component) is None

    # Register recovery procedure
    async def restore_procedure():
        return await backup_manager.restore_backup(backup_id)

    recovery_manager.register_procedure(
        name="restore_state",
        handler=restore_procedure
    )

    # Execute recovery
    success = await recovery_manager.execute_procedure("restore_state")
    assert success is True


    # Verify restored state
    restored_state = await state_manager.load_state(component)
    assert restored_state == sample_state

async def test_concurrent_operations(
    backup_manager,
    state_manager,
    recovery_manager,
    sample_state
):
    """Test concurrent backup and recovery operations."""
    components = ["component_a", "component_b"]

    # Save states
    for component in components:
        await state_manager.save_state(component, sample_state)

    # Concurrent backup creation
    backup_tasks = []
    for _ in range(3):
        backup_tasks.append(backup_manager.create_backup(components))

    backup_ids = await asyncio.gather(*backup_tasks)
    assert len(backup_ids) == 3

    # Concurrent state modifications
    mod_tasks = []
    for component in components:
        modified_state = {**sample_state, "modified": True}
        mod_tasks.append(state_manager.save_state(component, modified_state))

    await asyncio.gather(*mod_tasks)

    # Concurrent restore operations
    restore_tasks = []
    for backup_id in backup_ids:
        restore_tasks.append(backup_manager.restore_backup(backup_id))

    results = await asyncio.gather(*restore_tasks)
    assert all(results)

async def test_recovery_error_handling(
    backup_manager,
    state_manager,
    recovery_manager,
    sample_state
):
    """Test error handling in recovery procedures."""
    # Create initial backup
    component = "test_component"
    await state_manager.save_state(component, sample_state)
    backup_id = await backup_manager.create_backup(["state"])

    # Register failing procedure
    async def failing_procedure():
        raise RuntimeError("Simulated failure")

    recovery_manager.register_procedure(
        name="failing_proc",
        handler=failing_procedure
    )

    # Register recovery procedure
    async def recovery_procedure():
        return await backup_manager.restore_backup(backup_id)

    recovery_manager.register_procedure(
        name="recovery_proc",
        handler=recovery_procedure,
        dependencies=["failing_proc"]
    )

    # Execute recovery chain
    success = await recovery_manager.execute_all()
    assert not success

    # Verify procedure states
    assert recovery_manager.get_procedure_status("failing_proc") == RecoveryStatus.FAILED
    assert recovery_manager.get_procedure_status("recovery_proc") == RecoveryStatus.PENDING
