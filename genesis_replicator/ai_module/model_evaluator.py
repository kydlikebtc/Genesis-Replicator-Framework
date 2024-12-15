"""
Model Evaluator Module

This module provides comprehensive model evaluation capabilities in the
Genesis Replicator Framework.
"""
from typing import Dict, Any, Optional, List, Callable, Union
import logging
from dataclasses import dataclass
from datetime import datetime
import json
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvaluationMetric(Enum):
    """Standard evaluation metrics."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    MSE = "mse"
    MAE = "mae"
    CUSTOM = "custom"

@dataclass
class EvaluationConfig:
    """Configuration for model evaluation."""
    model_name: str
    version_id: str
    metrics: List[Union[EvaluationMetric, str]]
    dataset_config: Dict[str, Any]
    batch_size: int = 32

@dataclass
class EvaluationResult:
    """Results from a model evaluation."""
    eval_id: str
    model_name: str
    version_id: str
    metrics: Dict[str, float]
    created_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

class ModelEvaluator:
    """Provides comprehensive model evaluation capabilities."""

    def __init__(self):
        """Initialize the ModelEvaluator."""
        self.evaluations: Dict[str, EvaluationResult] = {}
        self.custom_metrics: Dict[str, Callable] = {}
        logger.info("Model Evaluator initialized")

    def register_custom_metric(
        self,
        name: str,
        metric_func: Callable[[Any, Any], float]
    ) -> None:
        """
        Register a custom evaluation metric.

        Args:
            name: Name of the custom metric
            metric_func: Function implementing the metric
        """
        self.custom_metrics[name] = metric_func
        logger.info(f"Registered custom metric: {name}")

    def start_evaluation(
        self,
        config: EvaluationConfig,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Start a model evaluation.

        Args:
            config: Evaluation configuration
            metadata: Additional evaluation metadata

        Returns:
            Evaluation ID
        """
        eval_id = f"eval-{config.model_name}-{int(datetime.now().timestamp())}"

        result = EvaluationResult(
            eval_id=eval_id,
            model_name=config.model_name,
            version_id=config.version_id,
            metrics={},
            created_at=datetime.now(),
            metadata=metadata or {}
        )

        self.evaluations[eval_id] = result
        logger.info(f"Started evaluation: {eval_id}")
        return eval_id

    def update_metrics(
        self,
        eval_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """
        Update metrics for an evaluation.

        Args:
            eval_id: ID of the evaluation
            metrics: Dictionary of metric values
        """
        if eval_id not in self.evaluations:
            raise ValueError(f"Evaluation '{eval_id}' not found")

        result = self.evaluations[eval_id]
        result.metrics.update(metrics)
        logger.info(f"Updated metrics for evaluation: {eval_id}")

    def complete_evaluation(
        self,
        eval_id: str,
        final_metrics: Optional[Dict[str, float]] = None
    ) -> EvaluationResult:
        """
        Mark an evaluation as complete.

        Args:
            eval_id: ID of the evaluation
            final_metrics: Final evaluation metrics

        Returns:
            Complete evaluation results
        """
        if eval_id not in self.evaluations:
            raise ValueError(f"Evaluation '{eval_id}' not found")

        result = self.evaluations[eval_id]
        if final_metrics:
            result.metrics.update(final_metrics)
        result.completed_at = datetime.now()
        logger.info(f"Completed evaluation: {eval_id}")
        return result

    def get_evaluation_status(
        self,
        eval_id: str
    ) -> Optional[EvaluationResult]:
        """
        Get the status of an evaluation.

        Args:
            eval_id: ID of the evaluation

        Returns:
            EvaluationResult if found, None otherwise
        """
        return self.evaluations.get(eval_id)

    def list_evaluations(
        self,
        model_name: Optional[str] = None,
        completed_only: bool = False
    ) -> List[EvaluationResult]:
        """
        List all evaluations.

        Args:
            model_name: Optional model name to filter by
            completed_only: If True, only return completed evaluations

        Returns:
            List of evaluation results
        """
        evals = self.evaluations.values()

        if model_name:
            evals = [e for e in evals if e.model_name == model_name]

        if completed_only:
            evals = [e for e in evals if e.completed_at is not None]

        return list(evals)

    def compare_evaluations(
        self,
        eval_ids: List[str],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare multiple evaluations.

        Args:
            eval_ids: List of evaluation IDs to compare
            metrics: Optional list of metrics to compare

        Returns:
            Dictionary comparing evaluation results
        """
        comparison = {}
        for eval_id in eval_ids:
            if eval_id not in self.evaluations:
                raise ValueError(f"Evaluation '{eval_id}' not found")

            result = self.evaluations[eval_id]
            if metrics:
                comparison[eval_id] = {
                    k: v for k, v in result.metrics.items() if k in metrics
                }
            else:
                comparison[eval_id] = result.metrics

        return comparison

    def export_evaluation(
        self,
        eval_id: str,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export evaluation results in a serializable format.

        Args:
            eval_id: ID of the evaluation to export
            include_metadata: Whether to include metadata

        Returns:
            Dictionary containing evaluation data
        """
        if eval_id not in self.evaluations:
            raise ValueError(f"Evaluation '{eval_id}' not found")

        result = self.evaluations[eval_id]
        export_data = {
            "eval_id": result.eval_id,
            "model_name": result.model_name,
            "version_id": result.version_id,
            "metrics": result.metrics,
            "created_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None
        }

        if include_metadata and result.metadata:
            export_data["metadata"] = result.metadata

        return export_data
