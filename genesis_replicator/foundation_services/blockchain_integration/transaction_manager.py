"""
Transaction Manager for blockchain integration.

This module manages transaction lifecycle, batching, and monitoring.
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception, TransactionNotFound

from ...foundation_services.exceptions import (
    BlockchainError,
    ChainConnectionError,
    ContractError,
    TransactionError,
    SecurityError
)


class TransactionManager:
    """Manages blockchain transaction operations and monitoring."""

    def __init__(self):
        """Initialize the transaction manager."""
        self._pending_transactions: Dict[str, Dict[str, Any]] = {}
        self._transaction_batches: Dict[str, List[str]] = {}
        self._nonce_locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def start(self) -> None:
        """Initialize and start the transaction manager.

        This method should be called before any other operations.
        """
        if self._initialized:
            return

        async with self._lock:
            self._initialized = True
            self._pending_transactions.clear()
            self._transaction_batches.clear()
            self._nonce_locks.clear()

    async def stop(self) -> None:
        """Stop and cleanup the transaction manager."""
        async with self._lock:
            self._pending_transactions.clear()
            self._transaction_batches.clear()
            self._nonce_locks.clear()
            self._initialized = False

    async def submit_transaction(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        transaction: Dict[str, Any],
        wait_for_receipt: bool = True
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Submit a transaction to the blockchain.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            transaction: Transaction parameters
            wait_for_receipt: Whether to wait for transaction receipt

        Returns:
            Tuple of (transaction hash, optional transaction receipt)

        Raises:
            TransactionError: If transaction submission fails
            SecurityError: If transaction validation fails
        """
        try:
            # Validate transaction signature
            if not self._validate_transaction_signature(transaction):
                raise SecurityError(
                    "Invalid transaction signature",
                    details={
                        "chain_id": chain_id,
                        "transaction": transaction
                    }
                )

            # Get or create nonce lock for the sender
            sender = transaction.get('from', None)
            if not sender:
                raise TransactionError(
                    "Transaction missing 'from' address",
                    details={"transaction": transaction}
                )

            nonce_lock = self._nonce_locks.setdefault(
                f"{chain_id}:{sender}",
                asyncio.Lock()
            )

            async with nonce_lock:
                # Get current nonce if not provided
                if 'nonce' not in transaction:
                    transaction['nonce'] = await web3.eth.get_transaction_count(
                        sender, 'pending'
                    )

                # Send transaction
                tx_hash = await web3.eth.send_transaction(transaction)
                tx_hash_hex = tx_hash.hex()

                # Store transaction info
                async with self._lock:
                    self._pending_transactions[tx_hash_hex] = {
                        'chain_id': chain_id,
                        'transaction': transaction,
                        'timestamp': web3.eth.get_block('latest').timestamp
                    }

                # Wait for receipt if requested
                receipt = None
                if wait_for_receipt:
                    receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
                    if receipt['status'] != 1:
                        raise TransactionError(
                            "Transaction failed",
                            details={
                                "chain_id": chain_id,
                                "transaction_hash": tx_hash_hex,
                                "receipt": dict(receipt)
                            }
                        )

                return tx_hash_hex, receipt

        except Web3Exception as e:
            raise TransactionError(
                f"Web3 error submitting transaction: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "transaction": transaction,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise TransactionError(
                f"Unexpected error submitting transaction: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "transaction": transaction,
                    "error": str(e)
                }
            )

    async def get_transaction_status(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        transaction_hash: str
    ) -> Dict[str, Any]:
        """Get the status of a transaction.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            transaction_hash: Transaction hash to check

        Returns:
            Transaction status information

        Raises:
            TransactionError: If status check fails
        """
        try:
            # Get transaction
            tx = await web3.eth.get_transaction(transaction_hash)
            if tx is None:
                raise TransactionError(
                    f"Transaction not found: {transaction_hash}",
                    details={
                        "chain_id": chain_id,
                        "transaction_hash": transaction_hash
                    }
                )

            # Get receipt if transaction is mined
            receipt = None
            if tx.get('blockNumber') is not None:
                receipt = await web3.eth.get_transaction_receipt(transaction_hash)

            return {
                'hash': transaction_hash,
                'chain_id': chain_id,
                'block_number': tx.get('blockNumber'),
                'from': tx.get('from'),
                'to': tx.get('to'),
                'value': tx.get('value'),
                'gas_price': tx.get('gasPrice'),
                'status': receipt.get('status') if receipt else None,
                'confirmations': (
                    await web3.eth.block_number - tx['blockNumber']
                    if tx.get('blockNumber') is not None
                    else 0
                )
            }

        except Web3Exception as e:
            raise TransactionError(
                f"Web3 error checking transaction status: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "transaction_hash": transaction_hash,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise TransactionError(
                f"Unexpected error checking transaction status: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "transaction_hash": transaction_hash,
                    "error": str(e)
                }
            )

    async def create_transaction_batch(
        self,
        batch_id: str,
        chain_id: str,
        transactions: List[Dict[str, Any]]
    ) -> None:
        """Create a batch of transactions.

        Args:
            batch_id: Unique identifier for the batch
            chain_id: Chain identifier
            transactions: List of transactions to batch

        Raises:
            TransactionError: If batch creation fails
        """
        try:
            async with self._lock:
                if batch_id in self._transaction_batches:
                    raise TransactionError(
                        f"Batch already exists: {batch_id}",
                        details={"batch_id": batch_id}
                    )

                self._transaction_batches[batch_id] = []
                for tx in transactions:
                    if 'from' not in tx:
                        raise TransactionError(
                            "Transaction missing 'from' address",
                            details={"transaction": tx}
                        )
                    self._transaction_batches[batch_id].append(tx)

        except Exception as e:
            raise TransactionError(
                f"Error creating transaction batch: {str(e)}",
                details={
                    "batch_id": batch_id,
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def submit_transaction_batch(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        batch_id: str,
        parallel: bool = False
    ) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """Submit a batch of transactions.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            batch_id: Batch identifier
            parallel: Whether to submit transactions in parallel

        Returns:
            List of (transaction hash, receipt) tuples

        Raises:
            TransactionError: If batch submission fails
        """
        try:
            if batch_id not in self._transaction_batches:
                raise TransactionError(
                    f"Batch not found: {batch_id}",
                    details={"batch_id": batch_id}
                )

            transactions = self._transaction_batches[batch_id]
            results = []

            if parallel:
                # Submit transactions in parallel
                tasks = [
                    self.submit_transaction(chain_id, web3, tx)
                    for tx in transactions
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for errors
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        raise TransactionError(
                            f"Error in parallel batch submission: {str(result)}",
                            details={
                                "batch_id": batch_id,
                                "transaction_index": i,
                                "error": str(result)
                            }
                        )
            else:
                # Submit transactions sequentially
                for tx in transactions:
                    result = await self.submit_transaction(chain_id, web3, tx)
                    results.append(result)

            return results

        except Exception as e:
            raise TransactionError(
                f"Error submitting transaction batch: {str(e)}",
                details={
                    "batch_id": batch_id,
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    def _validate_transaction_signature(self, transaction: Dict[str, Any]) -> bool:
        """Validate transaction signature.

        Args:
            transaction: Transaction data with signature

        Returns:
            True if signature is valid, False otherwise
        """
        # Implement actual signature validation
        # This is a placeholder - implement proper validation
        return 'signature' not in transaction or self._verify_signature(transaction)

    def _verify_signature(self, transaction: Dict[str, Any]) -> bool:
        """Verify transaction signature.

        Args:
            transaction: Transaction data with signature

        Returns:
            True if signature is valid, False otherwise
        """
        # Implement actual signature verification
        # This is a placeholder - implement proper verification
        return len(transaction.get('signature', '')) >= 64
