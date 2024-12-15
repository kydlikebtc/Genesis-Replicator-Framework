"""
Retry Manager for event system.

This module manages retry operations with configurable backoff strategies.
"""
import asyncio
import logging
from typing import Dict, Optional, Any, Callable, Awaitable
from dataclasses import dataclass


@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_factor: float = 2.0
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None


class RetryManager:
    """Manages retry operations with configurable strategies."""

    def __init__(self):
        """Initialize the retry manager."""
        self._lock = asyncio.Lock()
        self._initialized = False
        self._logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Initialize and start the retry manager."""
        if self._initialized:
            return

        async with self._lock:
            self._initialized = True

    async def stop(self) -> None:
        """Stop and cleanup the retry manager."""
        async with self._lock:
            self._initialized = False

    async def retry_operation(
        self,
        operation: Callable[[], Awaitable[Any]],
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None
    ) -> Any:
        """Execute operation with retry logic.

        Args:
            operation: Async operation to retry
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
            backoff_factor: Multiplier for subsequent delays
            on_success: Optional callback for successful operation
            on_failure: Optional callback for final failure

        Returns:
            Operation result

        Raises:
            Exception: If operation fails after all retries
        """
        if not self._initialized:
            raise RuntimeError("Retry manager not initialized")

        attempt = 0
        last_error = None
        current_delay = retry_delay

        while attempt <= max_retries:
            try:
                result = await operation()
                if on_success:
                    on_success(result)
                return result

            except Exception as e:
                attempt += 1
                last_error = e

                if attempt <= max_retries:
                    self._logger.warning(
                        f"Retry attempt {attempt}/{max_retries} failed: {str(e)}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
                else:
                    if on_failure:
                        on_failure(e)
                    raise

    def is_running(self) -> bool:
        """Check if retry manager is running.

        Returns:
            True if initialized and running
        """
        return self._initialized
