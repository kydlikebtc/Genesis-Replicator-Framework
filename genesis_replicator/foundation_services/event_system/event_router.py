"""
Event Router Module

This module implements the core event routing system for the Genesis Replicator Framework.
It provides functionality for event subscription and publishing, supporting the event-driven
architecture of the system.
"""
from typing import Callable, Dict, List
import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging

from .filter_chain import FilterChain, FilterRule
from .priority_queue import PriorityQueue, PrioritizedEvent
from .retry_manager import RetryManager, RetryConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Event:
    """Represents an event in the system"""
    type: str
    data: dict
    timestamp: datetime = datetime.now()
    priority: int = 0

class EventRouter:
    """
    Core event routing system that manages subscriptions and event publishing.

    Attributes:
        subscribers (Dict[str, List[Callable]]): Maps event types to their handlers
        filter_chain (FilterChain): Handles event filtering
        priority_queue (PriorityQueue): Manages event priorities
        retry_manager (RetryManager): Handles retry logic for failed events
    """

    def __init__(self, queue_capacity: int = 1000):
        """Initialize the EventRouter with all required components"""
        self.subscribers: Dict[str, List[Callable]] = {}
        self.filter_chain = FilterChain()
        self.priority_queue = PriorityQueue(capacity=queue_capacity)
        self.retry_manager = RetryManager(RetryConfig())
        self._processing = False
        logger.info("EventRouter initialized with all components")

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type (str): The type of event to subscribe to
            handler (Callable): The function to handle the event
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.info(f"Handler subscribed to event type: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        Unsubscribe a handler from a specific event type.

        Args:
            event_type (str): The type of event to unsubscribe from
            handler (Callable): The handler to remove
        """
        if event_type in self.subscribers and handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            logger.info(f"Handler unsubscribed from event type: {event_type}")

    async def publish_event(self, event: Event) -> None:
        """
        Publish an event to all subscribed handlers asynchronously.

        Args:
            event (Event): The event to publish
        """
        # Apply filter chain
        if not self.filter_chain.apply_filters(event.type, event.data):
            logger.info(f"Event {event.type} filtered out")
            return

        # Create prioritized event and add to queue
        prioritized_event = PrioritizedEvent(
            priority=event.priority,
            timestamp=event.timestamp,
            event_type=event.type,
            event_data=event.data
        )

        if await self.priority_queue.enqueue(prioritized_event):
            logger.info(f"Event of type {event.type} queued for processing")

            # Start processing if not already running
            if not self._processing:
                asyncio.create_task(self.process_events())
        else:
            logger.warning(f"Failed to enqueue event of type {event.type}")

    async def process_events(self) -> None:
        """Process events from the queue continuously"""
        self._processing = True

        try:
            while True:
                event = await self.priority_queue.dequeue()
                if not event:
                    # No more events in queue
                    break

                if event.event_type in self.subscribers:
                    for handler in self.subscribers[event.event_type]:
                        operation_id = f"{event.event_type}_{event.timestamp.isoformat()}"
                        try:
                            await self.retry_manager.execute_with_retry(
                                operation_id,
                                self._execute_handler,
                                handler,
                                event.event_data
                            )
                        except Exception as e:
                            logger.error(f"Failed to process event {event.event_type} after retries: {str(e)}")
        finally:
            self._processing = False

    async def _execute_handler(self, handler: Callable, event_data: dict) -> None:
        """
        Execute an event handler with proper error handling.

        Args:
            handler (Callable): The handler to execute
            event_data (dict): The event data to process
        """
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_data)
            else:
                handler(event_data)
            logger.debug(f"Handler executed successfully")
        except Exception as e:
            logger.error(f"Handler execution failed: {str(e)}")
            raise

    def add_filter(self, pattern: str, condition: Callable = None, priority: int = 0) -> None:
        """
        Add a filter rule to the filter chain.

        Args:
            pattern (str): Event type pattern to match
            condition (Callable, optional): Additional filtering condition
            priority (int, optional): Filter priority
        """
        filter_rule = FilterRule(
            pattern=pattern,
            condition=condition,
            priority=priority,
            description=f"Filter for pattern: {pattern}"
        )
        self.filter_chain.add_filter(filter_rule)

    def set_resource_limit(self, resource_type: str, limit: int) -> None:
        """
        Set resource limit for event processing.

        Args:
            resource_type (str): Type of resource
            limit (int): Maximum allowed resources
        """
        self.priority_queue.set_resource_limit(resource_type, limit)

    def get_queue_stats(self) -> dict:
        """
        Get current queue statistics.

        Returns:
            dict: Queue statistics
        """
        return self.priority_queue.get_queue_stats()
