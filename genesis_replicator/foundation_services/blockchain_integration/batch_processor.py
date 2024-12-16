"""
Batch transaction processor for blockchain operations.

This module handles batching and processing of blockchain transactions.
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from ...foundation_services.exceptions import (
    BlockchainError,
    TransactionError
)


class BatchProcessor:
    """Handles batching and processing of blockchain transactions."""

    def __init__(self, max_batch_size: int = 10, max_concurrent: int = 3):
        """Initialize the batch processor.

        Args:
            max_batch_size: Maximum number of transactions per batch
            max_concurrent: Maximum number of concurrent transactions
        """
        self._batch_size = max_batch_size
        self._max_concurrent = max_concurrent
        self._batch_interval = 1.0  # seconds
        self._max_retries = 3
        self._processing = False
        self._batch_queue: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def add_transaction(self, transaction: Dict[str, Any]) -> None:
        """Add a transaction to the batch queue.

        Args:
            transaction: Transaction parameters

        Raises:
            TransactionError: If batch processing fails
        """
        async with self._lock:
            self._batch_queue.append(transaction)

    async def process_batch(
        self,
        transactions: Optional[List[Dict[str, Any]]] = None,
        process_func: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a batch of transactions.

        Args:
            transactions: Optional list of transactions to process
            process_func: Optional function to process each transaction

        Yields:
            Dict containing transaction result
        """
        if transactions:
            self._batch_queue.extend(transactions)

        while self._batch_queue:
            batch = self._batch_queue[:self._batch_size]
            self._batch_queue = self._batch_queue[self._batch_size:]

            tasks = []
            for tx in batch:
                task = asyncio.create_task(self._process_transaction(tx, process_func))
                tasks.append(task)

            for result in asyncio.as_completed(tasks):
                try:
                    tx_result = await result
                    yield {
                        'success': True,
                        'result': tx_result
                    }
                except Exception as e:
                    yield {
                        'success': False,
                        'error': str(e)
                    }

    async def _process_transaction(
        self,
        transaction: Dict[str, Any],
        process_func: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> Any:
        """Process a single transaction with retry logic.

        Args:
            transaction: Transaction to process
            process_func: Optional function to process the transaction

        Returns:
            Transaction result

        Raises:
            TransactionError: If transaction processing fails after retries
        """
        retries = 0
        while retries < self._max_retries:
            try:
                async with self._semaphore:
                    if process_func:
                        return await process_func(transaction)
                    return await self._send_transaction(transaction)
            except Exception as e:
                retries += 1
                if retries >= self._max_retries:
                    raise TransactionError(
                        f"Transaction failed after {retries} retries: {str(e)}",
                        details={
                            "transaction": transaction,
                            "error": str(e)
                        }
                    )
                await asyncio.sleep(self._batch_interval)

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
