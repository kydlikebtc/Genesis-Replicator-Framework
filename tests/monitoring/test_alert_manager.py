"""
Tests for the alert management system.
"""
import pytest
from datetime import datetime
from genesis_replicator.monitoring.alert_manager import AlertSeverity, AlertStatus

async def test_alert_creation(alert_manager):
    """Test alert creation and notification."""
    alert_id = await alert_manager.create_alert(
        title="Test Alert",
        description="Test Description",
        severity=AlertSeverity.WARNING,
        source="test_source"
    )

    assert alert_id in alert_manager.alerts
    alert = alert_manager.alerts[alert_id]
    assert alert.title == "Test Alert"
    assert alert.severity == AlertSeverity.WARNING
    assert alert.status == AlertStatus.NEW

async def test_alert_lifecycle(alert_manager):
    """Test alert lifecycle management."""
    alert_id = await alert_manager.create_alert(
        title="Lifecycle Test",
        description="Test Description",
        severity=AlertSeverity.ERROR,
        source="test_source"
    )

    # Test acknowledgement
    await alert_manager.acknowledge_alert(alert_id, {"user": "test_user"})
    assert alert_manager.alerts[alert_id].status == AlertStatus.ACKNOWLEDGED

    # Test resolution
    await alert_manager.resolve_alert(alert_id, {"resolution": "fixed"})
    assert alert_manager.alerts[alert_id].status == AlertStatus.RESOLVED

    # Test closure
    await alert_manager.close_alert(alert_id)
    assert alert_manager.alerts[alert_id].status == AlertStatus.CLOSED

async def test_alert_handlers(alert_manager, test_alert_handler):
    """Test alert handler notification."""
    alert_manager.register_handler(test_alert_handler, AlertSeverity.CRITICAL)

    await alert_manager.create_alert(
        title="Handler Test",
        description="Test Description",
        severity=AlertSeverity.CRITICAL,
        source="test_source"
    )

    assert len(test_alert_handler.alerts) == 1
    assert test_alert_handler.alerts[0].severity == AlertSeverity.CRITICAL

async def test_alert_filtering(alert_manager):
    """Test alert filtering capabilities."""
    # Create alerts with different severities
    await alert_manager.create_alert(
        title="Info Alert",
        description="Info",
        severity=AlertSeverity.INFO,
        source="test"
    )
    await alert_manager.create_alert(
        title="Warning Alert",
        description="Warning",
        severity=AlertSeverity.WARNING,
        source="test"
    )

    # Test severity filtering
    info_alerts = alert_manager.get_alerts_by_severity(AlertSeverity.INFO)
    assert len(info_alerts) == 1
    assert info_alerts[0].severity == AlertSeverity.INFO

    # Test status filtering
    active_alerts = alert_manager.get_active_alerts()
    assert len(active_alerts) == 2

async def test_security_validation(alert_manager):
    """Test alert security validation."""
    # Test invalid alert creation
    with pytest.raises(ValueError):
        await alert_manager.create_alert(
            title="",  # Empty title should fail
            description="Test",
            severity=AlertSeverity.INFO,
            source="test"
        )

    # Test unauthorized alert modification
    alert_id = await alert_manager.create_alert(
        title="Security Test",
        description="Test",
        severity=AlertSeverity.INFO,
        source="test"
    )

    with pytest.raises(ValueError):
        await alert_manager.acknowledge_alert("invalid_id", {})
