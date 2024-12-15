"""
Filter Chain implementation for event system.

This module implements a chain of filters for event processing and validation.
"""
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field


@dataclass
class Filter:
    """Represents a filter in the chain."""
    name: str
    func: Callable
    priority: int = 0


class FilterChain:
    """Manages a chain of filters for event processing."""

    def __init__(self):
        """Initialize the filter chain."""
        self._filters: Dict[str, Filter] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def start(self) -> None:
        """Initialize and start the filter chain."""
        if self._initialized:
            return

        async with self._lock:
            self._initialized = True
            self._filters.clear()

    async def stop(self) -> None:
        """Stop and cleanup the filter chain."""
        async with self._lock:
            self._filters.clear()
            self._initialized = False

    def add_filter(self, name: str, func: Callable, priority: int = 0) -> None:
        """Add a filter to the chain.

        Args:
            name: Filter identifier
            func: Filter function
            priority: Filter priority (lower executes first)
        """
        if not self._initialized:
            raise RuntimeError("Filter chain not initialized")
        self._filters[name] = Filter(name=name, func=func, priority=priority)

    def remove_filter(self, name: str) -> None:
        """Remove a filter from the chain.

        Args:
            name: Filter identifier
        """
        if not self._initialized:
            raise RuntimeError("Filter chain not initialized")
        if name in self._filters:
            del self._filters[name]

    def get_filters(self) -> List[str]:
        """Get list of filter names.

        Returns:
            List of filter identifiers
        """
        if not self._initialized:
            raise RuntimeError("Filter chain not initialized")
        return list(self._filters.keys())

    async def evaluate(self, event: Dict[str, Any]) -> bool:
        """Evaluate an event through the filter chain.

        Args:
            event: Event data to evaluate

        Returns:
            True if event passes all filters, False otherwise
        """
        if not self._initialized:
            raise RuntimeError("Filter chain not initialized")

        # Sort filters by priority
        sorted_filters = sorted(
            self._filters.values(),
            key=lambda x: x.priority
        )

        # Apply filters in order
        for filter_obj in sorted_filters:
            try:
                if not filter_obj.func(event):
                    return False
            except Exception as e:
                # Re-raise exceptions for proper error handling
                raise type(e)(
                    f"Error in filter '{filter_obj.name}': {str(e)}"
                ) from e

        return True

    def is_running(self) -> bool:
        """Check if filter chain is running.

        Returns:
            True if initialized and running
        """
        return self._initialized
