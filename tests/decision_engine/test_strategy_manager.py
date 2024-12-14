"""
Tests for the Strategy Manager implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from genesis_replicator.decision_engine.strategy_manager import StrategyManager

@pytest.fixture
async def strategy_manager():
    """Create a new StrategyManager instance for testing."""
    manager = StrategyManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_strategy_registration():
    """Test strategy registration and validation."""
    manager = StrategyManager()
    await manager.start()

    # Test valid strategy registration
    strategy_config = {
        "name": "test_strategy",
        "type": "trading",
        "parameters": {
            "risk_level": "medium",
            "max_position_size": 1000
        }
    }

    strategy_id = await manager.register_strategy(strategy_config)
    assert strategy_id == "test_strategy"
    assert manager.get_strategy_status(strategy_id) == "registered"

    # Test invalid strategy registration
    with pytest.raises(ValueError):
        await manager.register_strategy({
            "name": "invalid_strategy"
            # Missing required fields
        })

    await manager.stop()

@pytest.mark.asyncio
async def test_strategy_execution():
    """Test strategy execution and monitoring."""
    manager = StrategyManager()
    await manager.start()

    execution_results = []
    async def execution_callback(strategy_id, result):
        execution_results.append((strategy_id, result))

    # Register strategy and callback
    strategy_id = await manager.register_strategy({
        "name": "test_strategy",
        "type": "trading",
        "parameters": {"test_param": "value"}
    })

    manager.register_execution_callback(execution_callback)

    # Execute strategy
    await manager.execute_strategy(strategy_id, {"market_data": "test_data"})
    await asyncio.sleep(0.1)  # Allow async processing

    assert len(execution_results) == 1
    assert execution_results[0][0] == strategy_id

    await manager.stop()

@pytest.mark.asyncio
async def test_strategy_optimization():
    """Test strategy optimization functionality."""
    manager = StrategyManager()
    await manager.start()

    strategy_id = await manager.register_strategy({
        "name": "test_strategy",
        "type": "trading",
        "parameters": {
            "threshold": 0.5,
            "window_size": 10
        }
    })

    # Mock performance metrics
    performance_data = {
        "returns": 0.15,
        "sharpe_ratio": 1.5,
        "max_drawdown": 0.1
    }

    # Optimize strategy parameters
    with patch.object(manager, '_evaluate_performance', return_value=performance_data):
        optimized_params = await manager.optimize_strategy(strategy_id)
        assert isinstance(optimized_params, dict)
        assert "threshold" in optimized_params
        assert "window_size" in optimized_params

    await manager.stop()

@pytest.mark.asyncio
async def test_strategy_validation():
    """Test strategy validation rules."""
    manager = StrategyManager()
    await manager.start()

    # Test parameter validation
    with pytest.raises(ValueError):
        await manager.register_strategy({
            "name": "test_strategy",
            "type": "trading",
            "parameters": {
                "risk_level": "invalid_level"  # Invalid risk level
            }
        })

    # Test strategy type validation
    with pytest.raises(ValueError):
        await manager.register_strategy({
            "name": "test_strategy",
            "type": "invalid_type",
            "parameters": {}
        })

    await manager.stop()

@pytest.mark.asyncio
async def test_strategy_monitoring():
    """Test strategy monitoring and alerts."""
    manager = StrategyManager()
    await manager.start()

    alerts = []
    async def alert_callback(strategy_id, alert_type, details):
        alerts.append((strategy_id, alert_type, details))

    # Register strategy and alert callback
    strategy_id = await manager.register_strategy({
        "name": "test_strategy",
        "type": "trading",
        "parameters": {"threshold": 0.5}
    })

    manager.register_alert_callback(alert_callback)

    # Simulate performance degradation
    await manager._monitor_performance(strategy_id)
    await asyncio.sleep(0.1)  # Allow async processing

    assert len(alerts) > 0
    assert alerts[0][0] == strategy_id

    await manager.stop()

@pytest.mark.asyncio
async def test_strategy_persistence():
    """Test strategy state persistence."""
    manager = StrategyManager()
    await manager.start()

    # Register and configure strategy
    strategy_id = await manager.register_strategy({
        "name": "test_strategy",
        "type": "trading",
        "parameters": {"initial_param": "value"}
    })

    # Update strategy state
    new_state = {"updated_param": "new_value"}
    await manager.update_strategy_state(strategy_id, new_state)

    # Verify persistence
    saved_state = await manager.get_strategy_state(strategy_id)
    assert saved_state["updated_param"] == "new_value"

    await manager.stop()
