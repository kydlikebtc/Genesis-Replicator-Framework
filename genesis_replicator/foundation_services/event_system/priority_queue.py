"""
Priority Queue Module

This module implements the priority-based event queue system for the Genesis Replicator Framework.
It provides functionality for managing event priorities and queue optimization.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import heapq
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PrioritizedEvent:
    """Represents an event with priority information"""
    priority: int
    timestamp: datetime
    event_type: str
    event_data: dict

    def __lt__(self, other):
        """Compare events based on priority and timestamp"""
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority > other.priority

class PriorityQueue:
    """
    Implements priority-based event queue with resource management.

    Attributes:
        queue (List): Priority queue for events
        capacity (int): Maximum queue capacity
        processing (bool): Flag indicating if queue is being processed
    """

    def __init__(self, capacity: int = 1000):
        """
        Initialize the PriorityQueue.

        Args:
            capacity (int): Maximum number of events in queue
        """
        self._queue: List[PrioritizedEvent] = []
        self.capacity = capacity
        self.processing = False
        self._resource_limits: Dict[str, int] = {}
        self._current_resources: Dict[str, int] = {}
        logger.info(f"PriorityQueue initialized with capacity {capacity}")


    async def enqueue(self, event: PrioritizedEvent) -> bool:
        """
        Add an event to the queue with priority handling.

        Args:
            event (PrioritizedEvent): Event to enqueue

        Returns:
            bool: True if event was enqueued successfully
        """
        if len(self._queue) >= self.capacity:
            logger.warning("Queue at capacity, checking for priority replacement")
            if self._queue[0].priority < event.priority:
                heapq.heappop(self._queue)
            else:
                logger.warning("Event rejected due to lower priority")
                return False

        heapq.heappush(self._queue, event)
        logger.info(f"Enqueued event of type {event.event_type} with priority {event.priority}")
        return True

    async def dequeue(self) -> Optional[PrioritizedEvent]:
        """
        Remove and return the highest priority event from the queue.

        Returns:
            Optional[PrioritizedEvent]: The highest priority event or None if queue is empty
        """
        if not self._queue:
            return None

        event = heapq.heappop(self._queue)
        logger.info(f"Dequeued event of type {event.event_type}")
        return event

    def set_resource_limit(self, resource_type: str, limit: int) -> None:
        """
        Set resource limit for a specific resource type.

        Args:
            resource_type (str): Type of resource
            limit (int): Maximum allowed resources
        """
        self._resource_limits[resource_type] = limit
        self._current_resources.setdefault(resource_type, 0)
        logger.info(f"Set resource limit for {resource_type}: {limit}")

    def allocate_resources(self, resource_type: str, amount: int = 1) -> bool:
        """
        Attempt to allocate resources for event processing.

        Args:
            resource_type (str): Type of resource
            amount (int): Amount of resources to allocate

        Returns:
            bool: True if resources were allocated successfully
        """
        if resource_type not in self._resource_limits:
            return True

        current = self._current_resources[resource_type]
        limit = self._resource_limits[resource_type]

        if current + amount <= limit:
            self._current_resources[resource_type] = current + amount
            return True
        return False

    def release_resources(self, resource_type: str, amount: int = 1) -> None:
        """
        Release allocated resources after event processing.

        Args:
            resource_type (str): Type of resource
            amount (int): Amount of resources to release
        """
        if resource_type in self._current_resources:
            self._current_resources[resource_type] = max(
                0, self._current_resources[resource_type] - amount
            )

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get current queue statistics.

        Returns:
            Dict[str, Any]: Queue statistics including size and resource usage
        """
        return {
            "size": len(self._queue),
            "capacity": self.capacity,
            "resources": self._current_resources.copy()
        }
