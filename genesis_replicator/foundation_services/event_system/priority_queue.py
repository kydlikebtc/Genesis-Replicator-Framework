"""
Priority Queue implementation for event system.

This module implements a priority-based queue for event processing.
"""
import asyncio
from typing import Any, Optional, Dict
from dataclasses import dataclass, field


@dataclass(order=True)
class PrioritizedItem:
    """Wrapper for items with priority."""
    priority: int
    sequence: int
    item: Any = field(compare=False)


class PriorityQueue:
    """Asynchronous priority queue implementation."""

    def __init__(self):
        """Initialize the priority queue."""
        self._queue = asyncio.PriorityQueue()
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._initialized = False

    async def start(self) -> None:
        """Initialize and start the priority queue."""
        if self._initialized:
            return

        async with self._lock:
            self._initialized = True
            self._sequence = 0

    async def stop(self) -> None:
        """Stop and cleanup the priority queue."""
        async with self._lock:
            while not self._queue.empty():
                await self._queue.get()
            self._initialized = False

    async def put(self, item: Any, priority: int = 0) -> None:
        """Put an item into the queue with priority.

        Args:
            item: Item to queue
            priority: Priority level (lower executes first)
        """
        if not self._initialized:
            raise RuntimeError("Priority queue not initialized")

        async with self._lock:
            self._sequence += 1
            await self._queue.put(PrioritizedItem(
                priority=priority,
                sequence=self._sequence,
                item=item
            ))

    async def get(self) -> Any:
        """Get the next item from the queue.

        Returns:
            Next item based on priority
        """
        if not self._initialized:
            raise RuntimeError("Priority queue not initialized")

        prioritized_item = await self._queue.get()
        return prioritized_item.item

    def is_running(self) -> bool:
        """Check if priority queue is running.

        Returns:
            True if initialized and running
        """
        return self._initialized

    async def size(self) -> int:
        """Get current queue size.

        Returns:
            Number of items in queue
        """
        return self._queue.qsize()

    async def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if queue is empty
        """
        return self._queue.empty()
