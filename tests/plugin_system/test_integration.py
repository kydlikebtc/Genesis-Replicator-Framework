"""
Integration tests for the plugin system.
"""
import pytest
import asyncio
from typing import Dict, Any
from genesis_replicator.plugin_system.plugin_manager import PluginManager
from genesis_replicator.plugin_system.plugin_interface import PluginInterface, PluginMetadata


class CustomTestPlugin(PluginInterface):
    """Custom test plugin for integration testing."""
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.event_received = None

    async def initialize(self) -> bool:
        self._context["initialized"] = True
        return True

    async def start(self) -> bool:
        self._context["started"] = True
        return True

    async def stop(self) -> bool:
        self._context["started"] = False
        return True

    async def cleanup(self) -> bool:
        self._context.clear()
        return True

    async def handle_event(self, event_type: str, event_data: Any) -> Any:
        self.event_received = (event_type, event_data)
        return event_data

    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return "test_key" in config


async def test_full_plugin_workflow():
    """Test complete plugin workflow from registration to event handling."""
    # Setup
    manager = PluginManager()
    metadata = PluginMetadata(
        name="custom_test_plugin",
        version="1.0.0",
        author="Test Author",
        description="Integration Test Plugin",
        dependencies={},
        permissions=["event.subscribe", "event.publish"],
        checksum="test_checksum"
    )
    config = {"test_key": "test_value"}
    plugin_code = """
    class CustomTestPlugin(PluginInterface):
        pass
    """

    # Register plugin
    result = await manager.register_plugin(
        CustomTestPlugin,
        metadata,
        config,
        plugin_code
    )
    assert result is True

    # Enable plugin
    result = await manager.enable_plugin("custom_test_plugin")
    assert result is True

    # Register event handler
    result = manager.register_event_handler("custom_test_plugin", "test_event")
    assert result is True

    # Send event
    test_data = {"message": "test"}
    await manager.handle_framework_event("test_event", test_data)

    # Update configuration
    new_config = {"test_key": "updated_value"}
    result = manager.update_plugin_config("custom_test_plugin", new_config)
    assert result is True

    # Disable plugin
    result = await manager.disable_plugin("custom_test_plugin")
    assert result is True


async def test_plugin_error_handling():
    """Test plugin system error handling and recovery."""
    manager = PluginManager()
    metadata = PluginMetadata(
        name="error_test_plugin",
        version="1.0.0",
        author="Test Author",
        description="Error Test Plugin",
        dependencies={"non_existent_plugin": "1.0.0"},
        permissions=["invalid_permission"],
        checksum="invalid_checksum"
    )

    # Test invalid plugin registration
    result = await manager.register_plugin(
        CustomTestPlugin,
        metadata,
        {},
        "invalid_code"
    )
    assert result is False

    # Test invalid configuration
    metadata.dependencies = {}
    metadata.checksum = "test_checksum"
    result = await manager.register_plugin(
        CustomTestPlugin,
        metadata,
        {"invalid_key": "value"},
        "class CustomTestPlugin(PluginInterface): pass"
    )
    assert result is False
