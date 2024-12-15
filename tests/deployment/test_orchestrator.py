"""
Tests for deployment orchestrator.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from genesis_replicator.deployment.orchestrator import (
    DeploymentOrchestrator,
    DeploymentConfig,
    DeploymentStatus
)
from genesis_replicator.ai_module.model_registry import ModelRegistry, ModelState

@pytest.fixture
def model_registry():
    registry = Mock(spec=ModelRegistry)
    registry.get_model.return_value = {
        "version_id": "test-1.0",
        "state": ModelState.REGISTERED
    }
    return registry

@pytest.fixture
def metrics_collector():
    collector = Mock()
    collector.configure_monitoring = AsyncMock()
    collector.get_metrics = AsyncMock(return_value={"accuracy": 0.95})
    collector.remove_monitoring = AsyncMock()
    return collector

@pytest.fixture
def health_checker():
    checker = Mock()
    checker.configure_checks = AsyncMock()
    checker.check_health = AsyncMock(return_value="healthy")
    checker.remove_checks = AsyncMock()
    return checker

@pytest.fixture
def orchestrator(model_registry, metrics_collector, health_checker):
    return DeploymentOrchestrator(
        model_registry,
        metrics_collector,
        health_checker
    )

@pytest.fixture
def deployment_config():
    return DeploymentConfig(
        model_name="test-model",
        version_id="test-1.0",
        environment="production",
        resources={"cpu": "2", "memory": "4Gi"},
        scaling_config={"min_replicas": 1, "max_replicas": 3},
        monitoring_config={"metrics_interval": 60}
    )

@pytest.mark.asyncio
async def test_deploy_model(orchestrator, deployment_config):
    deployment_id = await orchestrator.deploy_model(deployment_config)
    assert deployment_id == "test-model-test-1.0-production"

    status = await orchestrator.get_deployment_status(deployment_id)
    assert status is not None
    assert status.status == "deployed"
    assert status.model_name == "test-model"
    assert status.version_id == "test-1.0"

@pytest.mark.asyncio
async def test_deploy_model_invalid_model(orchestrator, deployment_config):
    orchestrator._model_registry.get_model.return_value = None
    with pytest.raises(ValueError):
        await orchestrator.deploy_model(deployment_config)

@pytest.mark.asyncio
async def test_get_deployment_status(orchestrator, deployment_config):
    deployment_id = await orchestrator.deploy_model(deployment_config)
    status = await orchestrator.get_deployment_status(deployment_id)

    assert status is not None
    assert status.metrics == {"accuracy": 0.95}
    assert status.health_status == "healthy"

@pytest.mark.asyncio
async def test_list_deployments(orchestrator, deployment_config):
    await orchestrator.deploy_model(deployment_config)
    deployments = await orchestrator.list_deployments()
    assert len(deployments) == 1
    assert deployments[0].environment == "production"

@pytest.mark.asyncio
async def test_undeploy_model(orchestrator, deployment_config):
    deployment_id = await orchestrator.deploy_model(deployment_config)
    await orchestrator.undeploy_model(deployment_id)

    status = await orchestrator.get_deployment_status(deployment_id)
    assert status is None

@pytest.mark.asyncio
async def test_undeploy_nonexistent_model(orchestrator):
    with pytest.raises(ValueError):
        await orchestrator.undeploy_model("nonexistent-id")
