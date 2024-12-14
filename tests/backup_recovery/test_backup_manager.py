"""
Tests for the backup manager.
"""
import pytest
import json
from pathlib import Path

async def test_backup_creation(backup_manager, sample_state):
    """Test creating a new backup."""
    components = ["state", "config"]
    backup_id = await backup_manager.create_backup(components)

    assert backup_id is not None
    backup_path = Path(backup_manager.backup_dir) / backup_id
    assert backup_path.exists()

    with open(backup_path / "metadata.json") as f:
        metadata = json.load(f)
        assert metadata["components"] == components
        assert metadata["status"] == "completed"

async def test_backup_restoration(backup_manager, sample_state):
    """Test restoring from backup."""
    components = ["state", "config"]
    backup_id = await backup_manager.create_backup(components)

    # Attempt restoration
    success = await backup_manager.restore_backup(backup_id)
    assert success is True

async def test_invalid_backup_restoration(backup_manager):
    """Test restoring from invalid backup."""
    with pytest.raises(ValueError):
        await backup_manager.restore_backup("nonexistent_backup")

async def test_list_backups(backup_manager, sample_state):
    """Test listing available backups."""
    # Create multiple backups
    backup_ids = []
    for _ in range(3):
        backup_id = await backup_manager.create_backup(["state"])
        backup_ids.append(backup_id)

    backups = await backup_manager.list_backups()
    assert len(backups) == 3
    assert all(b["backup_id"] in backup_ids for b in backups)

async def test_partial_backup_restoration(backup_manager, sample_state):
    """Test restoring specific components from backup."""
    components = ["state", "config", "models"]
    backup_id = await backup_manager.create_backup(components)

    # Restore only state component
    success = await backup_manager.restore_backup(backup_id, components=["state"])
    assert success is True
