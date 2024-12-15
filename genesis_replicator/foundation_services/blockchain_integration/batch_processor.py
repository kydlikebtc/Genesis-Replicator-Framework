"""
Batch transaction processor for blockchain operations.

This module handles batching and processing of blockchain transactions.
"""
import asyncio
from typing import List, Dict, Any, Optional
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from ...foundation_services.exceptions import (
    BlockchainError,
    TransactionError
)


class BatchProcessor:
    """Handles batching and processing of blockchain transactions."""

    def __init__(self):
        """Initialize the batch processor."""
        self._batch_size = 10
        self._batch_interval = 1.0  # seconds
        self._max_retries = 3
        self._processing = False
        self._batch_queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def add_transaction(self, transaction: Dict[str, Any]) -> None:
        """Add a transaction to the batch queue.

        Args:
            transaction: Transaction parameters

        Raises:
            TransactionError: If batch processing fails
        """
        async with self._lock:
            self._batch_queue.append(transaction)
            if len(self._batch_queue) >= self._batch_size and not self._processing:
                await self._process_batch()

    async def _process_batch(self) -> None:
        """Process a batch of transactions."""
        try:
            self._processing = True
            batch = self._batch_queue[:self._batch_size]
            self._batch_queue = self._batch_queue[self._batch_size:]

            # Process transactions in parallel
            tasks = [
                self._send_transaction(tx)
                for tx in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results
            for tx, result in zip(batch, results):
                if isinstance(result, Exception):
                    print(f"Transaction failed: {str(result)}")
                    # Add to retry queue if retries remaining
                    if tx.get('retries', 0) < self._max_retries:
                        tx['retries'] = tx.get('retries', 0) + 1
                        self._batch_queue.append(tx)

        except Exception as e:
            raise TransactionError(
                f"Batch processing failed: {str(e)}",
                details={"error": str(e)}
            )
        finally:
            self._processing = False

    async def _send_transaction(self, transaction: Dict[str, Any]) -> str:
        """Send a single transaction.

        Args:
            transaction: Transaction parameters

        Returns:
            Transaction hash

        Raises:
            TransactionError: If transaction fails
        """
        try:
            web3: AsyncWeb3 = transaction['web3']
            tx_hash = await web3.eth.send_transaction(transaction)
            return tx_hash.hex()
        except Web3Exception as e:
            raise TransactionError(
                f"Transaction failed: {str(e)}",
                details={
                    "transaction": transaction,
                    "error": str(e)
                }
            )

    async def start(self) -> None:
        """Start the batch processor."""
        while True:
            await asyncio.sleep(self._batch_interval)
            if self._batch_queue and not self._processing:
                await self._process_batch()

    async def configure_chain(
        self,
        chain_id: int,
        batch_size: Optional[int] = None,
        batch_interval: Optional[float] = None,
        max_retries: Optional[int] = None
    ) -> None:
        """Configure batch processor parameters.

        Args:
            chain_id: Chain identifier
            batch_size: Number of transactions per batch
            batch_interval: Interval between batch processing
            max_retries: Maximum number of retry attempts
        """
        if batch_size is not None:
            self._batch_size = batch_size
        if batch_interval is not None:
            self._batch_interval = batch_interval
        if max_retries is not None:
            self._max_retries = max_retries
