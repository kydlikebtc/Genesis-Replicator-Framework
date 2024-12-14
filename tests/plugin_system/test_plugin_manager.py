"""
Tests for the plugin manager implementation.
"""
import pytest
from typing import Dict, Any
from genesis_replicator.plugin_system.plugin_manager import PluginManager
from genesis_replicator.plugin_system.plugin_interface import PluginInterface
from .conftest import TestPlugin  # Import TestPlugin from local conftest


async def test_plugin_registration(plugin_manager, test_plugin, test_metadata):
    """Test plugin registration process."""
    config = {"test_key": "test_value"}
    plugin_code = "class TestPlugin(PluginInterface): pass"

    result = await plugin_manager.register_plugin(
        TestPlugin,
        test_metadata,
        config,
        plugin_code
    )
    assert result is True

    stored_config = plugin_manager.get_plugin_config("test_plugin")
    assert stored_config == config


async def test_plugin_lifecycle(plugin_manager, test_plugin, test_metadata):
    """Test plugin lifecycle management."""
    config = {"test_key": "test_value"}
    plugin_code = "class TestPlugin(PluginInterface): pass"

    # Register
    await plugin_manager.register_plugin(TestPlugin, test_metadata, config, plugin_code)

    # Enable
    result = await plugin_manager.enable_plugin("test_plugin")
    assert result is True

    # Disable
    result = await plugin_manager.disable_plugin("test_plugin")
    assert result is True


async def test_plugin_event_handling(plugin_manager, test_plugin, test_metadata):
    """Test plugin event handling."""
    config = {"test_key": "test_value"}
    plugin_code = "class TestPlugin(PluginInterface): pass"

    # Register and enable
    await plugin_manager.register_plugin(TestPlugin, test_metadata, config, plugin_code)
    await plugin_manager.enable_plugin("test_plugin")

    # Register event handler
    result = plugin_manager.register_event_handler("test_plugin", "test_event")
    assert result is True

    # Handle event
    event_data = {"test": "data"}
    await plugin_manager.handle_framework_event("test_event", event_data)


async def test_plugin_config_update(plugin_manager, test_plugin, test_metadata):
    """Test plugin configuration updates."""
    initial_config = {"test_key": "test_value"}
    plugin_code = "class TestPlugin(PluginInterface): pass"

    # Register
    await plugin_manager.register_plugin(TestPlugin, test_metadata, initial_config, plugin_code)

    # Update config
    new_config = {"test_key": "new_value"}
    result = plugin_manager.update_plugin_config("test_plugin", new_config)
    assert result is True

    # Verify update
    stored_config = plugin_manager.get_plugin_config("test_plugin")
    assert stored_config == new_config
