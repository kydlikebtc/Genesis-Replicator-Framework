"""
Tests for the Event Router implementation.
"""

import pytest
import asyncio
from genesis_replicator.foundation_services.event_system.event_router import EventRouter

@pytest.fixture
def event_router():
    """Create a new EventRouter instance for testing."""
    return EventRouter()

@pytest.mark.asyncio
async def test_start_stop(event_router):
    """Test starting and stopping the event router."""
    assert not event_router._running

    await event_router.start()
    assert event_router._running

    await event_router.stop()
    assert not event_router._running

@pytest.mark.asyncio
async def test_subscribe_unsubscribe(event_router):
    """Test subscribing and unsubscribing from events."""
    async def callback(data):
        pass

    event_router.subscribe("test_event", callback, "test_subscriber")
    assert "test_event" in event_router._subscriptions
    assert len(event_router._subscriptions["test_event"]) == 1

    event_router.unsubscribe("test_event", "test_subscriber")
    assert len(event_router._subscriptions["test_event"]) == 0

@pytest.mark.asyncio
async def test_publish_and_receive(event_router):
    """Test publishing events and receiving them through subscribers."""
    received_data = []

    async def callback(data):
        received_data.append(data)

    await event_router.start()
    event_router.subscribe("test_event", callback, "test_subscriber")

    # Start event processing
    process_task = asyncio.create_task(event_router.process_events())

    # Publish test event
    test_data = {"message": "test"}
    await event_router.publish("test_event", test_data)

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Stop event router and processing
    await event_router.stop()
    process_task.cancel()

    assert len(received_data) == 1
    assert received_data[0] == test_data

@pytest.mark.asyncio
async def test_multiple_subscribers(event_router):
    """Test multiple subscribers receiving the same event."""
    received_data_1 = []
    received_data_2 = []

    async def callback_1(data):
        received_data_1.append(data)

    async def callback_2(data):
        received_data_2.append(data)

    await event_router.start()
    event_router.subscribe("test_event", callback_1, "subscriber_1")
    event_router.subscribe("test_event", callback_2, "subscriber_2")

    # Start event processing
    process_task = asyncio.create_task(event_router.process_events())

    # Publish test event
    test_data = {"message": "test"}
    await event_router.publish("test_event", test_data)

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Stop event router and processing
    await event_router.stop()
    process_task.cancel()

    assert len(received_data_1) == 1
    assert len(received_data_2) == 1
    assert received_data_1[0] == test_data
    assert received_data_2[0] == test_data

@pytest.mark.asyncio
async def test_get_subscribers(event_router):
    """Test getting subscriber information."""
    async def callback(data):
        pass

    event_router.subscribe("event1", callback, "subscriber1")
    event_router.subscribe("event1", callback, "subscriber2")
    event_router.subscribe("event2", callback, "subscriber3")

    # Get all subscribers
    all_subscribers = event_router.get_subscribers()
    assert len(all_subscribers) == 2
    assert len(all_subscribers["event1"]) == 2
    assert len(all_subscribers["event2"]) == 1

    # Get subscribers for specific event
    event1_subscribers = event_router.get_subscribers("event1")
    assert len(event1_subscribers) == 1
    assert len(event1_subscribers["event1"]) == 2

@pytest.mark.asyncio
async def test_priority_handling(event_router):
    """Test event handling with different priorities."""
    received_order = []

    async def callback_high(data):
        received_order.append("high")

    async def callback_medium(data):
        received_order.append("medium")

    async def callback_low(data):
        received_order.append("low")

    await event_router.start()
    event_router.subscribe("test_event", callback_low, "low_priority", priority=3)
    event_router.subscribe("test_event", callback_high, "high_priority", priority=1)
    event_router.subscribe("test_event", callback_medium, "medium_priority", priority=2)

    # Start event processing
    process_task = asyncio.create_task(event_router.process_events())

    # Publish test event
    await event_router.publish("test_event", {"message": "test"})

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Stop event router and processing
    await event_router.stop()
    process_task.cancel()

    assert received_order == ["high", "medium", "low"]

@pytest.mark.asyncio
async def test_error_handling(event_router):
    """Test error handling during event processing."""
    error_caught = False

    async def failing_callback(data):
        raise Exception("Test error")

    async def error_handler(error, event_type, subscriber_id):
        nonlocal error_caught
        error_caught = True
        assert isinstance(error, Exception)
        assert error.args[0] == "Test error"
        assert event_type == "test_event"
        assert subscriber_id == "failing_subscriber"

    await event_router.start()
    event_router.set_error_handler(error_handler)
    event_router.subscribe("test_event", failing_callback, "failing_subscriber")

    # Start event processing
    process_task = asyncio.create_task(event_router.process_events())

    # Publish test event
    await event_router.publish("test_event", {"message": "test"})

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Stop event router and processing
    await event_router.stop()
    process_task.cancel()

    assert error_caught

@pytest.mark.asyncio
async def test_event_filtering(event_router):
    """Test event filtering functionality."""
    received_data = []

    async def callback(data):
        received_data.append(data)

    def filter_func(data):
        return data.get("value", 0) > 10

    await event_router.start()
    event_router.subscribe(
        "test_event",
        callback,
        "filtered_subscriber",
        filter_func=filter_func
    )

    # Start event processing
    process_task = asyncio.create_task(event_router.process_events())

    # Publish test events
    await event_router.publish("test_event", {"value": 5})
    await event_router.publish("test_event", {"value": 15})

    # Wait for event processing
    await asyncio.sleep(0.1)

    # Stop event router and processing
    await event_router.stop()
    process_task.cancel()

    assert len(received_data) == 1
    assert received_data[0]["value"] == 15
