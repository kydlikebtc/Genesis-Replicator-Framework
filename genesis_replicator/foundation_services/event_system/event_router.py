"""
Event Router Module

This module implements the core event routing system for the Genesis Replicator Framework.
It provides functionality for event subscription, routing, and distribution.
"""
from typing import Any, Callable, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    """Represents an event in the system."""
    event_type: str
    data: Any
    timestamp: datetime = datetime.utcnow()
    priority: int = 0
    source: str = ""


class EventRouter:
    """
    Implements event routing logic and manages subscription patterns.
    Ensures reliable event delivery and distribution.
    """

    def __init__(self):
        """Initialize the event router with empty subscribers dictionary."""
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._active = True

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> bool:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle the event

        Returns:
            bool: True if subscription was successful
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if handler not in self.subscribers[event_type]:
            self.subscribers[event_type].append(handler)
            return True
        return False

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> bool:
        """
        Unsubscribe a handler from a specific event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove

        Returns:
            bool: True if unsubscription was successful
        """
        if event_type in self.subscribers and handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            return True
        return False

    def publish_event(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event object containing event data and metadata
        """
        if not self._active:
            raise RuntimeError("Event router is not active")

        if event.event_type in self.subscribers:
            for handler in self.subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # In production, this should be logged and possibly retried
                    print(f"Error handling event {event.event_type}: {str(e)}")

    def start(self) -> None:
        """Activate the event router."""
        self._active = True

    def stop(self) -> None:
        """Deactivate the event router."""
        self._active = False

    def clear_subscribers(self) -> None:
        """Remove all subscribers."""
        self.subscribers.clear()

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for a specific event type.

        Args:
            event_type: Type of event to count subscribers for

        Returns:
            int: Number of subscribers
        """
        return len(self.subscribers.get(event_type, []))
