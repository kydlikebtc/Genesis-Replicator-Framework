"""
Tests for the plugin security implementation.
"""
import pytest
from genesis_replicator.plugin_system.plugin_security import PluginSecurity


def test_plugin_validation(test_metadata):
    """Test plugin validation process."""
    security = PluginSecurity()
    plugin_code = "class TestPlugin(PluginInterface): pass"

    # Register trusted checksum
    security.register_trusted_checksum("test_plugin", "test_checksum")

    # Test validation
    result = security.validate_plugin(test_metadata, plugin_code)
    assert result is True


def test_permission_validation(test_metadata):
    """Test permission validation."""
    security = PluginSecurity()

    # Register permissions
    security.register_permissions("test_plugin", ["event.subscribe"])

    # Test runtime permission check
    result = security.verify_runtime_permissions(
        "test_plugin",
        "event.subscribe",
        {"context": "test"}
    )
    assert result is True


def test_plugin_blocking(test_metadata):
    """Test plugin blocking functionality."""
    security = PluginSecurity()
    plugin_code = "class TestPlugin(PluginInterface): pass"

    # Block plugin
    security.block_plugin("test_plugin")

    # Verify blocked plugin validation fails
    result = security.validate_plugin(test_metadata, plugin_code)
    assert result is False

    # Unblock and verify
    security.unblock_plugin("test_plugin")
    security.register_trusted_checksum("test_plugin", "test_checksum")
    result = security.validate_plugin(test_metadata, plugin_code)
    assert result is True
