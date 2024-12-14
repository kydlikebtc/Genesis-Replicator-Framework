"""
Transaction Manager Module

This module implements the transaction management system for the Genesis Replicator Framework.
It provides functionality for transaction processing, gas optimization, and nonce management.
"""
from typing import Dict, Optional, Any
import asyncio
import logging
from web3 import Web3
from web3.types import TxParams, Wei

from .chain_manager import ChainManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionConfig:
    """Configuration for transaction parameters"""
    def __init__(
        self,
        gas_limit: int = 2000000,
        gas_price_strategy: str = "medium",
        max_priority_fee: Optional[int] = None,
        confirmation_blocks: int = 1
    ):
        self.gas_limit = gas_limit
        self.gas_price_strategy = gas_price_strategy
        self.max_priority_fee = max_priority_fee
        self.confirmation_blocks = confirmation_blocks

class NonceManager:
    """Manages transaction nonces for accounts"""
    def __init__(self):
        self.nonces: Dict[str, Dict[str, int]] = {}  # chain -> address -> nonce

    def get_nonce(self, chain: str, address: str) -> Optional[int]:
        """Get current nonce for address on chain"""
        return self.nonces.get(chain, {}).get(address)

    def update_nonce(self, chain: str, address: str, nonce: int) -> None:
        """Update nonce for address on chain"""
        if chain not in self.nonces:
            self.nonces[chain] = {}
        self.nonces[chain][address] = nonce

class TransactionManager:
    """
    Manages blockchain transactions and gas optimization.

    Attributes:
        chain_manager (ChainManager): Reference to chain manager
        nonce_manager (NonceManager): Nonce tracking
        pending_transactions (Dict): Tracks pending transactions
    """

    def __init__(self, chain_manager: ChainManager):
        """
        Initialize TransactionManager.

        Args:
            chain_manager (ChainManager): Chain manager instance
        """
        self.chain_manager = chain_manager
        self.nonce_manager = NonceManager()
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        self.default_config = TransactionConfig()
        logger.info("TransactionManager initialized")

    async def estimate_gas(
        self,
        tx_params: TxParams,
        chain_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Estimate gas for transaction.

        Args:
            tx_params (TxParams): Transaction parameters
            chain_name (Optional[str]): Target chain name

        Returns:
            Optional[int]: Estimated gas amount
        """
        web3 = self.chain_manager.get_web3(chain_name)
        if not web3:
            logger.error("No Web3 connection available")
            return None

        try:
            return web3.eth.estimate_gas(tx_params)
        except Exception as e:
            logger.error(f"Error estimating gas: {str(e)}")
            return None

    async def get_gas_price(
        self,
        chain_name: Optional[str] = None,
        strategy: str = "medium"
    ) -> Optional[Wei]:
        """
        Get optimal gas price based on strategy.

        Args:
            chain_name (Optional[str]): Chain name
            strategy (str): Price strategy (low/medium/high)

        Returns:
            Optional[Wei]: Gas price in Wei
        """
        web3 = self.chain_manager.get_web3(chain_name)
        if not web3:
            logger.error("No Web3 connection available")
            return None

        try:
            base_fee = web3.eth.get_block('latest').baseFeePerGas
            multiplier = {
                "low": 1.1,
                "medium": 1.3,
                "high": 1.5
            }.get(strategy, 1.3)

            return Wei(int(base_fee * multiplier))
        except Exception as e:
            logger.error(f"Error getting gas price: {str(e)}")
            return web3.eth.gas_price

    async def prepare_transaction(
        self,
        tx_params: TxParams,
        chain_name: Optional[str] = None,
        config: Optional[TransactionConfig] = None
    ) -> Optional[TxParams]:
        """
        Prepare transaction with optimal parameters.

        Args:
            tx_params (TxParams): Base transaction parameters
            chain_name (Optional[str]): Chain name
            config (Optional[TransactionConfig]): Transaction configuration

        Returns:
            Optional[TxParams]: Prepared transaction parameters
        """
        web3 = self.chain_manager.get_web3(chain_name)
        if not web3:
            logger.error("No Web3 connection available")
            return None

        config = config or self.default_config
        chain = chain_name or self.chain_manager.default_chain

        try:
            # Get or update nonce
            from_address = tx_params['from']
            nonce = self.nonce_manager.get_nonce(chain, from_address)
            if nonce is None:
                nonce = web3.eth.get_transaction_count(from_address)
            self.nonce_manager.update_nonce(chain, from_address, nonce + 1)

            # Estimate gas if not provided
            gas_limit = tx_params.get('gas', await self.estimate_gas(tx_params, chain_name))
            if not gas_limit:
                gas_limit = config.gas_limit

            # Get gas price
            gas_price = await self.get_gas_price(chain_name, config.gas_price_strategy)

            # Prepare final transaction
            prepared_tx = {
                **tx_params,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce
            }

            return prepared_tx

        except Exception as e:
            logger.error(f"Error preparing transaction: {str(e)}")
            return None

    async def send_transaction(
        self,
        tx_params: TxParams,
        private_key: str,
        chain_name: Optional[str] = None,
        config: Optional[TransactionConfig] = None
    ) -> Optional[str]:
        """
        Send transaction to blockchain.

        Args:
            tx_params (TxParams): Transaction parameters
            private_key (str): Private key for signing
            chain_name (Optional[str]): Chain name
            config (Optional[TransactionConfig]): Transaction configuration

        Returns:
            Optional[str]: Transaction hash if successful
        """
        web3 = self.chain_manager.get_web3(chain_name)
        if not web3:
            logger.error("No Web3 connection available")
            return None

        try:
            # Prepare transaction
            prepared_tx = await self.prepare_transaction(tx_params, chain_name, config)
            if not prepared_tx:
                return None

            # Sign transaction
            signed = web3.eth.account.sign_transaction(prepared_tx, private_key)

            # Send transaction
            tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)

            # Track pending transaction
            self.pending_transactions[tx_hash.hex()] = {
                'chain': chain_name or self.chain_manager.default_chain,
                'params': prepared_tx,
                'timestamp': asyncio.get_event_loop().time()
            }

            logger.info(f"Transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Error sending transaction: {str(e)}")
            return None

    async def wait_for_transaction(
        self,
        tx_hash: str,
        chain_name: Optional[str] = None,
        timeout: int = 120
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for transaction confirmation.

        Args:
            tx_hash (str): Transaction hash
            chain_name (Optional[str]): Chain name
            timeout (int): Maximum wait time in seconds

        Returns:
            Optional[Dict[str, Any]]: Transaction receipt if confirmed
        """
        web3 = self.chain_manager.get_web3(chain_name)
        if not web3:
            logger.error("No Web3 connection available")
            return None

        try:
            # Wait for transaction receipt
            receipt = await asyncio.wait_for(
                web3.eth.wait_for_transaction_receipt(tx_hash),
                timeout=timeout
            )

            # Clean up pending transaction
            if tx_hash in self.pending_transactions:
                del self.pending_transactions[tx_hash]

            return receipt

        except asyncio.TimeoutError:
            logger.error(f"Transaction {tx_hash} confirmation timeout")
            return None
        except Exception as e:
            logger.error(f"Error waiting for transaction: {str(e)}")
            return None

    async def monitor_pending_transactions(self) -> None:
        """Monitor and clean up pending transactions"""
        while True:
            current_time = asyncio.get_event_loop().time()
            for tx_hash, tx_data in list(self.pending_transactions.items()):
                # Check transactions older than 1 hour
                if current_time - tx_data['timestamp'] > 3600:
                    logger.warning(f"Transaction {tx_hash} pending for too long")
                    del self.pending_transactions[tx_hash]

            await asyncio.sleep(300)  # Check every 5 minutes
