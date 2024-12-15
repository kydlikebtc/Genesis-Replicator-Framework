"""
Tests for the plugin lifecycle implementation.
"""
import pytest
from genesis_replicator.plugin_system.plugin_lifecycle import PluginLifecycle


async def test_plugin_loading(test_plugin):
    """Test plugin loading process."""
    lifecycle = PluginLifecycle()
    result = await lifecycle.load_plugin(test_plugin)
    assert result is True

    loaded_plugins = lifecycle.get_loaded_plugins()
    assert "test_plugin" in loaded_plugins


async def test_plugin_enabling(test_plugin):
    """Test plugin enabling process."""
    lifecycle = PluginLifecycle()
    await lifecycle.load_plugin(test_plugin)

    result = await lifecycle.enable_plugin("test_plugin")
    assert result is True

    state = lifecycle.get_plugin_state("test_plugin")
    assert state == "enabled"


async def test_plugin_disabling(test_plugin):
    """Test plugin disabling process."""
    lifecycle = PluginLifecycle()
    await lifecycle.load_plugin(test_plugin)
    await lifecycle.enable_plugin("test_plugin")

    result = await lifecycle.disable_plugin("test_plugin")
    assert result is True

    state = lifecycle.get_plugin_state("test_plugin")
    assert state == "disabled"


async def test_dependency_verification(test_plugin, test_metadata):
    """Test plugin dependency verification."""
    lifecycle = PluginLifecycle()

    # Test with no dependencies
    result = await lifecycle._verify_dependencies(test_metadata)
    assert result is True

    # Test with dependencies
    test_metadata.dependencies = {"dep_plugin": "1.0.0"}
    result = await lifecycle._verify_dependencies(test_metadata)
    assert result is False
