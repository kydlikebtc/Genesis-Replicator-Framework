# Monitoring System API Reference

## Overview
The monitoring system provides real-time metrics collection, health checks, and alerting capabilities for the Genesis Replicator Framework.

## Components

### MetricsCollector
```python
class MetricsCollector:
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect system-wide metrics."""

    async def store_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Store collected metrics."""
```

### HealthChecker
```python
class HealthChecker:
    async def check_health(self, component_id: str) -> HealthStatus:
        """Check health of a specific component."""

    async def get_system_health(self) -> Dict[str, HealthStatus]:
        """Get overall system health status."""
```

### AlertManager
```python
class AlertManager:
    async def create_alert(self, alert: Alert) -> str:
        """Create a new alert."""

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an existing alert."""
```

## Usage Examples
```python
# Initialize monitoring
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
alert_manager = AlertManager()

# Collect and store metrics
metrics = await metrics_collector.collect_metrics()
await metrics_collector.store_metrics(metrics)

# Check system health
health = await health_checker.get_system_health()

# Create and resolve alerts
alert_id = await alert_manager.create_alert(alert)
await alert_manager.resolve_alert(alert_id)
```
