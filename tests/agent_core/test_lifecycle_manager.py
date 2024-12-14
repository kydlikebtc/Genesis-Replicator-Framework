"""
Tests for the Lifecycle Manager implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from genesis_replicator.agent_core.lifecycle_manager import LifecycleManager

@pytest.fixture
async def lifecycle_manager():
    """Create a new LifecycleManager instance for testing."""
    manager = LifecycleManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_agent_creation():
    """Test agent creation and initialization."""
    manager = LifecycleManager()
    await manager.start()

    # Test creating agent with valid configuration
    agent_config = {
        "id": "test_agent",
        "type": "trading",
        "parameters": {"strategy": "test_strategy"}
    }

    agent_id = await manager.create_agent(agent_config)
    assert agent_id == "test_agent"
    assert manager.get_agent_status(agent_id) == "initialized"

    await manager.stop()

@pytest.mark.asyncio
async def test_agent_lifecycle():
    """Test agent lifecycle state transitions."""
    manager = LifecycleManager()
    await manager.start()

    # Create and start agent
    agent_id = await manager.create_agent({
        "id": "test_agent",
        "type": "trading"
    })

    # Test lifecycle transitions
    await manager.start_agent(agent_id)
    assert manager.get_agent_status(agent_id) == "running"

    await manager.pause_agent(agent_id)
    assert manager.get_agent_status(agent_id) == "paused"

    await manager.resume_agent(agent_id)
    assert manager.get_agent_status(agent_id) == "running"

    await manager.stop_agent(agent_id)
    assert manager.get_agent_status(agent_id) == "stopped"

    await manager.stop()

@pytest.mark.asyncio
async def test_agent_monitoring():
    """Test agent monitoring and health checks."""
    manager = LifecycleManager()
    await manager.start()

    health_checks = []
    async def health_callback(agent_id, status):
        health_checks.append((agent_id, status))

    # Register health monitor
    manager.register_health_monitor(health_callback)

    # Create agent and trigger health check
    agent_id = await manager.create_agent({
        "id": "test_agent",
        "type": "trading"
    })

    await manager.start_agent(agent_id)
    await manager._check_agent_health(agent_id)
    await asyncio.sleep(0.1)  # Allow async processing

    assert len(health_checks) == 1
    assert health_checks[0][0] == agent_id
    assert health_checks[0][1]["status"] == "healthy"

    await manager.stop()

@pytest.mark.asyncio
async def test_agent_recovery():
    """Test agent recovery from failures."""
    manager = LifecycleManager()
    await manager.start()

    agent_id = await manager.create_agent({
        "id": "test_agent",
        "type": "trading"
    })

    # Simulate agent failure
    with patch.object(manager, '_get_agent_process') as mock_process:
        mock_process.return_value = None
        await manager._handle_agent_failure(agent_id)

        # Verify recovery attempt
        assert manager.get_agent_status(agent_id) == "recovering"
        await asyncio.sleep(0.1)  # Allow recovery process

        # Verify automatic restart
        assert manager.get_agent_status(agent_id) == "running"

    await manager.stop()

@pytest.mark.asyncio
async def test_agent_configuration():
    """Test agent configuration management."""
    manager = LifecycleManager()
    await manager.start()

    # Test configuration validation
    with pytest.raises(ValueError):
        await manager.create_agent({
            "id": "invalid_agent"
            # Missing required 'type' field
        })

    # Test configuration update
    agent_id = await manager.create_agent({
        "id": "test_agent",
        "type": "trading",
        "parameters": {"strategy": "initial"}
    })

    await manager.update_agent_config(
        agent_id,
        {"parameters": {"strategy": "updated"}}
    )

    config = manager.get_agent_config(agent_id)
    assert config["parameters"]["strategy"] == "updated"

    await manager.stop()

@pytest.mark.asyncio
async def test_bulk_operations():
    """Test bulk agent operations."""
    manager = LifecycleManager()
    await manager.start()

    # Create multiple agents
    agent_configs = [
        {"id": f"agent_{i}", "type": "trading"}
        for i in range(3)
    ]

    agent_ids = []
    for config in agent_configs:
        agent_id = await manager.create_agent(config)
        agent_ids.append(agent_id)

    # Test bulk start
    await manager.bulk_start_agents(agent_ids)
    for agent_id in agent_ids:
        assert manager.get_agent_status(agent_id) == "running"

    # Test bulk stop
    await manager.bulk_stop_agents(agent_ids)
    for agent_id in agent_ids:
        assert manager.get_agent_status(agent_id) == "stopped"

    await manager.stop()
