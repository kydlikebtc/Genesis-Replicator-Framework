# Async Operations API Reference

## Overview
The async operations system provides robust concurrency controls, connection pooling, and timeout handling for the Genesis Replicator Framework. This documentation covers the key components and their usage.

## Components

### ChainManager
The `ChainManager` class provides connection pooling and concurrent chain operations management.

```python
class ChainManager:
    def __init__(self, max_connections: int = 10):
        """
        Initialize chain manager with connection pool.

        Args:
            max_connections: Maximum number of concurrent connections
        """

    async def connect_to_chain(self, chain_id: str, endpoint: str, credentials: Dict[str, Any]) -> bool:
        """
        Connect to a blockchain network with connection pooling.

        Args:
            chain_id: Unique identifier for the chain
            endpoint: Chain endpoint URL
            credentials: Authentication credentials

        Returns:
            bool: True if connection successful

        Raises:
            ChainConnectionError: If connection fails
            SecurityError: If credentials are invalid
        """

    async def get_connection(self, chain_id: str) -> Connection:
        """
        Get a connection from the pool.

        Args:
            chain_id: Chain identifier

        Returns:
            Connection: Pooled connection instance

        Raises:
            KeyError: If chain_id not found
        """
```

### ConnectionPool
The connection pool manages blockchain network connections with automatic cleanup and resource limits.

```python
class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        """
        Initialize connection pool.

        Args:
            max_connections: Maximum number of concurrent connections
        """

    async def acquire(self) -> Connection:
        """
        Acquire connection from pool with backpressure handling.

        Returns:
            Connection: Available connection

        Raises:
            TimeoutError: If pool is full
        """
```

## Usage Examples

### Basic Connection Management
```python
# Initialize chain manager
manager = ChainManager(max_connections=5)
await manager.start()

# Connect to chain with automatic pooling
await manager.connect_to_chain(
    "ethereum_mainnet",
    "https://mainnet.infura.io/v3/YOUR-PROJECT-ID",
    credentials={"api_key": "your_key"}
)

# Get pooled connection
connection = await manager.get_connection("ethereum_mainnet")
```

### Concurrent Operations
```python
# Handle multiple concurrent operations
async def process_chains():
    tasks = []
    for chain_id in chain_ids:
        tasks.append(manager.connect_to_chain(
            chain_id,
            endpoints[chain_id],
            credentials[chain_id]
        ))
    await asyncio.gather(*tasks)
```

## Best Practices

1. **Resource Management**
   - Always use connection pooling for blockchain interactions
   - Set appropriate pool size limits based on system resources
   - Implement proper cleanup in shutdown procedures

2. **Concurrency Control**
   - Use `asyncio.gather()` for parallel operations
   - Implement backpressure handling for connection limits
   - Handle timeouts appropriately

3. **Error Handling**
   - Implement proper exception handling for async operations
   - Use timeout mechanisms for long-running operations
   - Handle connection failures gracefully

4. **Security**
   - Validate credentials before establishing connections
   - Implement rate limiting for connection attempts
   - Use secure connection parameters

## Configuration

The async operations system can be configured through the framework's configuration system:

```json
{
    "chain_manager": {
        "max_connections": 10,
        "connection_timeout": 30,
        "retry_attempts": 3
    }
}
```

## Monitoring

Monitor async operations using the framework's monitoring system:

```python
# Get connection pool metrics
metrics = await manager.get_pool_metrics()
print(f"Active connections: {metrics['active_connections']}")
print(f"Pool utilization: {metrics['pool_utilization']}%")
```
