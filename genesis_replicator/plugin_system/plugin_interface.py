"""
Plugin Interface definitions for Genesis Replicator Framework.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import asyncio


@dataclass
class PluginMetadata:
    """Metadata for plugin identification and verification."""
    name: str
    version: str
    author: str
    description: str
    dependencies: Dict[str, str]
    permissions: list[str]
    checksum: str


class PluginInterface(ABC):
    """Base interface that all plugins must implement."""

    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self._is_enabled = False
        self._context: Dict[str, Any] = {}

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin with required resources."""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Start the plugin's main functionality."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the plugin's functionality."""
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """Clean up resources used by the plugin."""
        pass

    def is_enabled(self) -> bool:
        """Check if the plugin is currently enabled."""
        return self._is_enabled

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set the plugin's execution context."""
        self._context = context

    def get_context(self) -> Dict[str, Any]:
        """Get the plugin's current execution context."""
        return self._context.copy()

    @abstractmethod
    async def handle_event(self, event_type: str, event_data: Any) -> Optional[Any]:
        """Handle framework events."""
        pass

    @abstractmethod
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass
