"""
Tests for the monitoring configuration system.
"""
import pytest
import os
import json
from genesis_replicator.monitoring.monitoring_config import MonitoringConfig

def test_config_initialization(monitoring_config):
    """Test configuration initialization."""
    assert monitoring_config.metrics_config is not None
    assert monitoring_config.health_check_config is not None
    assert monitoring_config.alert_config is not None

def test_config_persistence(monitoring_config, tmp_path):
    """Test configuration persistence."""
    # Update configuration
    monitoring_config.update_metrics_config(collection_interval=30)
    monitoring_config.update_health_check_config(check_interval=15)
    monitoring_config.update_alert_config(
        notification_channels=["email", "slack"]
    )

    # Create new instance with same path
    new_config = MonitoringConfig(monitoring_config.config_path)

    # Verify persistence
    assert new_config.metrics_config.collection_interval == 30
    assert new_config.health_check_config.check_interval == 15
    assert "email" in new_config.alert_config.notification_channels
    assert "slack" in new_config.alert_config.notification_channels

def test_config_validation(monitoring_config):
    """Test configuration validation."""
    # Test invalid metrics configuration
    with pytest.raises(AttributeError):
        monitoring_config.update_metrics_config(invalid_option=123)

    # Test invalid health check configuration
    with pytest.raises(AttributeError):
        monitoring_config.update_health_check_config(invalid_option=123)

    # Test invalid alert configuration
    with pytest.raises(AttributeError):
        monitoring_config.update_alert_config(invalid_option=123)

def test_config_security(monitoring_config, tmp_path):
    """Test configuration security."""
    config_path = tmp_path / "monitoring_config.json"

    # Create config with sensitive data
    config_data = {
        "metrics": {"collection_interval": 60},
        "health_checks": {"check_interval": 30},
        "alerts": {
            "notification_channels": ["secure_channel"],
            "severity_thresholds": {"critical": 0.9}
        }
    }

    with open(config_path, 'w') as f:
        json.dump(config_data, f)

    # Verify file permissions
    assert os.stat(config_path).st_mode & 0o777 == 0o644

def test_performance_settings(monitoring_config):
    """Test performance-related configuration."""
    # Configure for high performance
    monitoring_config.update_metrics_config(
        collection_interval=1,
        max_entries=10000
    )
    monitoring_config.update_health_check_config(
        check_interval=1,
        timeout=0.5
    )

    # Verify settings
    metrics_config = monitoring_config.get_metrics_config()
    assert metrics_config.collection_interval == 1
    assert metrics_config.max_entries == 10000

    health_config = monitoring_config.get_health_check_config()
    assert health_config.check_interval == 1
    assert health_config.timeout == 0.5
