"""
Alert management system for Genesis Replicator Framework.

This module handles alert generation, notification routing, and alert
lifecycle management for system events and health status changes.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle status."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class Alert:
    """Container for alert information."""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    acknowledgement: Optional[Dict[str, Any]] = None
    resolution: Optional[Dict[str, Any]] = None

class AlertHandler:
    """Base class for alert handlers."""

    async def handle_alert(self, alert: Alert):
        """Handle an alert notification.

        Args:
            alert: Alert to handle
        """
        raise NotImplementedError

class AlertManager:
    """Manages system alerts and notifications."""

    def __init__(self):
        """Initialize the alert manager."""
        self.alerts: Dict[str, Alert] = {}
        self.handlers: Dict[AlertSeverity, List[AlertHandler]] = {
            severity: [] for severity in AlertSeverity
        }
        self._alert_counter = 0

    def register_handler(self, handler: AlertHandler, severity: AlertSeverity):
        """Register an alert handler for a specific severity level.

        Args:
            handler: Alert handler implementation
            severity: Severity level to handle
        """
        if severity not in self.handlers:
            self.handlers[severity] = []
        self.handlers[severity].append(handler)

    async def create_alert(self,
                          title: str,
                          description: str,
                          severity: AlertSeverity,
                          source: str,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new alert.

        Args:
            title: Alert title
            description: Alert description
            severity: Alert severity level
            source: Alert source identifier
            metadata: Additional alert metadata

        Returns:
            ID of the created alert
        """
        self._alert_counter += 1
        alert_id = f"alert_{self._alert_counter}"

        alert = Alert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=severity,
            status=AlertStatus.NEW,
            source=source,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        self.alerts[alert_id] = alert
        await self._notify_handlers(alert)
        return alert_id

    async def acknowledge_alert(self,
                              alert_id: str,
                              acknowledgement: Dict[str, Any]):
        """Acknowledge an existing alert.

        Args:
            alert_id: ID of the alert to acknowledge
            acknowledgement: Acknowledgement details
        """
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledgement = acknowledgement
        await self._notify_handlers(alert)

    async def resolve_alert(self,
                           alert_id: str,
                           resolution: Dict[str, Any]):
        """Resolve an existing alert.

        Args:
            alert_id: ID of the alert to resolve
            resolution: Resolution details
        """
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolution = resolution
        await self._notify_handlers(alert)

    async def close_alert(self, alert_id: str):
        """Close an existing alert.

        Args:
            alert_id: ID of the alert to close
        """
        if alert_id not in self.alerts:
            raise ValueError(f"Alert {alert_id} not found")

        alert = self.alerts[alert_id]
        alert.status = AlertStatus.CLOSED
        await self._notify_handlers(alert)

    async def _notify_handlers(self, alert: Alert):
        """Notify all registered handlers for an alert.

        Args:
            alert: Alert to notify handlers about
        """
        handlers = self.handlers.get(alert.severity, [])
        await asyncio.gather(
            *(handler.handle_alert(alert) for handler in handlers)
        )

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (non-closed) alerts.

        Returns:
            List of active alerts
        """
        return [
            alert for alert in self.alerts.values()
            if alert.status != AlertStatus.CLOSED
        ]

    def get_alerts_by_severity(self,
                             severity: AlertSeverity) -> List[Alert]:
        """Get alerts filtered by severity level.

        Args:
            severity: Severity level to filter by

        Returns:
            List of alerts with the specified severity
        """
        return [
            alert for alert in self.alerts.values()
            if alert.severity == severity
        ]

    def get_alerts_by_status(self,
                            status: AlertStatus) -> List[Alert]:
        """Get alerts filtered by status.

        Args:
            status: Status to filter by

        Returns:
            List of alerts with the specified status
        """
        return [
            alert for alert in self.alerts.values()
            if alert.status == status
        ]
