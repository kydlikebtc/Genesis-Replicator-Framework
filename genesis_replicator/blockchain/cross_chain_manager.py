"""
Cross-chain transaction manager for coordinating multi-chain operations.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime
import hashlib

from ..foundation_services.blockchain_integration.chain_manager import ChainManager
from ..foundation_services.blockchain_integration.transaction_manager import TransactionManager
from ..security.contract_security import ContractSecurity

logger = logging.getLogger(__name__)

@dataclass
class CrossChainTransaction:
    """Represents a cross-chain transaction."""
    transaction_id: str
    source_chain: str
    target_chain: str
    source_tx: Dict[str, Any]
    target_tx: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    dependencies: Set[str]
    confirmations: Dict[str, int]

class CrossChainManager:
    """Manages cross-chain transactions and coordination."""

    def __init__(
        self,
        chain_manager: ChainManager,
        transaction_manager: TransactionManager,
        contract_security: ContractSecurity
    ):
        """Initialize cross-chain manager.

        Args:
            chain_manager: Chain manager instance
            transaction_manager: Transaction manager instance
            contract_security: Contract security instance
        """
        self._chain_manager = chain_manager
        self._transaction_manager = transaction_manager
        self._contract_security = contract_security
        self._transactions: Dict[str, CrossChainTransaction] = {}
        self._lock = asyncio.Lock()
        self._pending_confirmations: Dict[str, Set[str]] = {}
        logger.info("Cross-chain manager initialized")

    async def initiate_cross_chain_transaction(
        self,
        source_chain: str,
        target_chain: str,
        source_tx: Dict[str, Any],
        target_tx: Dict[str, Any],
        dependencies: Optional[Set[str]] = None
    ) -> str:
        """Initiate a cross-chain transaction.

        Args:
            source_chain: Source blockchain identifier
            target_chain: Target blockchain identifier
            source_tx: Source transaction details
            target_tx: Target transaction details
            dependencies: Optional transaction dependencies

        Returns:
            Transaction ID

        Raises:
            ValueError: If chain configuration is invalid
            RuntimeError: If transaction initiation fails
        """
        try:
            # Validate chains
            if not await self._chain_manager.is_chain_supported(source_chain):
                raise ValueError(f"Source chain {source_chain} not supported")
            if not await self._chain_manager.is_chain_supported(target_chain):
                raise ValueError(f"Target chain {target_chain} not supported")

            # Generate transaction ID
            tx_data = f"{source_chain}-{target_chain}-{datetime.now().isoformat()}"
            transaction_id = hashlib.sha256(tx_data.encode()).hexdigest()[:16]

            # Create transaction record
            transaction = CrossChainTransaction(
                transaction_id=transaction_id,
                source_chain=source_chain,
                target_chain=target_chain,
                source_tx=source_tx,
                target_tx=target_tx,
                status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                dependencies=dependencies or set(),
                confirmations={source_chain: 0, target_chain: 0}
            )

            async with self._lock:
                self._transactions[transaction_id] = transaction
                if dependencies:
                    for dep_id in dependencies:
                        if dep_id not in self._transactions:
                            raise ValueError(f"Dependency {dep_id} not found")

            # Validate and prepare transactions
            await self._validate_transactions(transaction)
            await self._prepare_transactions(transaction)

            logger.info(f"Initiated cross-chain transaction: {transaction_id}")
            return transaction_id

        except Exception as e:
            logger.error(f"Failed to initiate cross-chain transaction: {str(e)}")
            raise

    async def execute_transaction(
        self,
        transaction_id: str
    ) -> None:
        """Execute a cross-chain transaction.

        Args:
            transaction_id: Transaction identifier

        Raises:
            ValueError: If transaction not found
            RuntimeError: If execution fails
        """
        if transaction_id not in self._transactions:
            raise ValueError(f"Transaction {transaction_id} not found")

        transaction = self._transactions[transaction_id]
        try:
            # Check dependencies
            for dep_id in transaction.dependencies:
                dep_tx = self._transactions.get(dep_id)
                if not dep_tx or dep_tx.status != "completed":
                    raise RuntimeError(f"Dependency {dep_id} not ready")

            # Execute source transaction
            source_result = await self._transaction_manager.submit_transaction(
                transaction.source_chain,
                transaction.source_tx
            )

            # Wait for source confirmation
            await self._wait_for_confirmation(
                transaction.source_chain,
                source_result["hash"]
            )

            # Execute target transaction
            target_result = await self._transaction_manager.submit_transaction(
                transaction.target_chain,
                transaction.target_tx
            )

            # Wait for target confirmation
            await self._wait_for_confirmation(
                transaction.target_chain,
                target_result["hash"]
            )

            # Update transaction status
            async with self._lock:
                transaction.status = "completed"
                transaction.updated_at = datetime.now()

            logger.info(f"Completed cross-chain transaction: {transaction_id}")

        except Exception as e:
            logger.error(f"Failed to execute transaction {transaction_id}: {str(e)}")
            async with self._lock:
                transaction.status = "failed"
                transaction.updated_at = datetime.now()
            raise RuntimeError(f"Transaction execution failed: {str(e)}")

    async def get_transaction_status(
        self,
        transaction_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get status of a cross-chain transaction.

        Args:
            transaction_id: Transaction identifier

        Returns:
            Transaction status details if found
        """
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            return None

        return {
            "transaction_id": transaction.transaction_id,
            "status": transaction.status,
            "source_chain": transaction.source_chain,
            "target_chain": transaction.target_chain,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat(),
            "confirmations": transaction.confirmations
        }

    async def _validate_transactions(
        self,
        transaction: CrossChainTransaction
    ) -> None:
        """Validate transaction security and parameters.

        Args:
            transaction: Transaction to validate

        Raises:
            ValueError: If validation fails
        """
        # Validate source transaction
        await self._contract_security.validate_transaction(
            transaction.source_chain,
            transaction.source_tx
        )

        # Validate target transaction
        await self._contract_security.validate_transaction(
            transaction.target_chain,
            transaction.target_tx
        )

    async def _prepare_transactions(
        self,
        transaction: CrossChainTransaction
    ) -> None:
        """Prepare transactions for execution.

        Args:
            transaction: Transaction to prepare

        Raises:
            RuntimeError: If preparation fails
        """
        try:
            # Prepare source transaction
            transaction.source_tx = await self._transaction_manager.prepare_transaction(
                transaction.source_chain,
                transaction.source_tx
            )

            # Prepare target transaction
            transaction.target_tx = await self._transaction_manager.prepare_transaction(
                transaction.target_chain,
                transaction.target_tx
            )

        except Exception as e:
            logger.error(f"Failed to prepare transactions: {str(e)}")
            raise RuntimeError(f"Transaction preparation failed: {str(e)}")

    async def _wait_for_confirmation(
        self,
        chain: str,
        tx_hash: str,
        required_confirmations: int = 12
    ) -> None:
        """Wait for transaction confirmation.

        Args:
            chain: Chain identifier
            tx_hash: Transaction hash
            required_confirmations: Required number of confirmations

        Raises:
            RuntimeError: If confirmation fails
        """
        try:
            confirmations = 0
            while confirmations < required_confirmations:
                confirmations = await self._chain_manager.get_transaction_confirmations(
                    chain,
                    tx_hash
                )
                if confirmations >= required_confirmations:
                    break
                await asyncio.sleep(15)  # Wait for next block

        except Exception as e:
            logger.error(f"Failed to get transaction confirmation: {str(e)}")
            raise RuntimeError(f"Transaction confirmation failed: {str(e)}")
