"""
Plugin System for Genesis Replicator Framework.

This module provides a flexible plugin architecture for extending framework functionality.
"""

from .plugin_manager import PluginManager
from .plugin_interface import PluginInterface, PluginMetadata
from .plugin_lifecycle import PluginLifecycle
from .plugin_security import PluginSecurity

__all__ = ['PluginManager', 'PluginInterface', 'PluginMetadata', 'PluginLifecycle', 'PluginSecurity']
