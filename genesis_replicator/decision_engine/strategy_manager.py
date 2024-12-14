"""
Strategy Manager Module

This module manages decision-making strategies in the Genesis Replicator Framework.
It provides functionality for registering, managing, and executing strategies.
"""
from typing import Dict, Callable, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StrategyMetadata:
    """Metadata for registered strategies."""
    name: str
    description: str
    created_at: datetime
    parameters: Dict[str, Any]
    version: str

class StrategyManager:
    """Manages decision-making strategies for agents."""

    def __init__(self):
        """Initialize the StrategyManager."""
        self.strategies: Dict[str, Callable] = {}
        self.metadata: Dict[str, StrategyMetadata] = {}
        logger.info("Strategy Manager initialized")

    def register_strategy(
        self,
        name: str,
        strategy_function: Callable,
        description: str = "",
        parameters: Dict[str, Any] = None,
        version: str = "1.0.0"
    ) -> None:
        """
        Register a new strategy with metadata.

        Args:
            name: Unique identifier for the strategy
            strategy_function: The strategy implementation
            description: Description of the strategy
            parameters: Required parameters for the strategy
            version: Version of the strategy
        """
        if name in self.strategies:
            raise ValueError(f"Strategy '{name}' already exists")

        self.strategies[name] = strategy_function
        self.metadata[name] = StrategyMetadata(
            name=name,
            description=description,
            created_at=datetime.now(),
            parameters=parameters or {},
            version=version
        )
        logger.info(f"Registered strategy: {name} (v{version})")

    def execute_strategy(
        self,
        name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Any:
        """
        Execute a registered strategy.

        Args:
            name: Name of the strategy to execute
            context: Execution context for the strategy
            **kwargs: Additional parameters for the strategy

        Returns:
            Result of the strategy execution
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")

        try:
            logger.debug(f"Executing strategy: {name}")
            result = self.strategies[name](context, **kwargs)
            logger.debug(f"Strategy {name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing strategy {name}: {str(e)}")
            raise

    def list_strategies(self) -> List[StrategyMetadata]:
        """
        List all registered strategies with their metadata.

        Returns:
            List of strategy metadata
        """
        return list(self.metadata.values())

    def get_strategy_metadata(self, name: str) -> Optional[StrategyMetadata]:
        """
        Get metadata for a specific strategy.

        Args:
            name: Name of the strategy

        Returns:
            Strategy metadata if found, None otherwise
        """
        return self.metadata.get(name)

    def remove_strategy(self, name: str) -> None:
        """
        Remove a registered strategy.

        Args:
            name: Name of the strategy to remove
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")

        del self.strategies[name]
        del self.metadata[name]
        logger.info(f"Removed strategy: {name}")

    def update_strategy(
        self,
        name: str,
        strategy_function: Optional[Callable] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None
    ) -> None:
        """
        Update an existing strategy and its metadata.

        Args:
            name: Name of the strategy to update
            strategy_function: New strategy implementation (optional)
            description: New description (optional)
            parameters: New parameters (optional)
            version: New version (optional)
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")

        if strategy_function:
            self.strategies[name] = strategy_function

        metadata = self.metadata[name]
        if description:
            metadata.description = description
        if parameters:
            metadata.parameters = parameters
        if version:
            metadata.version = version

        logger.info(f"Updated strategy: {name}")
