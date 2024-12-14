"""
Tests for the Event Router module.
"""
import pytest
from datetime import datetime
from genesis_replicator.foundation_services.event_system.event_router import EventRouter, Event


def test_event_creation():
    """Test event object creation."""
    event = Event(event_type="test", data={"key": "value"})
    assert event.event_type == "test"
    assert event.data == {"key": "value"}
    assert isinstance(event.timestamp, datetime)


def test_subscribe_and_publish():
    """Test subscribing to and publishing events."""
    router = EventRouter()
    received_events = []

    def handler(event):
        received_events.append(event)

    # Subscribe to test event
    router.subscribe("test_event", handler)
    assert router.get_subscriber_count("test_event") == 1

    # Publish test event
    test_event = Event(event_type="test_event", data="test_data")
    router.publish_event(test_event)

    assert len(received_events) == 1
    assert received_events[0].event_type == "test_event"
    assert received_events[0].data == "test_data"


def test_unsubscribe():
    """Test unsubscribing from events."""
    router = EventRouter()

    def handler(event):
        pass

    # Subscribe and then unsubscribe
    router.subscribe("test_event", handler)
    assert router.get_subscriber_count("test_event") == 1

    router.unsubscribe("test_event", handler)
    assert router.get_subscriber_count("test_event") == 0


def test_multiple_subscribers():
    """Test multiple subscribers for the same event."""
    router = EventRouter()
    count1 = count2 = 0

    def handler1(event):
        nonlocal count1
        count1 += 1

    def handler2(event):
        nonlocal count2
        count2 += 1

    router.subscribe("test_event", handler1)
    router.subscribe("test_event", handler2)

    test_event = Event(event_type="test_event", data="test_data")
    router.publish_event(test_event)

    assert count1 == 1
    assert count2 == 1


def test_router_start_stop():
    """Test router activation and deactivation."""
    router = EventRouter()

    # Router should be active by default
    test_event = Event(event_type="test_event", data="test_data")
    router.publish_event(test_event)  # Should not raise error

    router.stop()
    with pytest.raises(RuntimeError):
        router.publish_event(test_event)

    router.start()
    router.publish_event(test_event)  # Should work again


def test_clear_subscribers():
    """Test clearing all subscribers."""
    router = EventRouter()

    def handler(event):
        pass

    router.subscribe("test_event1", handler)
    router.subscribe("test_event2", handler)

    assert router.get_subscriber_count("test_event1") == 1
    assert router.get_subscriber_count("test_event2") == 1

    router.clear_subscribers()

    assert router.get_subscriber_count("test_event1") == 0
    assert router.get_subscriber_count("test_event2") == 0
