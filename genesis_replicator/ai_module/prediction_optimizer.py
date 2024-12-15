"""
Prediction Optimizer Module

This module optimizes model predictions and hyperparameters in the
Genesis Replicator Framework.
"""
from typing import Dict, Any, Optional, List, Tuple, Callable
import logging
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """Available optimization strategies."""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    EVOLUTIONARY = "evolutionary"

@dataclass
class OptimizationConfig:
    """Configuration for optimization process."""
    strategy: OptimizationStrategy
    parameter_space: Dict[str, Any]
    max_iterations: int
    evaluation_metric: str
    minimize: bool = True
    early_stopping: bool = True
    patience: int = 5

@dataclass
class OptimizationResult:
    """Results from an optimization run."""
    run_id: str
    best_params: Dict[str, Any]
    best_score: float
    history: List[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None

class PredictionOptimizer:
    """Optimizes model predictions and hyperparameters."""

    def __init__(self):
        """Initialize the PredictionOptimizer."""
        self.optimization_runs: Dict[str, OptimizationResult] = {}
        self.evaluation_functions: Dict[str, Callable] = {}
        logger.info("Prediction Optimizer initialized")

    def register_evaluation_function(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], float]
    ) -> None:
        """
        Register an evaluation function for optimization.

        Args:
            name: Name of the evaluation function
            func: Function that evaluates parameters and returns a score
        """
        self.evaluation_functions[name] = func
        logger.info(f"Registered evaluation function: {name}")

    def optimize(
        self,
        config: OptimizationConfig,
        evaluation_context: Dict[str, Any]
    ) -> str:
        """
        Start an optimization run.

        Args:
            config: Optimization configuration
            evaluation_context: Context for evaluation function

        Returns:
            Run ID for the optimization process
        """
        if config.evaluation_metric not in self.evaluation_functions:
            raise ValueError(
                f"Evaluation function '{config.evaluation_metric}' not registered"
            )

        run_id = f"opt-{int(datetime.now().timestamp())}"
        result = OptimizationResult(
            run_id=run_id,
            best_params={},
            best_score=float('inf') if config.minimize else float('-inf'),
            history=[],
            created_at=datetime.now()
        )
        self.optimization_runs[run_id] = result

        logger.info(f"Started optimization run: {run_id}")
        return run_id

    def update_optimization(
        self,
        run_id: str,
        params: Dict[str, Any],
        score: float
    ) -> bool:
        """
        Update optimization results with new evaluation.

        Args:
            run_id: ID of the optimization run
            params: Parameters that were evaluated
            score: Evaluation score

        Returns:
            True if new best score was found
        """
        if run_id not in self.optimization_runs:
            raise ValueError(f"Optimization run '{run_id}' not found")

        result = self.optimization_runs[run_id]
        is_better = (
            score < result.best_score
            if result.best_score != float('inf')
            else True
        )

        result.history.append({
            "params": params,
            "score": score,
            "timestamp": datetime.now()
        })

        if is_better:
            result.best_params = params
            result.best_score = score
            logger.info(f"New best score for run {run_id}: {score}")
            return True

        return False

    def complete_optimization(self, run_id: str) -> OptimizationResult:
        """
        Mark an optimization run as complete.

        Args:
            run_id: ID of the optimization run

        Returns:
            Final optimization results
        """
        if run_id not in self.optimization_runs:
            raise ValueError(f"Optimization run '{run_id}' not found")

        result = self.optimization_runs[run_id]
        result.completed_at = datetime.now()
        logger.info(f"Completed optimization run: {run_id}")
        return result

    def get_optimization_status(
        self,
        run_id: str
    ) -> Optional[OptimizationResult]:
        """
        Get the current status of an optimization run.

        Args:
            run_id: ID of the optimization run

        Returns:
            OptimizationResult if found, None otherwise
        """
        return self.optimization_runs.get(run_id)

    def list_optimization_runs(
        self,
        completed_only: bool = False
    ) -> List[OptimizationResult]:
        """
        List all optimization runs.

        Args:
            completed_only: If True, only return completed runs

        Returns:
            List of optimization results
        """
        runs = self.optimization_runs.values()
        if completed_only:
            runs = [r for r in runs if r.completed_at is not None]
        return list(runs)

    def get_best_parameters(
        self,
        run_id: str
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Get the best parameters found in an optimization run.

        Args:
            run_id: ID of the optimization run

        Returns:
            Tuple of (best parameters, best score) if found
        """
        result = self.optimization_runs.get(run_id)
        if not result or not result.best_params:
            return None
        return (result.best_params, result.best_score)
