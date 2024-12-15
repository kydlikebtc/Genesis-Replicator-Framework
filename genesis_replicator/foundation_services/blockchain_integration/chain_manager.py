"""
Chain Manager for blockchain integration.

This module manages multi-chain operations, network connections, and chain status monitoring.
"""
import asyncio
from typing import Dict, List, Optional, Any, Type
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from .exceptions import (
    ChainConnectionError,
    TransactionError,
    SecurityError,
    ConfigurationError
)
from .protocols.base import BaseProtocolAdapter
from .protocols.bnb_chain import BNBChainAdapter


class ChainManager:
    """Manages blockchain network connections and operations."""

    def __init__(self):
        """Initialize the chain manager."""
        self._connections: Dict[str, AsyncWeb3] = {}
        self._chain_configs: Dict[str, Dict[str, Any]] = {}
        self._status_monitors: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._connection_semaphore = asyncio.Semaphore(10)  # Limit concurrent connections
        self._connection_pool: Dict[str, List[AsyncWeb3]] = {}
        self._protocol_adapters: Dict[str, BaseProtocolAdapter] = {}
        self._health_metrics: Dict[str, Dict[str, Any]] = {}  # Store health metrics
        self._initialized = False

    async def start(self) -> None:
        """Initialize and start the chain manager.

        This method should be called before any other operations.
        """
        if self._initialized:
            return

        async with self._lock:
            self._initialized = True
            self._connections.clear()
            self._chain_configs.clear()
            self._status_monitors.clear()
            self._protocol_adapters.clear()

            # Register default protocol adapters
            await self.register_protocol_adapter("bnb", BNBChainAdapter())

    async def stop(self) -> None:
        """Stop and cleanup the chain manager."""
        async with self._lock:
            # Disconnect from all chains
            for chain_id in list(self._connections.keys()):
                await self.disconnect_from_chain(chain_id)
            self._initialized = False
            self._protocol_adapters.clear()

    async def register_protocol_adapter(self, chain_type: str, adapter: BaseProtocolAdapter) -> None:
        """Register a protocol adapter for a specific chain type.

        Args:
            chain_type: Chain type identifier (e.g., "bnb", "eth")
            adapter: Protocol adapter instance

        Raises:
            ValueError: If adapter is invalid
        """
        if not isinstance(adapter, BaseProtocolAdapter):
            raise ValueError("Invalid protocol adapter")

        async with self._lock:
            self._protocol_adapters[chain_type] = adapter

    async def configure(self, chain_id: str, config: Dict[str, Any]) -> None:
        """Configure chain connection parameters.

        Args:
            chain_id: Chain identifier
            config: Configuration parameters

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            await self.validate_chain_credentials(chain_id, config)
            self._chain_configs[chain_id] = config
        except Exception as e:
            raise ConfigurationError(
                f"Failed to configure chain {chain_id}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def get_chain_health(self, chain_id: str) -> Dict[str, Any]:
        """Get health metrics for a chain.

        Args:
            chain_id: Chain identifier

        Returns:
            Dict containing health metrics

        Raises:
            ChainConnectionError: If chain not found
        """
        if chain_id not in self._connections:
            raise ChainConnectionError(
                f"Chain {chain_id} not connected",
                details={"chain_id": chain_id}
            )
        return self._health_metrics.get(chain_id, {})

    async def get_all_chain_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health metrics for all connected chains.

        Returns:
            Dict mapping chain IDs to their health metrics
        """
        return self._health_metrics.copy()

    async def connect_chain(
        self,
        chain_id: str,
        credentials: Optional[Dict[str, Any]] = None
    ) -> None:
        """Connect to a chain with security validation.

        Args:
            chain_id: Chain identifier
            credentials: Optional security credentials

        Raises:
            SecurityError: If authentication fails
        """
        if not self._verify_chain_access(chain_id, credentials):
            raise SecurityError(
                "Unauthorized chain access",
                details={"chain_id": chain_id}
            )

    async def validate_chain_credentials(
        self,
        chain_id: str,
        credentials: Optional[Dict[str, Any]]
    ) -> bool:
        """Validate chain access credentials.

        Args:
            chain_id: Chain identifier
            credentials: Security credentials

        Returns:
            True if credentials are valid, False otherwise

        Raises:
            SecurityError: If validation fails
        """
        try:
            async with self._lock:
                return self._verify_chain_access(chain_id, credentials)
        except Exception as e:
            raise SecurityError(
                f"Failed to validate credentials for chain {chain_id}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    def _verify_chain_access(
        self,
        chain_id: str,
        credentials: Optional[Dict[str, Any]]
    ) -> bool:
        """Verify chain access permissions.

        Args:
            chain_id: Chain identifier
            credentials: Security credentials

        Returns:
            True if access is allowed, False otherwise
        """
        # Implement actual security checks
        # This is a placeholder - implement proper security validation
        if not credentials:
            return False
        return 'role' in credentials and credentials['role'] == 'admin'

    async def connect_to_chain(self, chain_id: str, endpoint_url: str, **config) -> None:
        """Connect to a blockchain network.

        Args:
            chain_id: Unique identifier for the blockchain network
            endpoint_url: RPC endpoint URL for the network
            **config: Additional configuration parameters

        Raises:
            ChainConnectionError: If connection fails
        """
        try:
            async with self._connection_semaphore:  # Limit concurrent connections
                async with self._lock:
                    if chain_id in self._connections:
                        raise ChainConnectionError(
                            f"Chain {chain_id} already connected",
                            details={"chain_id": chain_id}
                        )

                    # Get protocol adapter if specified
                    protocol = config.get('protocol')
                    adapter = None
                    if protocol:
                        adapter = self._protocol_adapters.get(protocol)
                        if not adapter:
                            raise ChainConnectionError(
                                f"Unsupported protocol {protocol}",
                                details={"chain_id": chain_id, "protocol": protocol}
                            )
                        await adapter.configure_web3(endpoint_url)
                        web3 = adapter.web3
                    else:
                        # Fallback to direct Web3 connection
                        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(endpoint_url))

                    # Initialize connection pool
                    if chain_id not in self._connection_pool:
                        self._connection_pool[chain_id] = []

                    # Test connection
                    try:
                        await asyncio.wait_for(web3.eth.chain_id, timeout=5.0)
                    except asyncio.TimeoutError:
                        raise ChainConnectionError(
                            f"Connection timeout for chain {chain_id}",
                            details={"chain_id": chain_id, "endpoint_url": endpoint_url}
                        )

                    # Add to pool and set as primary connection
                    self._connection_pool[chain_id].append(web3)
                    self._connections[chain_id] = web3
                    self._chain_configs[chain_id] = config

                    # Start monitoring task
                    if chain_id not in self._status_monitors:
                        self._status_monitors[chain_id] = asyncio.create_task(
                            self._monitor_chain_status(chain_id)
                        )

        except Web3Exception as e:
            raise ChainConnectionError(
                f"Failed to connect to chain {chain_id}",
                details={
                    "chain_id": chain_id,
                    "endpoint_url": endpoint_url,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ChainConnectionError(
                f"Unexpected error connecting to chain {chain_id}",
                details={
                    "chain_id": chain_id,
                    "endpoint_url": endpoint_url,
                    "error": str(e)
                }
            )

    async def disconnect_from_chain(self, chain_id: str) -> None:
        """Disconnect from a blockchain network.

        Args:
            chain_id: Chain identifier to disconnect from

        Raises:
            ChainConnectionError: If chain not found or disconnect fails
        """
        try:
            async with self._lock:
                if chain_id not in self._connections:
                    raise ChainConnectionError(
                        f"Chain {chain_id} not connected",
                        details={"chain_id": chain_id}
                    )

                # Cancel status monitoring
                if chain_id in self._status_monitors:
                    self._status_monitors[chain_id].cancel()
                    del self._status_monitors[chain_id]

                # Close connection and cleanup
                del self._connections[chain_id]
                del self._chain_configs[chain_id]
        except Exception as e:
            raise ChainConnectionError(
                f"Error during disconnect from chain {chain_id}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def get_chain_status(self, chain_id: str) -> Dict[str, Any]:
        """Get current status of a blockchain network.

        Args:
            chain_id: Chain identifier to check

        Returns:
            Dict containing chain status information

        Raises:
            ChainConnectionError: If chain not found or status check fails
        """
        try:
            if chain_id not in self._connections:
                raise ChainConnectionError(
                    f"Chain {chain_id} not connected",
                    details={"chain_id": chain_id}
                )

            web3 = self._connections[chain_id]

            # Gather chain information
            block_number = await web3.eth.block_number
            gas_price = await web3.eth.gas_price
            syncing = await web3.eth.syncing

            return {
                "chain_id": chain_id,
                "block_number": block_number,
                "gas_price": gas_price,
                "syncing": syncing,
                "connected": True
            }
        except Web3Exception as e:
            raise ChainConnectionError(
                f"Failed to get chain {chain_id} status",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def get_connected_chains(self) -> List[str]:
        """Get list of connected chain IDs.

        Returns:
            List of connected chain identifiers
        """
        async with self._lock:
            return list(self._connections.keys())

    async def execute_transaction(self, chain_id: str, transaction: Dict[str, Any]) -> str:
        """Execute a transaction on specified chain.

        Args:
            chain_id: Chain to execute transaction on
            transaction: Transaction parameters

        Returns:
            Transaction hash

        Raises:
            ChainConnectionError: If chain not found
            TransactionError: If transaction fails
        """
        if chain_id not in self._connections:
            raise ChainConnectionError(
                f"Chain {chain_id} not connected",
                details={"chain_id": chain_id}
            )

        web3 = self._connections[chain_id]
        protocol_adapter = self._protocol_adapters.get(self._chain_configs[chain_id].get('protocol'))

        try:
            # Get chain-specific gas estimation and optimization
            if protocol_adapter:
                gas_estimate = await protocol_adapter.estimate_gas(web3, transaction)
                optimized_tx = await protocol_adapter.optimize_transaction(web3, {
                    **transaction,
                    'gas': gas_estimate
                })
            else:
                # Default gas estimation if no protocol adapter
                gas_estimate = await web3.eth.estimate_gas(transaction)
                optimized_tx = {
                    **transaction,
                    'gas': gas_estimate
                }

            # Add current gas price with buffer for network congestion
            gas_price = await web3.eth.gas_price
            optimized_tx['gasPrice'] = int(gas_price * 1.1)  # 10% buffer

            # Execute transaction with exponential backoff retry
            max_retries = 3
            retry_delay = 1
            for attempt in range(max_retries):
                try:
                    tx_hash = await web3.eth.send_transaction(optimized_tx)
                    return tx_hash.hex()
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

        except Exception as e:
            raise TransactionError(
                "Transaction execution failed",
                details={
                    "chain_id": chain_id,
                    "error": str(e),
                    "transaction": transaction
                }
            )

    async def execute_transaction_batch(
        self,
        chain_id: str,
        transactions: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[str]:
        """Execute multiple transactions in parallel with rate limiting.

        Args:
            chain_id: Chain to execute transactions on
            transactions: List of transaction parameters
            max_concurrent: Maximum number of concurrent transactions

        Returns:
            List of transaction hashes

        Raises:
            ChainConnectionError: If chain not found
            TransactionError: If any transaction fails
        """
        if not transactions:
            return []

        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def execute_with_semaphore(tx: Dict[str, Any]) -> str:
            async with semaphore:
                return await self.execute_transaction(chain_id, tx)

        try:
            # Execute transactions in parallel with rate limiting
            tasks = [execute_with_semaphore(tx) for tx in transactions]
            results = await asyncio.gather(*tasks)
            return results
        except Exception as e:
            raise TransactionError(
                "Batch transaction execution failed",
                details={
                    "chain_id": chain_id,
                    "error": str(e),
                    "completed_transactions": len(results)
                }
            )

    async def track_transaction(
        self,
        chain_id: str,
        tx_hash: str,
        timeout: int = 300,
        poll_interval: int = 2,
        required_confirmations: int = 1
    ) -> Dict[str, Any]:
        """Track transaction status with timeout and confirmation requirements.

        Args:
            chain_id: Chain identifier
            tx_hash: Transaction hash to track
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds
            required_confirmations: Number of required confirmations

        Returns:
            Transaction receipt with additional status information

        Raises:
            ChainConnectionError: If chain not found
            TransactionError: If transaction fails or times out
        """
        if chain_id not in self._connections:
            raise ChainConnectionError(
                f"Chain {chain_id} not connected",
                details={"chain_id": chain_id}
            )

        web3 = self._connections[chain_id]
        start_time = asyncio.get_event_loop().time()

        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TransactionError(
                    f"Transaction {tx_hash} tracking timed out",
                    details={
                        "chain_id": chain_id,
                        "tx_hash": tx_hash,
                        "timeout": timeout
                    }
                )

            try:
                receipt = await web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    current_block = await web3.eth.block_number
                    confirmations = current_block - receipt['blockNumber']

                    if confirmations >= required_confirmations:
                        return {
                            **dict(receipt),
                            'confirmations': confirmations,
                            'confirmed': True,
                            'success': receipt['status'] == 1
                        }

            except Exception as e:
                print(f"Error checking transaction {tx_hash}: {str(e)}")

            await asyncio.sleep(poll_interval)

    async def _monitor_chain_status(self, chain_id: str) -> None:
        """Monitor chain status and manage connection pool.

        Args:
            chain_id: Chain identifier to monitor
        """
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                async with self._lock:
                    if chain_id not in self._connections:
                        break

                    web3 = self._connections[chain_id]
                    try:
                        # Collect health metrics
                        start_time = asyncio.get_event_loop().time()
                        block_number = await web3.eth.block_number
                        latency = asyncio.get_event_loop().time() - start_time

                        # Get peer count if supported
                        try:
                            peer_count = await web3.net.peer_count
                        except Exception:
                            peer_count = None

                        # Update health metrics
                        self._health_metrics[chain_id] = {
                            'latency': latency,
                            'block_height': block_number,
                            'peers': peer_count,
                            'timestamp': asyncio.get_event_loop().time(),
                            'connection_count': len(self._connection_pool.get(chain_id, [])),
                            'is_syncing': await web3.eth.syncing
                        }

                        # Log warnings for concerning metrics
                        if latency > 5.0:  # High latency threshold
                            print(f"Warning: High latency ({latency:.2f}s) for chain {chain_id}")
                        if peer_count is not None and peer_count < 3:  # Low peer count threshold
                            print(f"Warning: Low peer count ({peer_count}) for chain {chain_id}")

                        # Test connection
                        await asyncio.wait_for(web3.eth.chain_id, timeout=5.0)
                    except (Web3Exception, asyncio.TimeoutError):
                        # Remove failed connection from pool
                        if chain_id in self._connection_pool:
                            pool = self._connection_pool[chain_id]
                            if web3 in pool:
                                pool.remove(web3)

                            # Try to switch to another connection from pool
                            if pool:
                                self._connections[chain_id] = pool[0]
                                # Update health metrics for connection failure
                                self._health_metrics[chain_id] = {
                                    'error': 'Connection failed - switched to backup',
                                    'timestamp': asyncio.get_event_loop().time(),
                                    'connection_count': len(pool)
                                }
                            else:
                                # No more connections available
                                del self._connections[chain_id]
                                del self._chain_configs[chain_id]
                                if chain_id in self._connection_pool:
                                    del self._connection_pool[chain_id]
                                if chain_id in self._health_metrics:
                                    del self._health_metrics[chain_id]
                                break

            except Exception as e:
                # Log error but continue monitoring
                print(f"Error monitoring chain {chain_id}: {str(e)}")
                if chain_id in self._health_metrics:
                    self._health_metrics[chain_id]['error'] = str(e)
                continue

    async def _get_connection(self, chain_id: str) -> AsyncWeb3:
        """Get an available connection from the pool with load balancing.

        Args:
            chain_id: Chain identifier

        Returns:
            AsyncWeb3 connection

        Raises:
            ChainConnectionError: If no connection available
        """
        async with self._lock:
            if chain_id not in self._connection_pool or not self._connection_pool[chain_id]:
                raise ChainConnectionError(
                    f"No connections available for chain {chain_id}",
                    details={"chain_id": chain_id}
                )

            connections = self._connection_pool[chain_id]
            # Rotate connections for load balancing
            connection = connections.pop(0)
            connections.append(connection)

            # Verify connection health before returning
            try:
                await asyncio.wait_for(connection.eth.chain_id, timeout=2.0)
                return connection
            except (asyncio.TimeoutError, Exception) as e:
                # Remove unhealthy connection
                if connection in connections:
                    connections.remove(connection)
                raise ChainConnectionError(
                    f"Connection health check failed for chain {chain_id}",
                    details={"chain_id": chain_id, "error": str(e)}
                )
