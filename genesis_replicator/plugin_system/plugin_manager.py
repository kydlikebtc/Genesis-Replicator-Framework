"""
Plugin Manager for Genesis Replicator Framework.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from .plugin_interface import PluginInterface, PluginMetadata
from .plugin_lifecycle import PluginLifecycle
from .plugin_security import PluginSecurity

logger = logging.getLogger(__name__)


class PluginManager:
    """Central manager for plugin operations including registration, loading, and event routing."""

    def __init__(self):
        self.lifecycle = PluginLifecycle()
        self.security = PluginSecurity()
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._event_handlers: Dict[str, List[PluginInterface]] = {}


    async def register_plugin(self,
                            plugin_class: Type[PluginInterface],
                            metadata: PluginMetadata,
                            config: Dict[str, Any],
                            plugin_code: str) -> bool:
        """Register and load a new plugin."""
        try:
            # Validate plugin security
            if not self.security.validate_plugin(metadata, plugin_code):
                logger.error(f"Security validation failed for plugin {metadata.name}")
                return False

            # Create plugin instance
            plugin = plugin_class(metadata)

            # Validate configuration
            if not await plugin.validate_configuration(config):
                logger.error(f"Configuration validation failed for plugin {metadata.name}")
                return False

            # Store configuration
            self._plugin_configs[metadata.name] = config

            # Load plugin
            if not await self.lifecycle.load_plugin(plugin):
                logger.error(f"Failed to load plugin {metadata.name}")
                return False

            # Set plugin context
            plugin.set_context({"config": config})

            return True
        except Exception as e:
            logger.error(f"Error registering plugin: {str(e)}")
            return False

    async def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a registered plugin."""
        return await self.lifecycle.enable_plugin(plugin_name)

    async def disable_plugin(self, plugin_name: str) -> bool:
        """Disable an enabled plugin."""
        return await self.lifecycle.disable_plugin(plugin_name)

    def get_plugin_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for a plugin."""
        return self._plugin_configs.get(plugin_name)

    def update_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """Update the configuration for a plugin."""
        try:
            plugin = self.lifecycle.get_loaded_plugins().get(plugin_name)
            if not plugin:
                logger.error(f"Plugin {plugin_name} not found")
                return False

            if not asyncio.run(plugin.validate_configuration(config)):
                logger.error(f"Invalid configuration for plugin {plugin_name}")
                return False

            self._plugin_configs[plugin_name] = config
            plugin.set_context({"config": config})
            return True
        except Exception as e:
            logger.error(f"Error updating plugin config: {str(e)}")
            return False

    async def handle_framework_event(self, event_type: str, event_data: Any) -> None:
        """Route framework events to registered plugins."""
        plugins = self.lifecycle.get_enabled_plugins()
        for plugin in plugins.values():
            try:
                await plugin.handle_event(event_type, event_data)
            except Exception as e:
                logger.error(f"Error handling event in plugin {plugin.metadata.name}: {str(e)}")

    def register_event_handler(self, plugin_name: str, event_type: str) -> bool:
        """Register a plugin as an event handler."""
        plugin = self.lifecycle.get_loaded_plugins().get(plugin_name)
        if not plugin:
            return False

        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        if plugin not in self._event_handlers[event_type]:
            self._event_handlers[event_type].append(plugin)
        return True

    def unregister_event_handler(self, plugin_name: str, event_type: str) -> bool:
        """Unregister a plugin as an event handler."""
        if event_type not in self._event_handlers:
            return False

        plugin = self.lifecycle.get_loaded_plugins().get(plugin_name)
        if not plugin:
            return False

        if plugin in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(plugin)
            return True
        return False
