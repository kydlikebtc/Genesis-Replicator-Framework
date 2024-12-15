# Event Processing System

The event processing system provides robust event handling capabilities with batching optimization and circuit breaker patterns for fault tolerance.

## Components

### Event Batcher
- Optimizes event processing through intelligent batching
- Configurable batch sizes and timing
- Priority-based processing
- Tag-based event grouping
- Comprehensive metrics collection

### Circuit Breaker
- Fault tolerance pattern implementation
- Configurable failure thresholds
- Automatic recovery with half-open state
- Detailed statistics tracking
- Manual reset capabilities

## Usage

### Event Batching
```python
# Initialize batcher
batcher = EventBatcher(
    max_batch_size=100,
    max_wait_time=1.0,
    min_batch_size=10
)

# Register processor
async def process_batch(batch: EventBatch):
    for event in batch.events:
        # Process event
        pass

await batcher.register_processor("event_type", process_batch)

# Add events
await batcher.add_event(
    "event_type",
    {"data": "event_data"},
    priority=1,
    tags={"tag1", "tag2"}
)
```

### Circuit Breaker
```python
# Initialize circuit breaker
breaker = CircuitBreaker(
    failure_threshold=0.5,
    reset_timeout=60.0,
    half_open_timeout=30.0
)

# Execute with protection
async def operation():
    # Potentially failing operation
    pass

try:
    result = await breaker.execute("circuit_id", operation)
except RuntimeError:
    # Circuit is open
    pass
```

## Configuration

### Event Batcher Configuration
- `max_batch_size`: Maximum events per batch
- `max_wait_time`: Maximum wait time in seconds
- `min_batch_size`: Minimum events for batch processing

### Circuit Breaker Configuration
- `failure_threshold`: Failure rate threshold (0.0-1.0)
- `reset_timeout`: Time before reset attempt in seconds
- `half_open_timeout`: Time in half-open state in seconds

## Metrics and Monitoring

### Event Batcher Metrics
- Total batches processed
- Pending events by type
- Active processors
- Event type statistics

### Circuit Breaker Metrics
- Total requests
- Failed requests
- Success rate
- Current state
- Last failure/success timestamps

## Error Handling

The system provides comprehensive error handling with:
- Batch processing retries
- Circuit state management
- Detailed error logging
- Failure rate tracking
- Automatic recovery mechanisms
