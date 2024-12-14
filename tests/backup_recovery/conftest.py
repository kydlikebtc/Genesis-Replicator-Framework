"""
Test fixtures for backup and recovery tests.
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from genesis_replicator.backup_recovery.backup_manager import BackupManager
from genesis_replicator.backup_recovery.state_persistence import StatePersistenceManager
from genesis_replicator.backup_recovery.recovery_manager import RecoveryManager

@pytest.fixture
async def backup_dir():
    """Provide temporary backup directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
async def state_dir():
    """Provide temporary state directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
async def backup_manager(backup_dir):
    """Provide configured backup manager."""
    manager = BackupManager(backup_dir=backup_dir)
    yield manager

@pytest.fixture
async def state_manager(state_dir):
    """Provide configured state persistence manager."""
    manager = StatePersistenceManager(state_dir=state_dir)
    yield manager

@pytest.fixture
async def recovery_manager():
    """Provide configured recovery manager."""
    manager = RecoveryManager()
    yield manager

@pytest.fixture
async def sample_state():
    """Provide sample state data."""
    return {
        "component_a": {"status": "active", "uptime": 3600},
        "component_b": {"status": "standby", "connections": 5}
    }

@pytest.fixture
async def mock_recovery_procedure():
    """Provide mock recovery procedure."""
    async def procedure():
        await asyncio.sleep(0.1)
        return True
    return procedure
