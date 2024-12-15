"""
Deployment orchestrator for managing model deployments across environments.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..ai_module.model_registry import ModelRegistry, ModelState
from ..monitoring.metrics_collector import MetricsCollector
from ..monitoring.health_checker import HealthChecker

logger = logging.getLogger(__name__)

@dataclass
class DeploymentConfig:
    """Configuration for model deployment."""
    model_name: str
    version_id: str
    environment: str
    resources: Dict[str, Any]
    scaling_config: Dict[str, Any]
    monitoring_config: Dict[str, Any]

@dataclass
class DeploymentStatus:
    """Status of a model deployment."""
    deployment_id: str
    model_name: str
    version_id: str
    environment: str
    status: str
    health_status: str
    created_at: datetime
    updated_at: datetime
    metrics: Dict[str, float]

class DeploymentOrchestrator:
    """Manages model deployments across environments."""

    def __init__(
        self,
        model_registry: ModelRegistry,
        metrics_collector: MetricsCollector,
        health_checker: HealthChecker
    ):
        """Initialize deployment orchestrator.

        Args:
            model_registry: Model registry instance
            metrics_collector: Metrics collector instance
            health_checker: Health checker instance
        """
        self._model_registry = model_registry
        self._metrics_collector = metrics_collector
        self._health_checker = health_checker
        self._deployments: Dict[str, DeploymentStatus] = {}
        self._lock = asyncio.Lock()
        logger.info("Deployment orchestrator initialized")

    async def deploy_model(
        self,
        config: DeploymentConfig
    ) -> str:
        """Deploy a model to the specified environment.

        Args:
            config: Deployment configuration

        Returns:
            Deployment ID

        Raises:
            ValueError: If model or version not found
            RuntimeError: If deployment fails
        """
        try:
            # Validate model and version
            model_version = self._model_registry.get_model(
                config.model_name,
                config.version_id
            )
            if not model_version:
                raise ValueError(
                    f"Model {config.model_name} version {config.version_id} not found"
                )

            # Create deployment ID
            deployment_id = f"{config.model_name}-{config.version_id}-{config.environment}"

            async with self._lock:
                # Create deployment status
                status = DeploymentStatus(
                    deployment_id=deployment_id,
                    model_name=config.model_name,
                    version_id=config.version_id,
                    environment=config.environment,
                    status="deploying",
                    health_status="unknown",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    metrics={}
                )
                self._deployments[deployment_id] = status

                try:
                    # Configure monitoring
                    await self._metrics_collector.configure_monitoring(
                        deployment_id,
                        config.monitoring_config
                    )

                    # Configure health checks
                    await self._health_checker.configure_checks(
                        deployment_id,
                        config.monitoring_config
                    )

                    # Update model state
                    self._model_registry.update_model_state(
                        config.model_name,
                        config.version_id,
                        ModelState.PRODUCTION
                    )

                    # Update deployment status
                    status.status = "deployed"
                    status.updated_at = datetime.now()
                    logger.info(f"Model deployed successfully: {deployment_id}")
                    return deployment_id

                except Exception as e:
                    status.status = "failed"
                    status.updated_at = datetime.now()
                    logger.error(f"Deployment failed: {str(e)}")
                    raise RuntimeError(f"Deployment failed: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to deploy model: {str(e)}")
            raise

    async def get_deployment_status(
        self,
        deployment_id: str
    ) -> Optional[DeploymentStatus]:
        """Get status of a deployment.

        Args:
            deployment_id: Deployment identifier

        Returns:
            DeploymentStatus if found, None otherwise
        """
        status = self._deployments.get(deployment_id)
        if not status:
            return None

        # Update metrics
        try:
            metrics = await self._metrics_collector.get_metrics(deployment_id)
            health = await self._health_checker.check_health(deployment_id)
            status.metrics = metrics
            status.health_status = health
            status.updated_at = datetime.now()
        except Exception as e:
            logger.error(f"Failed to update deployment status: {str(e)}")

        return status

    async def list_deployments(
        self,
        environment: Optional[str] = None
    ) -> List[DeploymentStatus]:
        """List all deployments, optionally filtered by environment.

        Args:
            environment: Optional environment to filter by

        Returns:
            List of deployment statuses
        """
        deployments = list(self._deployments.values())
        if environment:
            deployments = [d for d in deployments if d.environment == environment]
        return deployments

    async def undeploy_model(
        self,
        deployment_id: str
    ) -> None:
        """Undeploy a model.

        Args:
            deployment_id: Deployment identifier

        Raises:
            ValueError: If deployment not found
            RuntimeError: If undeployment fails
        """
        if deployment_id not in self._deployments:
            raise ValueError(f"Deployment {deployment_id} not found")

        try:
            status = self._deployments[deployment_id]
            status.status = "undeploying"
            status.updated_at = datetime.now()

            # Clean up monitoring
            await self._metrics_collector.remove_monitoring(deployment_id)
            await self._health_checker.remove_checks(deployment_id)

            # Update model state
            self._model_registry.update_model_state(
                status.model_name,
                status.version_id,
                ModelState.ARCHIVED
            )

            # Remove deployment
            del self._deployments[deployment_id]
            logger.info(f"Model undeployed successfully: {deployment_id}")

        except Exception as e:
            logger.error(f"Failed to undeploy model: {str(e)}")
            raise RuntimeError(f"Undeployment failed: {str(e)}")
