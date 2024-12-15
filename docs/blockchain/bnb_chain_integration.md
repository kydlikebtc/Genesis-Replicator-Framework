# BNB Chain Integration Guide

## Overview

The Genesis Replicator Framework provides comprehensive support for BNB Chain (formerly BSC) integration, enabling seamless interaction with the BNB Chain ecosystem.

## Features

- Native BNB Chain protocol support
- Smart contract deployment and interaction
- Transaction management
- Event monitoring
- Gas optimization
- Cross-chain operations

## Configuration

```json
{
    "bnb_chain": {
        "chain_id": 56,
        "rpc_url": "https://bsc-dataseed.binance.org",
        "ws_url": "wss://bsc-ws-node.nariox.org:443",
        "explorer_url": "https://bscscan.com"
    }
}
```

## Usage Examples

### Initialize Chain Manager
```python
from genesis_replicator.foundation_services.blockchain_integration import ChainManager

chain_manager = ChainManager()
await chain_manager.initialize_chain("bnb_chain")
```

### Deploy Contract
```python
contract = await chain_manager.deploy_contract(
    chain="bnb_chain",
    contract_name="MyContract",
    constructor_args=[arg1, arg2]
)
```

### Send Transaction
```python
tx_hash = await chain_manager.send_transaction(
    chain="bnb_chain",
    to_address="0x...",
    value=1000000000000000000  # 1 BNB
)
```

## Best Practices

1. Gas Management
   - Use dynamic gas price estimation
   - Implement gas optimization strategies
   - Monitor gas costs

2. Transaction Handling
   - Implement proper error handling
   - Use retry mechanisms
   - Monitor transaction status

3. Event Monitoring
   - Subscribe to relevant events
   - Implement event filtering
   - Handle event processing

## Security Considerations

1. Private Key Management
   - Use secure key storage
   - Implement key rotation
   - Monitor key usage

2. Transaction Validation
   - Validate all parameters
   - Implement transaction limits
   - Monitor for suspicious activity

3. Smart Contract Security
   - Audit contracts
   - Implement access controls
   - Monitor contract interactions

## Troubleshooting

Common issues and solutions:

1. Connection Issues
   ```python
   # Retry connection with fallback nodes
   await chain_manager.retry_connection(
       chain="bnb_chain",
       max_retries=3
   )
   ```

2. Transaction Failures
   ```python
   # Check transaction status
   status = await chain_manager.get_transaction_status(tx_hash)
   if status.failed:
       error = await chain_manager.get_transaction_error(tx_hash)
   ```

## API Reference

### ChainManager

```python
class ChainManager:
    async def initialize_chain(
        self,
        chain: str,
        config: Optional[Dict] = None
    ) -> None:
        """Initialize blockchain connection."""
        pass

    async def deploy_contract(
        self,
        chain: str,
        contract_name: str,
        constructor_args: List[Any]
    ) -> Contract:
        """Deploy smart contract."""
        pass

    async def send_transaction(
        self,
        chain: str,
        to_address: str,
        value: int,
        data: Optional[bytes] = None
    ) -> str:
        """Send blockchain transaction."""
        pass
```

### TransactionManager

```python
class TransactionManager:
    async def prepare_transaction(
        self,
        chain: str,
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare transaction for submission."""
        pass

    async def submit_transaction(
        self,
        chain: str,
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit transaction to blockchain."""
        pass
```

## Error Handling

The framework provides comprehensive error handling:

```python
from genesis_replicator.foundation_services.exceptions import (
    ChainConnectionError,
    TransactionError,
    ContractError
)

try:
    await chain_manager.send_transaction(...)
except ChainConnectionError:
    # Handle connection issues
    pass
except TransactionError as e:
    # Handle transaction failures
    pass
except ContractError as e:
    # Handle contract-related errors
    pass
```

## Monitoring and Metrics

The framework provides built-in monitoring:

```python
# Get chain metrics
metrics = await chain_manager.get_metrics("bnb_chain")

# Monitor specific events
await chain_manager.monitor_events(
    chain="bnb_chain",
    contract_address="0x...",
    event_name="Transfer"
)
```

## Rate Limiting

Built-in rate limiting protection:

```python
# Configure rate limits
await chain_manager.set_rate_limits(
    chain="bnb_chain",
    limits={
        "requests_per_second": 10,
        "requests_per_minute": 500
    }
)
```

## Cross-Chain Operations

Support for cross-chain transactions:

```python
# Initialize cross-chain operation
tx_id = await cross_chain_manager.initiate_cross_chain_transaction(
    source_chain="ethereum",
    target_chain="bnb_chain",
    source_tx={...},
    target_tx={...}
)

# Execute cross-chain transaction
await cross_chain_manager.execute_transaction(tx_id)
```
