"""
Tests for the Contract Manager implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager

@pytest.fixture
async def contract_manager():
    """Create a new ContractManager instance for testing."""
    manager = ContractManager()
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_contract_deployment():
    """Test contract deployment functionality."""
    manager = ContractManager()
    await manager.start()

    # Mock contract data
    contract_abi = [{"type": "function", "name": "test", "inputs": [], "outputs": []}]
    contract_bytecode = "0x123..."

    with patch.object(manager, '_deploy_contract') as mock_deploy:
        mock_deploy.return_value = "0xabc..."

        address = await manager.deploy_contract(
            contract_abi,
            contract_bytecode,
            constructor_args=[]
        )

        assert address == "0xabc..."
        mock_deploy.assert_called_once()

    await manager.stop()

@pytest.mark.asyncio
async def test_contract_interaction():
    """Test contract method interaction."""
    manager = ContractManager()
    await manager.start()

    # Mock contract instance
    mock_contract = Mock()
    mock_contract.test = Mock(return_value="test_result")

    with patch.object(manager, '_get_contract', return_value=mock_contract):
        result = await manager.call_contract_method(
            "0xabc...",
            "test",
            []
        )

        assert result == "test_result"
        mock_contract.test.assert_called_once()

    await manager.stop()

@pytest.mark.asyncio
async def test_contract_event_monitoring():
    """Test contract event monitoring."""
    manager = ContractManager()
    await manager.start()

    events = []
    async def event_callback(event):
        events.append(event)

    # Register event monitor
    contract_address = "0xabc..."
    event_name = "TestEvent"

    await manager.monitor_contract_events(
        contract_address,
        event_name,
        event_callback
    )

    # Simulate event
    mock_event = {
        "event": "TestEvent",
        "args": {"param1": "value1"}
    }

    # Trigger mock event
    await manager._process_contract_event(contract_address, mock_event)
    await asyncio.sleep(0.1)  # Allow async processing

    assert len(events) == 1
    assert events[0]["event"] == "TestEvent"
    assert events[0]["args"]["param1"] == "value1"

    await manager.stop()

@pytest.mark.asyncio
async def test_contract_validation():
    """Test contract validation functionality."""
    manager = ContractManager()
    await manager.start()

    # Test invalid ABI
    with pytest.raises(ValueError):
        await manager.deploy_contract(
            [],  # Empty ABI
            "0x123...",
            []
        )

    # Test invalid bytecode
    with pytest.raises(ValueError):
        await manager.deploy_contract(
            [{"type": "function", "name": "test"}],
            "",  # Empty bytecode
            []
        )

    await manager.stop()

@pytest.mark.asyncio
async def test_contract_state_management():
    """Test contract state management."""
    manager = ContractManager()
    await manager.start()

    # Mock contract state
    contract_address = "0xabc..."
    state_var = "test_var"

    with patch.object(manager, '_get_contract_state') as mock_state:
        mock_state.return_value = "test_value"

        value = await manager.get_contract_state(
            contract_address,
            state_var
        )

        assert value == "test_value"
        mock_state.assert_called_once_with(contract_address, state_var)

    await manager.stop()

@pytest.mark.asyncio
async def test_contract_error_handling():
    """Test error handling in contract operations."""
    manager = ContractManager()
    await manager.start()

    # Test handling of deployment error
    with patch.object(manager, '_deploy_contract', side_effect=Exception("Deployment failed")):
        with pytest.raises(Exception) as exc_info:
            await manager.deploy_contract(
                [{"type": "function", "name": "test"}],
                "0x123...",
                []
            )
        assert str(exc_info.value) == "Deployment failed"

    await manager.stop()
