"""
Event processing optimization for Genesis Replicator Framework.
"""
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging

@dataclass
class EventStats:
    """Event processing statistics."""
    processed_count: int
    average_latency: float
    queue_size: int
    error_count: int

class EventOptimizer:
    """Optimizes event processing performance."""

    def __init__(
        self,
        max_batch_size: int = 100,
        max_queue_size: int = 1000,
        processing_timeout: float = 5.0
    ):
        """Initialize event optimizer.

        Args:
            max_batch_size: Maximum events per batch
            max_queue_size: Maximum queue size
            processing_timeout: Event processing timeout
        """
        self._max_batch_size = max_batch_size
        self._max_queue_size = max_queue_size
        self._processing_timeout = processing_timeout
        self._stats = EventStats(0, 0.0, 0, 0)
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._processors: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)

    async def process_event(
        self,
        event_type: str,
        event_data: Any
    ) -> bool:
        """Process single event.

        Args:
            event_type: Type of event
            event_data: Event data

        Returns:
            bool: Success status
        """
        try:
            await self._event_queue.put((event_type, event_data))
            return True
        except asyncio.QueueFull:
            self._logger.error("Event queue full")
            return False

    async def process_batch(
        self,
        event_type: str,
        events: List[Any]
    ) -> bool:
        """Process batch of events.

        Args:
            event_type: Type of events
            events: List of event data

        Returns:
            bool: Success status
        """
        if len(events) > self._max_batch_size:
            self._logger.warning(f"Batch size exceeds maximum: {len(events)}")
            events = events[:self._max_batch_size]

        try:
            for event_data in events:
                await self._event_queue.put((event_type, event_data))
            return True
        except asyncio.QueueFull:
            self._logger.error("Event queue full during batch processing")
            return False

    async def register_processor(
        self,
        event_type: str,
        processor: Callable
    ) -> None:
        """Register event processor.

        Args:
            event_type: Type of events to process
            processor: Processing function
        """
        async with self._lock:
            if event_type not in self._processors:
                self._processors[event_type] = []
            self._processors[event_type].append(processor)

    async def start_processing(self) -> None:
        """Start event processing loop."""
        while True:
            try:
                event_type, event_data = await self._event_queue.get()
                start_time = asyncio.get_event_loop().time()

                # Process event with timeout
                try:
                    async with asyncio.timeout(self._processing_timeout):
                        await self._process_single_event(event_type, event_data)
                except asyncio.TimeoutError:
                    self._logger.error(f"Event processing timeout: {event_type}")
                    self._stats.error_count += 1
                    continue

                # Update statistics
                processing_time = asyncio.get_event_loop().time() - start_time
                self._update_stats(processing_time)

            except Exception as e:
                self._logger.error(f"Event processing error: {str(e)}")
                self._stats.error_count += 1

    async def get_stats(self) -> EventStats:
        """Get event processing statistics.

        Returns:
            EventStats: Current statistics
        """
        return self._stats

    async def _process_single_event(
        self,
        event_type: str,
        event_data: Any
    ) -> None:
        """Process single event with registered processors.

        Args:
            event_type: Type of event
            event_data: Event data
        """
        if event_type not in self._processors:
            self._logger.warning(f"No processors for event type: {event_type}")
            return

        for processor in self._processors[event_type]:
            await processor(event_data)

    def _update_stats(self, processing_time: float) -> None:
        """Update processing statistics.

        Args:
            processing_time: Time taken to process event
        """
        self._stats.processed_count += 1
        self._stats.queue_size = self._event_queue.qsize()

        # Update moving average of latency
        if self._stats.average_latency == 0:
            self._stats.average_latency = processing_time
        else:
            self._stats.average_latency = (
                0.9 * self._stats.average_latency +
                0.1 * processing_time
            )
