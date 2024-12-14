"""
Model Registry Module

This module manages AI model registration, versioning, and lifecycle management
in the Genesis Replicator Framework.
"""
from typing import Dict, Any, Optional, List, Union
import logging
from dataclasses import dataclass
from datetime import datetime
import json
from enum import Enum
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelState(Enum):
    """Represents the possible states of a model in its lifecycle."""
    REGISTERED = "registered"
    TRAINING = "training"
    TESTING = "testing"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

@dataclass
class ModelVersion:
    """Represents a specific version of a model."""
    version_id: str
    created_at: datetime
    metadata: Dict[str, Any]
    checksum: str
    state: ModelState
    performance_metrics: Dict[str, float]

@dataclass
class ModelInfo:
    """Contains information about a registered model."""
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    versions: Dict[str, ModelVersion]
    current_version: Optional[str]
    tags: List[str]

class ModelRegistry:
    """Manages AI model registration, versioning, and lifecycle."""

    def __init__(self):
        """Initialize the ModelRegistry."""
        self.models: Dict[str, ModelInfo] = {}
        logger.info("Model Registry initialized")

    def register_model(
        self,
        name: str,
        model_instance: Any,
        description: str = "",
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
        version: str = "1.0.0"
    ) -> str:
        """
        Register a new model or new version of existing model.

        Args:
            name: Unique identifier for the model
            model_instance: The model object to register
            description: Description of the model
            metadata: Additional model metadata
            tags: List of tags for the model
            version: Version string for this model instance

        Returns:
            Version ID of the registered model
        """
        metadata = metadata or {}
        tags = tags or []

        # Generate checksum for model instance
        model_bytes = json.dumps(str(model_instance.__dict__)).encode()
        checksum = hashlib.sha256(model_bytes).hexdigest()

        # Create version info
        version_id = f"{name}-{version}-{checksum[:8]}"
        model_version = ModelVersion(
            version_id=version_id,
            created_at=datetime.now(),
            metadata=metadata,
            checksum=checksum,
            state=ModelState.REGISTERED,
            performance_metrics={}
        )

        if name in self.models:
            # Update existing model
            model_info = self.models[name]
            model_info.versions[version_id] = model_version
            model_info.updated_at = datetime.now()
            model_info.tags.extend([tag for tag in tags if tag not in model_info.tags])
        else:
            # Create new model entry
            model_info = ModelInfo(
                name=name,
                description=description,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                versions={version_id: model_version},
                current_version=version_id,
                tags=tags
            )
            self.models[name] = model_info

        logger.info(f"Registered model: {name} (version: {version_id})")
        return version_id

    def get_model(
        self,
        name: str,
        version_id: Optional[str] = None
    ) -> Optional[ModelVersion]:
        """
        Retrieve a specific model version.

        Args:
            name: Name of the model
            version_id: Specific version to retrieve (None for current version)

        Returns:
            ModelVersion if found, None otherwise
        """
        if name not in self.models:
            return None

        model_info = self.models[name]
        if version_id is None:
            version_id = model_info.current_version

        return model_info.versions.get(version_id)

    def update_model_state(
        self,
        name: str,
        version_id: str,
        state: ModelState
    ) -> None:
        """
        Update the state of a model version.

        Args:
            name: Name of the model
            version_id: Version ID to update
            state: New state for the model
        """
        if name not in self.models:
            raise ValueError(f"Model '{name}' not found")

        model_info = self.models[name]
        if version_id not in model_info.versions:
            raise ValueError(f"Version '{version_id}' not found for model '{name}'")

        model_info.versions[version_id].state = state
        logger.info(f"Updated model {name} ({version_id}) state to: {state.value}")

    def set_current_version(self, name: str, version_id: str) -> None:
        """
        Set the current version for a model.

        Args:
            name: Name of the model
            version_id: Version ID to set as current
        """
        if name not in self.models:
            raise ValueError(f"Model '{name}' not found")

        model_info = self.models[name]
        if version_id not in model_info.versions:
            raise ValueError(f"Version '{version_id}' not found for model '{name}'")

        model_info.current_version = version_id
        logger.info(f"Set current version for {name} to: {version_id}")

    def update_performance_metrics(
        self,
        name: str,
        version_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """
        Update performance metrics for a model version.

        Args:
            name: Name of the model
            version_id: Version ID to update
            metrics: Dictionary of performance metrics
        """
        if name not in self.models:
            raise ValueError(f"Model '{name}' not found")

        model_info = self.models[name]
        if version_id not in model_info.versions:
            raise ValueError(f"Version '{version_id}' not found for model '{name}'")

        model_version = model_info.versions[version_id]
        model_version.performance_metrics.update(metrics)
        logger.info(f"Updated performance metrics for {name} ({version_id})")

    def list_models(
        self,
        tag: Optional[str] = None,
        state: Optional[ModelState] = None
    ) -> List[ModelInfo]:
        """
        List all registered models, optionally filtered by tag or state.

        Args:
            tag: Optional tag to filter by
            state: Optional state to filter by

        Returns:
            List of matching ModelInfo objects
        """
        models = self.models.values()

        if tag:
            models = [m for m in models if tag in m.tags]

        if state:
            models = [
                m for m in models
                if any(v.state == state for v in m.versions.values())
            ]

        return list(models)

    def get_model_history(
        self,
        name: str
    ) -> List[Dict[str, Any]]:
        """
        Get the version history of a model.

        Args:
            name: Name of the model

        Returns:
            List of version histories with timestamps and states
        """
        if name not in self.models:
            raise ValueError(f"Model '{name}' not found")

        model_info = self.models[name]
        history = []

        for version_id, version in model_info.versions.items():
            history.append({
                "version_id": version_id,
                "created_at": version.created_at,
                "state": version.state.value,
                "metrics": version.performance_metrics,
                "metadata": version.metadata
            })

        return sorted(history, key=lambda x: x["created_at"])
