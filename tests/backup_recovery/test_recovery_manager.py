"""
Tests for the recovery manager.
"""
import pytest
import asyncio
from genesis_replicator.backup_recovery.recovery_manager import RecoveryStatus

async def test_procedure_registration(recovery_manager, mock_recovery_procedure):
    """Test recovery procedure registration."""
    recovery_manager.register_procedure(
        name="test_procedure",
        handler=mock_recovery_procedure
    )

    assert "test_procedure" in recovery_manager._procedures
    assert recovery_manager.get_procedure_status("test_procedure") == RecoveryStatus.PENDING

async def test_procedure_execution(recovery_manager, mock_recovery_procedure):
    """Test executing a recovery procedure."""
    recovery_manager.register_procedure(
        name="test_procedure",
        handler=mock_recovery_procedure
    )

    success = await recovery_manager.execute_procedure("test_procedure")
    assert success is True
    assert recovery_manager.get_procedure_status("test_procedure") == RecoveryStatus.COMPLETED

async def test_procedure_dependencies(recovery_manager):
    """Test procedure dependency resolution."""
    async def proc_a():
        await asyncio.sleep(0.1)
        return True

    async def proc_b():
        await asyncio.sleep(0.1)
        return True

    recovery_manager.register_procedure(name="proc_a", handler=proc_a)
    recovery_manager.register_procedure(
        name="proc_b",
        handler=proc_b,
        dependencies=["proc_a"]
    )

    # Execute with dependencies
    success = await recovery_manager.execute_all()
    assert success is True

    status_a = recovery_manager.get_procedure_status("proc_a")
    status_b = recovery_manager.get_procedure_status("proc_b")
    assert status_a == RecoveryStatus.COMPLETED
    assert status_b == RecoveryStatus.COMPLETED

async def test_procedure_timeout(recovery_manager):
    """Test procedure timeout handling."""
    async def slow_procedure():
        await asyncio.sleep(2)
        return True

    recovery_manager.register_procedure(
        name="slow_proc",
        handler=slow_procedure,
        timeout=1
    )

    success = await recovery_manager.execute_procedure("slow_proc")
    assert success is False
    assert recovery_manager.get_procedure_status("slow_proc") == RecoveryStatus.FAILED

async def test_circular_dependencies(recovery_manager):
    """Test circular dependency detection."""
    async def mock_proc():
        return True

    recovery_manager.register_procedure(
        name="proc_a",
        handler=mock_proc,
        dependencies=["proc_b"]
    )
    recovery_manager.register_procedure(
        name="proc_b",
        handler=mock_proc,
        dependencies=["proc_a"]
    )

    with pytest.raises(ValueError, match="Circular dependency detected"):
        await recovery_manager.execute_all()
