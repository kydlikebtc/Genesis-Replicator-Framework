"""
Event batcher for optimizing event processing throughput.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class EventBatch:
    """Represents a batch of events."""
    batch_id: str
    events: List[Dict[str, Any]]
    created_at: datetime
    size: int
    priority: int
    tags: Set[str]

class EventBatcher:
    """Manages event batching and processing optimization."""

    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_time: float = 1.0,
        min_batch_size: int = 10
    ):
        """Initialize event batcher.

        Args:
            max_batch_size: Maximum events per batch
            max_wait_time: Maximum wait time in seconds
            min_batch_size: Minimum events for batch processing
        """
        self._max_batch_size = max_batch_size
        self._max_wait_time = max_wait_time
        self._min_batch_size = min_batch_size
        self._batches: Dict[str, EventBatch] = {}
        self._pending_events: Dict[str, List[Dict[str, Any]]] = {}
        self._batch_processors: Dict[str, Callable[[EventBatch], Awaitable[None]]] = {}
        self._lock = asyncio.Lock()
        self._processing_tasks: Set[asyncio.Task] = set()
        self._batch_timers: Dict[str, asyncio.Task] = {}
        logger.info("Event batcher initialized")

    async def add_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        priority: int = 0,
        tags: Optional[Set[str]] = None
    ) -> None:
        """Add event to batch.

        Args:
            event_type: Type of event
            event_data: Event data
            priority: Event priority
            tags: Optional event tags
        """
        async with self._lock:
            if event_type not in self._pending_events:
                self._pending_events[event_type] = []
                # Start batch timer
                self._start_batch_timer(event_type)

            self._pending_events[event_type].append({
                "data": event_data,
                "priority": priority,
                "tags": tags or set(),
                "timestamp": datetime.now().isoformat()
            })

            # Check if batch should be created
            if len(self._pending_events[event_type]) >= self._max_batch_size:
                await self._create_batch(event_type)

    async def register_processor(
        self,
        event_type: str,
        processor: Callable[[EventBatch], Awaitable[None]]
    ) -> None:
        """Register processor for event type.

        Args:
            event_type: Type of event
            processor: Async processor function
        """
        self._batch_processors[event_type] = processor
        logger.info(f"Registered processor for event type: {event_type}")

    async def get_batch_stats(self) -> Dict[str, Any]:
        """Get batching statistics.

        Returns:
            Dictionary of batch statistics
        """
        async with self._lock:
            stats = {
                "total_batches": len(self._batches),
                "pending_events": {
                    event_type: len(events)
                    for event_type, events in self._pending_events.items()
                },
                "active_processors": len(self._processing_tasks),
                "event_types": list(self._batch_processors.keys())
            }
            return stats

    def _start_batch_timer(self, event_type: str) -> None:
        """Start timer for batch creation.

        Args:
            event_type: Type of event
        """
        if event_type in self._batch_timers:
            self._batch_timers[event_type].cancel()

        async def timer():
            await asyncio.sleep(self._max_wait_time)
            async with self._lock:
                if event_type in self._pending_events:
                    if len(self._pending_events[event_type]) >= self._min_batch_size:
                        await self._create_batch(event_type)

        self._batch_timers[event_type] = asyncio.create_task(timer())

    async def _create_batch(self, event_type: str) -> None:
        """Create and process event batch.

        Args:
            event_type: Type of event
        """
        if not self._pending_events[event_type]:
            return

        # Create batch
        events = self._pending_events[event_type]
        batch_id = f"{event_type}-{datetime.now().isoformat()}"

        # Calculate batch priority and tags
        avg_priority = sum(e["priority"] for e in events) / len(events)
        all_tags = set().union(*(e["tags"] for e in events))

        batch = EventBatch(
            batch_id=batch_id,
            events=events,
            created_at=datetime.now(),
            size=len(events),
            priority=int(avg_priority),
            tags=all_tags
        )

        self._batches[batch_id] = batch
        self._pending_events[event_type] = []

        # Process batch
        if event_type in self._batch_processors:
            task = asyncio.create_task(self._process_batch(batch, event_type))
            self._processing_tasks.add(task)
            task.add_done_callback(self._processing_tasks.discard)

    async def _process_batch(
        self,
        batch: EventBatch,
        event_type: str
    ) -> None:
        """Process event batch.

        Args:
            batch: Event batch
            event_type: Type of event
        """
        try:
            processor = self._batch_processors[event_type]
            await processor(batch)
            logger.info(f"Processed batch: {batch.batch_id}")
        except Exception as e:
            logger.error(f"Failed to process batch {batch.batch_id}: {str(e)}")
        finally:
            async with self._lock:
                if batch.batch_id in self._batches:
                    del self._batches[batch.batch_id]

    async def stop(self) -> None:
        """Stop event batcher and clean up."""
        # Cancel batch timers
        for timer in self._batch_timers.values():
            timer.cancel()

        # Wait for processing tasks
        if self._processing_tasks:
            await asyncio.gather(*self._processing_tasks, return_exceptions=True)

        logger.info("Event batcher stopped")
