"""
Plugin Lifecycle Management for Genesis Replicator Framework.
"""
from typing import Dict, Any, Optional
import asyncio
import logging
from .plugin_interface import PluginInterface, PluginMetadata

logger = logging.getLogger(__name__)


class PluginLifecycle:
    """Manages the lifecycle of plugins including loading, enabling, and disabling."""

    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._states: Dict[str, str] = {}
        self._dependencies_met: Dict[str, bool] = {}

    async def load_plugin(self, plugin: PluginInterface) -> bool:
        """Load a plugin and verify its metadata."""
        try:
            plugin_name = plugin.metadata.name
            if plugin_name in self._plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return False

            # Verify dependencies
            if not await self._verify_dependencies(plugin.metadata):
                logger.error(f"Dependencies not met for plugin {plugin_name}")
                return False

            self._plugins[plugin_name] = plugin
            self._states[plugin_name] = "loaded"
            logger.info(f"Plugin {plugin_name} loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading plugin: {str(e)}")
            return False

    async def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a loaded plugin."""
        try:
            if plugin_name not in self._plugins:
                logger.error(f"Plugin {plugin_name} not found")
                return False

            plugin = self._plugins[plugin_name]
            if not await plugin.initialize():
                logger.error(f"Failed to initialize plugin {plugin_name}")
                return False

            if not await plugin.start():
                logger.error(f"Failed to start plugin {plugin_name}")
                await plugin.cleanup()
                return False

            plugin._is_enabled = True
            self._states[plugin_name] = "enabled"
            logger.info(f"Plugin {plugin_name} enabled successfully")
            return True
        except Exception as e:
            logger.error(f"Error enabling plugin {plugin_name}: {str(e)}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """Disable an enabled plugin."""
        try:
            if plugin_name not in self._plugins:
                logger.error(f"Plugin {plugin_name} not found")
                return False


            plugin = self._plugins[plugin_name]
            if not plugin.is_enabled():
                logger.warning(f"Plugin {plugin_name} is not enabled")
                return False

            if not await plugin.stop():
                logger.error(f"Failed to stop plugin {plugin_name}")
                return False

            if not await plugin.cleanup():
                logger.error(f"Failed to cleanup plugin {plugin_name}")
                return False

            plugin._is_enabled = False
            self._states[plugin_name] = "disabled"
            logger.info(f"Plugin {plugin_name} disabled successfully")
            return True
        except Exception as e:
            logger.error(f"Error disabling plugin {plugin_name}: {str(e)}")
            return False

    async def _verify_dependencies(self, metadata: PluginMetadata) -> bool:
        """Verify that all plugin dependencies are met."""
        for dep_name, dep_version in metadata.dependencies.items():
            if dep_name not in self._plugins:
                return False
            # Version verification logic would go here
        return True

    def get_plugin_state(self, plugin_name: str) -> Optional[str]:
        """Get the current state of a plugin."""
        return self._states.get(plugin_name)

    def get_loaded_plugins(self) -> Dict[str, PluginInterface]:
        """Get all loaded plugins."""
        return self._plugins.copy()

    def get_enabled_plugins(self) -> Dict[str, PluginInterface]:
        """Get all enabled plugins."""
        return {name: plugin for name, plugin in self._plugins.items()
                if plugin.is_enabled()}
