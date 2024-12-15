"""
Event Router Implementation for Genesis Replicator Framework

This module implements the core event routing system that enables communication
between different components of the framework through a publish-subscribe pattern.
"""

from typing import Any, Callable, Dict, List, Optional, Set
import logging
import asyncio
from dataclasses import dataclass, field

from ..exceptions import (
    EventNotFoundError,
    EventHandlerError,
    EventRouterError,
    EventValidationError
)

logger = logging.getLogger(__name__)

@dataclass
class Subscription:
    """Represents a subscription to an event type."""
    callback: Callable
    event_type: str
    subscriber_id: str

@dataclass
class EventRouter:
    """
    Core event routing system implementing the publish-subscribe pattern.

    Handles event subscription, publishing, and routing between framework components.
    """
    _subscriptions: Dict[str, Set[Subscription]] = field(default_factory=dict)
    _running: bool = False
    _event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def start(self):
        """Start the event router."""
        if self._running:
            logger.warning("Event router is already running")
            return

        self._running = True
        logger.info("Event router started")

    async def stop(self):
        """Stop the event router."""
        if not self._running:
            logger.warning("Event router is not running")
            return

        self._running = False
        logger.info("Event router stopped")

    def subscribe(self, event_type: str, callback: Callable, subscriber_id: str) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            subscriber_id: Unique identifier for the subscriber

        Raises:
            EventValidationError: If event_type or subscriber_id is invalid
        """
        if not event_type or not isinstance(event_type, str):
            raise EventValidationError("Invalid event type",
                                     details={"event_type": event_type})

        if not subscriber_id or not isinstance(subscriber_id, str):
            raise EventValidationError("Invalid subscriber ID",
                                     details={"subscriber_id": subscriber_id})

        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = set()

        subscription = Subscription(callback, event_type, subscriber_id)
        self._subscriptions[event_type].add(subscription)
        logger.info(f"Added subscription for {event_type} from {subscriber_id}")

    def unsubscribe(self, event_type: str, subscriber_id: str) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            subscriber_id: Unique identifier for the subscriber

        Raises:
            EventNotFoundError: If event_type doesn't exist
        """
        if event_type not in self._subscriptions:
            raise EventNotFoundError(event_type)

        self._subscriptions[event_type] = {
            sub for sub in self._subscriptions[event_type]
            if sub.subscriber_id != subscriber_id
        }
        logger.info(f"Removed subscription for {event_type} from {subscriber_id}")

    async def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event to publish
            data: Data to send with the event

        Raises:
            EventRouterError: If router is not running
            EventNotFoundError: If no subscribers exist for event_type
        """
        if not self._running:
            raise EventRouterError("Cannot publish event: Event router is not running")

        if event_type not in self._subscriptions:
            raise EventNotFoundError(event_type)

        await self._event_queue.put((event_type, data))
        logger.debug(f"Published event {event_type}")

    async def process_events(self) -> None:
        """
        Process events from the event queue.

        Raises:
            EventHandlerError: If a subscriber callback fails
            EventRouterError: If event processing fails
        """
        while self._running:
            try:
                event_type, data = await self._event_queue.get()
                subscribers = self._subscriptions.get(event_type, set())

                for subscription in subscribers:
                    try:
                        await subscription.callback(data)
                    except Exception as e:
                        error_details = {
                            "event_type": event_type,
                            "subscriber_id": subscription.subscriber_id,
                            "error": str(e)
                        }
                        logger.error(f"Error in subscriber callback: {error_details}")
                        raise EventHandlerError(
                            f"Subscriber callback failed: {str(e)}",
                            details=error_details
                        )

                self._event_queue.task_done()

            except Exception as e:
                error_details = {"error": str(e)}
                logger.error(f"Error processing event: {error_details}")
                raise EventRouterError(
                    f"Event processing failed: {str(e)}",
                    details=error_details
                )

    def get_subscribers(self, event_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get all subscribers, optionally filtered by event type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            Dictionary mapping event types to lists of subscriber IDs

        Raises:
            EventNotFoundError: If specified event_type doesn't exist
        """
        result = {}

        if event_type:
            if event_type not in self._subscriptions:
                raise EventNotFoundError(event_type)
            result[event_type] = [
                sub.subscriber_id
                for sub in self._subscriptions[event_type]
            ]
        else:
            for evt_type, subscriptions in self._subscriptions.items():
                result[evt_type] = [
                    sub.subscriber_id
                    for sub in subscriptions
                ]

        return result
