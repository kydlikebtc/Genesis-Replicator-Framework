"""
Retry Manager Module

This module implements the retry management system for the Genesis Replicator Framework.
It provides functionality for handling failed operations and implementing retry strategies.
"""
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1

@dataclass
class RetryState:
    """Tracks the state of retry attempts"""
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    next_attempt: Optional[datetime] = None
    last_error: Optional[Exception] = None

class RetryManager:
    """
    Implements retry strategies for failed operations.

    Attributes:
        config (RetryConfig): Retry configuration
        state (Dict[str, RetryState]): State tracking for retry operations
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize the RetryManager.

        Args:
            config (Optional[RetryConfig]): Retry configuration
        """
        self.config = config or RetryConfig()
        self.state: Dict[str, RetryState] = {}
        logger.info("RetryManager initialized")

    def calculate_next_delay(self, attempts: int) -> float:
        """
        Calculate delay for next retry attempt using exponential backoff.

        Args:
            attempts (int): Number of attempts so far

        Returns:
            float: Delay in seconds before next attempt
        """
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** (attempts - 1)),
            self.config.max_delay
        )

        # Add jitter to prevent thundering herd
        jitter = delay * self.config.jitter
        return max(0, delay + (jitter * (2 * asyncio.get_event_loop().time() % 1 - 1)))

    async def execute_with_retry(
        self,
        operation_id: str,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            operation_id (str): Unique identifier for the operation
            operation (Callable): The operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Any: Result of the successful operation

        Raises:
            Exception: If all retry attempts fail
        """
        if operation_id not in self.state:
            self.state[operation_id] = RetryState()

        state = self.state[operation_id]

        while state.attempts < self.config.max_attempts:
            try:
                state.attempts += 1
                state.last_attempt = datetime.now()

                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)

                # Success - clear retry state
                del self.state[operation_id]
                return result

            except Exception as e:
                state.last_error = e
                logger.warning(
                    f"Operation {operation_id} failed (attempt {state.attempts}): {str(e)}"
                )

                if state.attempts >= self.config.max_attempts:
                    logger.error(
                        f"Operation {operation_id} failed after {state.attempts} attempts"
                    )
                    raise

                delay = self.calculate_next_delay(state.attempts)
                state.next_attempt = datetime.now() + timedelta(seconds=delay)
                await asyncio.sleep(delay)

    def get_retry_state(self, operation_id: str) -> Optional[RetryState]:
        """
        Get the current retry state for an operation.

        Args:
            operation_id (str): Operation identifier

        Returns:
            Optional[RetryState]: Current retry state or None if not found
        """
        return self.state.get(operation_id)

    def clear_retry_state(self, operation_id: str) -> None:
        """
        Clear retry state for an operation.

        Args:
            operation_id (str): Operation identifier
        """
        if operation_id in self.state:
            del self.state[operation_id]
            logger.info(f"Cleared retry state for operation {operation_id}")
