"""
Plugin Security Management for Genesis Replicator Framework.
"""
import hashlib
import json
from typing import Dict, Any, List
import logging
from .plugin_interface import PluginMetadata

logger = logging.getLogger(__name__)


class PluginSecurity:
    """Manages plugin security, validation, and permissions."""

    def __init__(self):
        self._trusted_checksums: Dict[str, str] = {}
        self._permission_registry: Dict[str, List[str]] = {}
        self._blocked_plugins: List[str] = []

    def validate_plugin(self, metadata: PluginMetadata, plugin_code: str) -> bool:
        """Validate plugin metadata and code integrity."""
        try:
            # Verify plugin is not blocked
            if metadata.name in self._blocked_plugins:
                logger.warning(f"Plugin {metadata.name} is blocked")
                return False

            # Verify checksum
            computed_checksum = self._compute_checksum(plugin_code)
            if computed_checksum != metadata.checksum:
                logger.error(f"Checksum mismatch for plugin {metadata.name}")
                return False

            # Verify permissions
            if not self._validate_permissions(metadata.permissions):
                logger.error(f"Invalid permissions requested by plugin {metadata.name}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating plugin: {str(e)}")
            return False

    def register_trusted_checksum(self, plugin_name: str, checksum: str) -> None:
        """Register a trusted checksum for a plugin."""
        self._trusted_checksums[plugin_name] = checksum

    def register_permissions(self, plugin_name: str, permissions: List[str]) -> None:
        """Register allowed permissions for a plugin."""
        self._permission_registry[plugin_name] = permissions

    def block_plugin(self, plugin_name: str) -> None:
        """Block a plugin from being loaded."""
        if plugin_name not in self._blocked_plugins:
            self._blocked_plugins.append(plugin_name)

    def unblock_plugin(self, plugin_name: str) -> None:
        """Unblock a previously blocked plugin."""
        if plugin_name in self._blocked_plugins:
            self._blocked_plugins.remove(plugin_name)

    def _compute_checksum(self, plugin_code: str) -> str:
        """Compute SHA-256 checksum of plugin code."""
        return hashlib.sha256(plugin_code.encode()).hexdigest()

    def _validate_permissions(self, requested_permissions: List[str]) -> bool:
        """Validate requested permissions against allowed permissions."""
        allowed_permissions = {
            "filesystem.read",
            "filesystem.write",
            "network.connect",
            "event.subscribe",
            "event.publish",
            "agent.interact",
            "config.read",
            "config.write"
        }
        return all(perm in allowed_permissions for perm in requested_permissions)

    def verify_runtime_permissions(self, plugin_name: str,
                                 permission: str,
                                 context: Dict[str, Any]) -> bool:
        """Verify plugin permissions at runtime."""
        if plugin_name not in self._permission_registry:
            return False
        return permission in self._permission_registry[plugin_name]
