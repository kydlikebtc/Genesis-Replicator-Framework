"""
Chain Manager for blockchain integration.

This module manages multi-chain operations, network connections, and chain status monitoring.
"""
import asyncio
import logging
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

logger = logging.getLogger(__name__)


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

        try:
            async with self._lock:
                self._initialized = True
                self._connections.clear()
                self._chain_configs.clear()
                self._status_monitors.clear()
                self._protocol_adapters.clear()
                # Note: Protocol adapters will be registered when needed
        except Exception as e:
            self._initialized = False
            raise ConfigurationError("Failed to start chain manager", details={"error": str(e)})

    async def is_running(self) -> bool:
        """Check if the chain manager is running.

        Returns:
            bool: True if the manager is initialized and running
        """
        return self._initialized

    async def stop(self) -> None:
        """Stop and cleanup the chain manager."""
        async with self._lock:
            # Cancel all monitoring tasks first
            for chain_id, task in list(self._status_monitors.items()):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling tasks
                except Exception as e:
                    logger.error(f"Error cancelling monitor task for chain {chain_id}: {e}")

            # Disconnect from all chains
            for chain_id in list(self._connections.keys()):
                try:
                    await self.disconnect_from_chain(chain_id)
                except Exception as e:
                    logger.error(f"Error disconnecting from chain {chain_id}: {e}")

            self._initialized = False
            self._protocol_adapters.clear()
            self._status_monitors.clear()
            self._connections.clear()
            self._chain_configs.clear()
            self._health_metrics.clear()

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

    async def configure(self, config: Dict[str, Dict[str, Any]]) -> None:
        """Configure chain connections.

        Args:
            config: Dictionary mapping chain IDs to their configurations

        Raises:
            ChainConnectionError: If configuration fails
        """
        if not self._initialized:
            raise ConfigurationError("Chain manager not initialized")

        try:
            async with asyncio.timeout(30):  # Global timeout for entire configuration
                async with self._lock:
                    # First validate all configurations with timeout
                    for chain_id, chain_config in config.items():
                        try:
                            await asyncio.wait_for(
                                self.validate_chain_credentials(chain_id, chain_config),
                                timeout=5.0
                            )
                            self._chain_configs[chain_id] = chain_config
                        except asyncio.TimeoutError:
                            raise ChainConnectionError(
                                f"Validation timeout for chain {chain_id}",
                                details={"chain_id": chain_id}
                            )

                    # Then connect and start monitoring for each chain with timeout
                    for chain_id, chain_config in config.items():
                        try:
                            await asyncio.wait_for(
                                self.connect_chain(chain_id, chain_config),
                                timeout=10.0
                            )

                            # Start monitoring task with explicit name and timeout
                            monitor_task = asyncio.create_task(
                                self._monitor_chain_status(chain_id),
                                name=f"monitor_{chain_id}"
                            )
                            self._status_monitors[chain_id] = monitor_task

                            # Wait briefly to ensure monitoring task starts
                            await asyncio.sleep(0.1)

                            # Verify task is running
                            if monitor_task.done():
                                exc = monitor_task.exception()
                                if exc:
                                    raise exc

                        except asyncio.TimeoutError:
                            logger.error(f"Connection timeout for chain {chain_id}")
                            # Clean up any partial configuration
                            if chain_id in self._chain_configs:
                                del self._chain_configs[chain_id]
                            if chain_id in self._status_monitors:
                                self._status_monitors[chain_id].cancel()
                                del self._status_monitors[chain_id]
                            raise ChainConnectionError(
                                f"Connection timeout for chain {chain_id}",
                                details={"chain_id": chain_id}
                            )

        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            # Clean up any partial configuration
            for chain_id in list(self._chain_configs.keys()):
                if chain_id in self._status_monitors:
                    self._status_monitors[chain_id].cancel()
                    del self._status_monitors[chain_id]
                if chain_id in self._chain_configs:
                    del self._chain_configs[chain_id]
            raise ChainConnectionError("Configuration failed", details={"error": str(e)})

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
        chain_config: Dict[str, Any]
    ) -> None:
        """Connect to a blockchain chain.

        Args:
            chain_id: Chain identifier
            chain_config: Chain configuration parameters

        Raises:
            ChainConnectionError: If connection fails
        """
        try:
            logger.debug(f"Attempting to connect to chain {chain_id}")
            # Remove chain_id and rpc_url from kwargs to avoid parameter conflicts
            connect_kwargs = {k: v for k, v in chain_config.items()
                           if k not in ['rpc_url', 'chain_id']}
            await self.connect_to_chain(
                chain_id,
                chain_config['rpc_url'],
                **connect_kwargs
            )
            logger.debug(f"Successfully connected to chain {chain_id}")
        except Exception as e:
            logger.error(f"Failed to connect to chain {chain_id}: {e}")
            raise ChainConnectionError(f"Failed to connect to chain {chain_id}", details={"error": str(e)})

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
            logger.debug(f"Validating credentials for chain {chain_id}")
            logger.debug(f"Credentials: {credentials}")

            if not credentials:
                logger.debug(f"No credentials provided for chain {chain_id}")
                return False

            # For testing and basic validation, we just check if required fields exist
            required_fields = ['rpc_url', 'chain_id']
            has_fields = all(field in credentials for field in required_fields)
            logger.debug(f"Chain {chain_id} has required fields: {has_fields}")

            if not has_fields:
                return False

            # Validate chain_id is an integer
            try:
                int(credentials['chain_id'])
            except (ValueError, TypeError):
                logger.debug(f"Invalid chain_id format for chain {chain_id}")
                return False

            # Validate rpc_url is a non-empty string
            if not isinstance(credentials['rpc_url'], str) or not credentials['rpc_url'].strip():
                logger.debug(f"Invalid rpc_url format for chain {chain_id}")
                return False

            return True

        except Exception as e:
            logger.error(f"Validation failed for chain {chain_id}: {e}")
            raise SecurityError(
                f"Failed to validate credentials for chain {chain_id}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def _verify_chain_access(
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
        logger.debug(f"Verifying chain access for {chain_id}")
        if not credentials:
            logger.debug(f"No credentials provided for chain {chain_id}")
            return False

        # For testing and basic validation, we just check if required fields exist
        required_fields = ['rpc_url', 'chain_id']
        has_fields = all(field in credentials for field in required_fields)
        logger.debug(f"Chain {chain_id} has required fields: {has_fields}")
        return has_fields

    async def connect_to_chain(
        self,
        chain_id: str,
        rpc_url: str,
        **kwargs
    ) -> None:
        """Connect to a blockchain chain.

        Args:
            chain_id: Chain identifier
            rpc_url: RPC endpoint URL
            **kwargs: Additional chain-specific configuration

        Raises:
            ChainConnectionError: If connection fails
        """
        try:
            async with asyncio.timeout(15.0):  # Increased timeout for initial connection
                async with self._lock:
                    if chain_id in self._connections:
                        logger.debug(f"Chain {chain_id} already connected")
                        return

                    logger.debug(f"Connecting to chain {chain_id} at {rpc_url}")

                    # Get protocol adapter if specified
                    protocol = kwargs.get('protocol')
                    if protocol:
                        adapter = self._protocol_adapters.get(protocol)
                        if not adapter:
                            raise ChainConnectionError(
                                f"Unsupported protocol {protocol}",
                                details={"chain_id": chain_id, "protocol": protocol}
                            )
                        try:
                            await asyncio.wait_for(adapter.configure_web3(rpc_url), timeout=10.0)
                            web3 = adapter.web3
                            logger.debug(f"Protocol adapter {protocol} configured for chain {chain_id}")
                        except asyncio.TimeoutError:
                            raise ChainConnectionError(
                                f"Protocol adapter configuration timeout for chain {chain_id}",
                                details={"chain_id": chain_id, "protocol": protocol}
                            )
                    else:
                        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))

                    try:
                        # Quick connection test with explicit timeout
                        await asyncio.wait_for(web3.connect(), timeout=5.0)
                        connected = await asyncio.wait_for(web3.is_connected(), timeout=5.0)
                        if not connected:
                            raise ChainConnectionError(
                                f"Failed to connect to chain {chain_id}",
                                details={"rpc_url": rpc_url}
                            )

                        # Store the connection
                        self._connections[chain_id] = web3
                        logger.debug(f"Successfully connected to chain {chain_id}")

                    except asyncio.TimeoutError:
                        logger.error(f"Connection test timeout for chain {chain_id}")
                        raise ChainConnectionError(
                            f"Connection test timeout for chain {chain_id}",
                            details={"rpc_url": rpc_url}
                        )
                    except Exception as e:
                        logger.error(f"Failed to connect to chain {chain_id}: {e}")
                        if chain_id in self._connections:
                            del self._connections[chain_id]
                        raise ChainConnectionError(
                            f"Failed to connect to chain {chain_id}",
                            details={"error": str(e), "rpc_url": rpc_url}
                        )

        except asyncio.TimeoutError:
            logger.error(f"Connection timeout for chain {chain_id}")
            raise ChainConnectionError(
                f"Connection timeout for chain {chain_id}",
                details={"rpc_url": rpc_url}
            )
        except Exception as e:
            logger.error(f"Unexpected error connecting to chain {chain_id}: {e}")
            raise ChainConnectionError(
                f"Failed to connect to chain {chain_id}",
                details={"error": str(e), "rpc_url": rpc_url}
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
        """Monitor chain status and update health metrics.

        Args:
            chain_id: Chain identifier to monitor
        """
        logger.debug(f"Starting monitoring task for chain {chain_id}")
        CHECK_INTERVAL = 5  # seconds
        MAX_RETRIES = 3
        retry_count = 0

        while self._initialized:  # Only run while manager is initialized
            try:
                # Check for task cancellation
                if asyncio.current_task().cancelled():
                    logger.debug(f"Monitoring task cancelled for chain {chain_id}")
                    break

                # Get connection with timeout
                try:
                    web3 = await asyncio.wait_for(
                        self._get_connection(chain_id),
                        timeout=2.0  # Reduced timeout for faster response
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout getting connection for chain {chain_id}")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for chain {chain_id}")
                        self._health_metrics[chain_id] = {
                            'status': 'error',
                            'last_check': asyncio.get_event_loop().time(),
                            'errors': ['Max connection retries reached']
                        }
                        await asyncio.sleep(CHECK_INTERVAL)
                    continue

                # Check connection with timeout
                try:
                    is_connected = await asyncio.wait_for(
                        web3.is_connected(),
                        timeout=2.0  # Reduced timeout for faster response
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout checking connection for chain {chain_id}")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for chain {chain_id}")
                        self._health_metrics[chain_id] = {
                            'status': 'error',
                            'last_check': asyncio.get_event_loop().time(),
                            'errors': ['Max connection check retries reached']
                        }
                        await asyncio.sleep(CHECK_INTERVAL)
                    continue

                if not is_connected:
                    logger.warning(f"Lost connection to chain {chain_id}")
                    self._health_metrics[chain_id] = {
                        'status': 'disconnected',
                        'last_check': asyncio.get_event_loop().time(),
                        'errors': ['Connection lost']
                    }
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for chain {chain_id}")
                        await asyncio.sleep(CHECK_INTERVAL)
                    continue

                # Reset retry count on successful connection
                retry_count = 0

                # Get chain status with timeout
                try:
                    block_number = await asyncio.wait_for(
                        web3.eth.get_block_number(),
                        timeout=2.0  # Reduced timeout for faster response
                    )
                    self._health_metrics[chain_id] = {
                        'status': 'connected',
                        'last_check': asyncio.get_event_loop().time(),
                        'block_number': block_number,
                        'errors': []
                    }
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout getting block number for chain {chain_id}")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Max retries reached for chain {chain_id}")
                        self._health_metrics[chain_id] = {
                            'status': 'error',
                            'last_check': asyncio.get_event_loop().time(),
                            'errors': ['Max block number retries reached']
                        }
                        await asyncio.sleep(CHECK_INTERVAL)
                    continue

                # Wait before next check
                await asyncio.sleep(CHECK_INTERVAL)

            except asyncio.CancelledError:
                logger.debug(f"Monitoring task cancelled for chain {chain_id}")
                break
            except Exception as e:
                logger.error(f"Error monitoring chain {chain_id}: {e}")
                self._health_metrics[chain_id] = {
                    'status': 'error',
                    'last_check': asyncio.get_event_loop().time(),
                    'errors': [str(e)]
                }
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.error(f"Max retries reached for chain {chain_id}")
                    await asyncio.sleep(CHECK_INTERVAL)
                continue

        logger.debug(f"Monitoring task stopped for chain {chain_id}")

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

    def get_supported_chains(self) -> List[str]:
        """Get list of supported chain IDs.

        Returns:
            List of configured chain identifiers
        """
        return list(self._chain_configs.keys())
