"""
Configuration management for the monitoring system.

This module handles configuration settings for metrics collection,
health checks, and alert management in the Genesis Replicator Framework.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import os

@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    collection_interval: int = 60
    retention_period: int = 86400  # 24 hours
    max_entries: int = 1000
    enabled_metrics: List[str] = None

@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    check_interval: int = 30
    timeout: float = 5.0
    retry_count: int = 3
    retry_delay: int = 5

@dataclass
class AlertConfig:
    """Configuration for alert management."""
    notification_channels: List[str]
    severity_thresholds: Dict[str, float]
    aggregation_window: int = 300  # 5 minutes
    cooldown_period: int = 3600  # 1 hour

class MonitoringConfig:
    """Manages monitoring system configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize monitoring configuration.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), "..", "config", "monitoring_config.json"
        )
        self.metrics_config = MetricsConfig()
        self.health_check_config = HealthCheckConfig()
        self.alert_config = AlertConfig(
            notification_channels=["console"],
            severity_thresholds={
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "error_rate": 0.01
            }
        )
        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            self._save_config()
            return

        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

            # Update metrics configuration
            metrics_data = config_data.get('metrics', {})
            self.metrics_config = MetricsConfig(
                collection_interval=metrics_data.get('collection_interval', 60),
                retention_period=metrics_data.get('retention_period', 86400),
                max_entries=metrics_data.get('max_entries', 1000),
                enabled_metrics=metrics_data.get('enabled_metrics', None)
            )

            # Update health check configuration
            health_data = config_data.get('health_checks', {})
            self.health_check_config = HealthCheckConfig(
                check_interval=health_data.get('check_interval', 30),
                timeout=health_data.get('timeout', 5.0),
                retry_count=health_data.get('retry_count', 3),
                retry_delay=health_data.get('retry_delay', 5)
            )

            # Update alert configuration
            alert_data = config_data.get('alerts', {})
            self.alert_config = AlertConfig(
                notification_channels=alert_data.get('notification_channels', ['console']),
                severity_thresholds=alert_data.get('severity_thresholds', {
                    "cpu_usage": 80.0,
                    "memory_usage": 85.0,
                    "disk_usage": 90.0,
                    "error_rate": 0.01
                }),
                aggregation_window=alert_data.get('aggregation_window', 300),
                cooldown_period=alert_data.get('cooldown_period', 3600)
            )

        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"Failed to load monitoring configuration: {str(e)}")

    def _save_config(self):
        """Save current configuration to file."""
        config_data = {
            'metrics': {
                'collection_interval': self.metrics_config.collection_interval,
                'retention_period': self.metrics_config.retention_period,
                'max_entries': self.metrics_config.max_entries,
                'enabled_metrics': self.metrics_config.enabled_metrics
            },
            'health_checks': {
                'check_interval': self.health_check_config.check_interval,
                'timeout': self.health_check_config.timeout,
                'retry_count': self.health_check_config.retry_count,
                'retry_delay': self.health_check_config.retry_delay
            },
            'alerts': {
                'notification_channels': self.alert_config.notification_channels,
                'severity_thresholds': self.alert_config.severity_thresholds,
                'aggregation_window': self.alert_config.aggregation_window,
                'cooldown_period': self.alert_config.cooldown_period
            }
        }

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_data, f, indent=4)
        except IOError as e:
            raise RuntimeError(f"Failed to save monitoring configuration: {str(e)}")

    def update_metrics_config(self, **kwargs):
        """Update metrics collection configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.metrics_config, key):
                setattr(self.metrics_config, key, value)
        self._save_config()

    def update_health_check_config(self, **kwargs):
        """Update health check configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.health_check_config, key):
                setattr(self.health_check_config, key, value)
        self._save_config()

    def update_alert_config(self, **kwargs):
        """Update alert management configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.alert_config, key):
                setattr(self.alert_config, key, value)
        self._save_config()

    def get_metrics_config(self) -> MetricsConfig:
        """Get current metrics configuration.

        Returns:
            Current metrics configuration
        """
        return self.metrics_config

    def get_health_check_config(self) -> HealthCheckConfig:
        """Get current health check configuration.

        Returns:
            Current health check configuration
        """
        return self.health_check_config

    def get_alert_config(self) -> AlertConfig:
        """Get current alert configuration.

        Returns:
            Current alert configuration
        """
        return self.alert_config
