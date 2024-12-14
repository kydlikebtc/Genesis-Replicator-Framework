"""
Fixtures for plugin system tests.
"""
import pytest
import asyncio
from typing import Dict, Any
from genesis_replicator.plugin_system.plugin_interface import PluginInterface, PluginMetadata
from genesis_replicator.plugin_system.plugin_manager import PluginManager


class TestPlugin(PluginInterface):
    """Test plugin implementation for testing."""
    async def initialize(self) -> bool:
        return True

    async def start(self) -> bool:
        return True

    async def stop(self) -> bool:
        return True

    async def cleanup(self) -> bool:
        return True

    async def handle_event(self, event_type: str, event_data: Any) -> Any:
        return event_data

    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return True


@pytest.fixture
def test_metadata():
    """Fixture for test plugin metadata."""
    return PluginMetadata(
        name="test_plugin",
        version="1.0.0",
        author="Test Author",
        description="Test Plugin",
        dependencies={},
        permissions=["event.subscribe"],
        checksum="test_checksum"
    )


@pytest.fixture
def test_plugin(test_metadata):
    """Fixture for test plugin instance."""
    return TestPlugin(test_metadata)


@pytest.fixture
async def plugin_manager():
    """Fixture for plugin manager instance."""
    manager = PluginManager()
    yield manager
