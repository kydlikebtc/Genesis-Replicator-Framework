"""
BNB Chain protocol adapter implementation.
"""
from typing import Any, Dict, Optional, Union

from web3 import Web3
from web3.exceptions import InvalidAddress
from web3.types import TxParams, Wei

from .base import BaseProtocolAdapter

class BNBChainAdapter(BaseProtocolAdapter):
    """Protocol adapter for BNB Chain."""

    def __init__(self):
        super().__init__()
        self.chain_id = 56  # BNB Chain Mainnet
        self.native_currency = "BNB"
        self.block_time = 3  # 3 seconds average block time
        self.max_gas_limit = 30_000_000  # Maximum gas limit for BNB Chain

    async def configure_web3(self, provider_url: str) -> None:
        """Configure Web3 instance for BNB Chain."""
        self.web3 = Web3(Web3.HTTPProvider(provider_url))
        if not self.web3.is_connected():
            raise ConnectionError("Failed to connect to BNB Chain node")

        # Verify chain ID
        chain_id = await self.web3.eth.chain_id
        if chain_id != self.chain_id:
            raise ValueError(f"Connected to wrong chain. Expected {self.chain_id}, got {chain_id}")

    async def estimate_gas(self, tx_params: TxParams) -> Wei:
        """Estimate gas for a transaction on BNB Chain."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        try:
            # Add 10% buffer for gas estimation
            estimated_gas = await self.web3.eth.estimate_gas(tx_params)
            return Wei(int(estimated_gas * 1.1))
        except Exception as e:
            raise ValueError(f"Gas estimation failed: {str(e)}")

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt from BNB Chain."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        receipt = await self.web3.eth.get_transaction_receipt(tx_hash)
        if not receipt:
            raise ValueError(f"Transaction {tx_hash} not found")
        return dict(receipt)

    async def send_transaction(self, tx_params: TxParams) -> str:
        """Send a transaction to BNB Chain."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        # Validate gas limit
        if tx_params.get('gas', 0) > self.max_gas_limit:
            raise ValueError(f"Gas limit exceeds maximum allowed ({self.max_gas_limit})")

        try:
            # Send transaction
            tx_hash = await self.web3.eth.send_transaction(tx_params)
            return tx_hash.hex()
        except Exception as e:
            raise ValueError(f"Transaction failed: {str(e)}")

    async def validate_address(self, address: str) -> bool:
        """Validate a BNB Chain address."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        try:
            return self.web3.is_address(address)
        except InvalidAddress:
            return False

    async def get_balance(self, address: str) -> Wei:
        """Get BNB balance for an address."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        if not await self.validate_address(address):
            raise ValueError("Invalid address")

        balance = await self.web3.eth.get_balance(address)
        return Wei(balance)

    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Get block information from BNB Chain."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        block = await self.web3.eth.get_block(block_identifier)
        return dict(block)

    async def get_gas_price(self) -> Wei:
        """Get current gas price on BNB Chain."""
        if not self.web3:
            raise RuntimeError("Web3 not configured")

        gas_price = await self.web3.eth.gas_price
        return Wei(gas_price)
