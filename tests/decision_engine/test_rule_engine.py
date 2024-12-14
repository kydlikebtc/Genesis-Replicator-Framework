"""
Tests for the Rule Engine implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from genesis_replicator.decision_engine.rule_engine import RuleEngine

@pytest.fixture
async def rule_engine():
    """Create a new RuleEngine instance for testing."""
    engine = RuleEngine()
    await engine.start()
    yield engine
    await engine.stop()

@pytest.mark.asyncio
async def test_rule_creation():
    """Test rule creation and validation."""
    engine = RuleEngine()
    await engine.start()

    # Test valid rule creation
    rule_config = {
        "name": "test_rule",
        "condition": "price > threshold",
        "action": "execute_trade",
        "parameters": {
            "threshold": 100,
            "position_size": 1000
        }
    }

    rule_id = await engine.create_rule(rule_config)
    assert rule_id == "test_rule"
    assert engine.get_rule_status(rule_id) == "active"

    # Test invalid rule creation
    with pytest.raises(ValueError):
        await engine.create_rule({
            "name": "invalid_rule"
            # Missing required fields
        })

    await engine.stop()

@pytest.mark.asyncio
async def test_rule_evaluation():
    """Test rule evaluation process."""
    engine = RuleEngine()
    await engine.start()

    # Create test rule
    rule_id = await engine.create_rule({
        "name": "price_threshold",
        "condition": "price > threshold",
        "action": "execute_trade",
        "parameters": {"threshold": 100}
    })

    # Test rule evaluation
    context = {"price": 150}
    result = await engine.evaluate_rule(rule_id, context)
    assert result["triggered"] is True
    assert result["action"] == "execute_trade"

    # Test with non-triggering condition
    context = {"price": 50}
    result = await engine.evaluate_rule(rule_id, context)
    assert result["triggered"] is False

    await engine.stop()

@pytest.mark.asyncio
async def test_rule_chaining():
    """Test rule chaining and dependencies."""
    engine = RuleEngine()
    await engine.start()

    # Create dependent rules
    rule1_id = await engine.create_rule({
        "name": "primary_rule",
        "condition": "value > 100",
        "action": "set_flag",
        "parameters": {"flag": "high_value"}
    })

    rule2_id = await engine.create_rule({
        "name": "secondary_rule",
        "condition": "flag == 'high_value'",
        "action": "trigger_alert",
        "parameters": {}
    })

    # Add dependency
    await engine.add_rule_dependency(rule2_id, rule1_id)

    # Test chained evaluation
    context = {"value": 150}
    results = await engine.evaluate_rule_chain(rule2_id, context)

    assert len(results) == 2
    assert results[0]["rule_id"] == rule1_id
    assert results[1]["rule_id"] == rule2_id
    assert all(r["triggered"] for r in results)

    await engine.stop()

@pytest.mark.asyncio
async def test_rule_priority():
    """Test rule priority handling."""
    engine = RuleEngine()
    await engine.start()

    execution_order = []
    async def track_execution(rule_id):
        execution_order.append(rule_id)

    # Create rules with different priorities
    rules = [
        {
            "name": f"rule_{i}",
            "condition": "true",
            "action": "track",
            "priority": i
        } for i in range(3)
    ]

    rule_ids = []
    for rule in rules:
        rule_id = await engine.create_rule(rule)
        rule_ids.append(rule_id)

    # Evaluate rules
    with patch.object(engine, '_execute_action', side_effect=track_execution):
        await engine.evaluate_all_rules({})
        await asyncio.sleep(0.1)  # Allow async processing

    # Verify execution order
    assert execution_order == rule_ids[::-1]  # Highest priority first

    await engine.stop()

@pytest.mark.asyncio
async def test_rule_conditions():
    """Test different types of rule conditions."""
    engine = RuleEngine()
    await engine.start()

    # Test numeric comparison
    numeric_rule = await engine.create_rule({
        "name": "numeric_rule",
        "condition": "value >= threshold",
        "parameters": {"threshold": 100}
    })

    # Test string comparison
    string_rule = await engine.create_rule({
        "name": "string_rule",
        "condition": "status == 'active'",
        "parameters": {}
    })

    # Test compound condition
    compound_rule = await engine.create_rule({
        "name": "compound_rule",
        "condition": "value > min_value and value < max_value",
        "parameters": {"min_value": 100, "max_value": 200}
    })

    # Test evaluations
    context = {
        "value": 150,
        "status": "active"
    }

    assert (await engine.evaluate_rule(numeric_rule, context))["triggered"]
    assert (await engine.evaluate_rule(string_rule, context))["triggered"]
    assert (await engine.evaluate_rule(compound_rule, context))["triggered"]

    await engine.stop()

@pytest.mark.asyncio
async def test_rule_actions():
    """Test rule action execution."""
    engine = RuleEngine()
    await engine.start()

    executed_actions = []
    async def mock_action_handler(action_type, parameters):
        executed_actions.append((action_type, parameters))

    # Register action handler
    engine.register_action_handler(mock_action_handler)

    # Create rule with action
    rule_id = await engine.create_rule({
        "name": "test_rule",
        "condition": "true",
        "action": "custom_action",
        "action_parameters": {"param1": "value1"}
    })

    # Evaluate rule
    await engine.evaluate_rule(rule_id, {})
    await asyncio.sleep(0.1)  # Allow async processing

    assert len(executed_actions) == 1
    assert executed_actions[0][0] == "custom_action"
    assert executed_actions[0][1]["param1"] == "value1"

    await engine.stop()
