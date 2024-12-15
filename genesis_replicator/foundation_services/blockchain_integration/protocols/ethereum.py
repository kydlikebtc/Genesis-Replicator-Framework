"""
Ethereum protocol adapter implementation.
"""
from typing import Any, Dict, Optional, Union

from web3 import AsyncWeb3
from web3.exceptions import InvalidAddress, Web3Exception
from web3.types import TxParams, Wei

from ..exceptions import ChainConnectionError, TransactionError
from .base import BaseProtocolAdapter


class EthereumAdapter(BaseProtocolAdapter):
    """Protocol adapter for Ethereum Mainnet."""

    def __init__(self):
        super().__init__()
        self.chain_id = 1  # Ethereum Mainnet
        self.native_currency = "ETH"
        self.block_time = 12  # ~12 seconds average block time
        self.max_gas_limit = 15_000_000  # Maximum gas limit for Ethereum

    async def configure_web3(self, provider_url: str) -> None:
        """Configure Web3 instance for Ethereum."""
        try:
            provider = AsyncWeb3.AsyncHTTPProvider(provider_url)
            self.web3 = AsyncWeb3(provider)
            if not await self.web3.is_connected():
                raise ChainConnectionError("Failed to connect to Ethereum node")

            # Verify chain ID
            chain_id = await self.web3.eth.chain_id
            if chain_id != self.chain_id:
                raise ChainConnectionError(f"Connected to wrong chain. Expected {self.chain_id}, got {chain_id}")
        except Web3Exception as e:
            raise ChainConnectionError(f"Failed to configure Web3: {str(e)}")

    async def estimate_gas(self, tx_params: TxParams) -> Wei:
        """Estimate gas for a transaction on Ethereum with EIP-1559 support."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        try:
            # Get base fee from latest block
            latest_block = await self.web3.eth.get_block('latest')
            base_fee = latest_block.get('baseFeePerGas', 0)

            # Add 20% buffer for gas estimation due to potential base fee changes
            estimated_gas = await self.web3.eth.estimate_gas(tx_params)
            return Wei(int(estimated_gas * 1.2))
        except Web3Exception as e:
            raise TransactionError(f"Gas estimation failed: {str(e)}")

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt from Ethereum."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        try:
            receipt = await self.web3.eth.get_transaction_receipt(tx_hash)
            if not receipt:
                raise TransactionError(f"Transaction {tx_hash} not found")
            return dict(receipt)
        except Web3Exception as e:
            raise ChainConnectionError(f"Failed to get transaction receipt: {str(e)}")

    async def send_transaction(self, tx_params: TxParams) -> str:
        """Send a transaction to Ethereum with EIP-1559 support."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        # Validate gas limit
        if tx_params.get('gas', 0) > self.max_gas_limit:
            raise TransactionError(f"Gas limit exceeds maximum allowed ({self.max_gas_limit})")

        try:
            # Handle EIP-1559 transaction type
            if 'maxFeePerGas' not in tx_params and 'gasPrice' not in tx_params:
                latest_block = await self.web3.eth.get_block('latest')
                base_fee = latest_block.get('baseFeePerGas', 0)

                # Set maxFeePerGas to 2x current base fee
                tx_params['maxFeePerGas'] = Wei(int(base_fee * 2))
                # Set maxPriorityFeePerGas to 1.5 gwei
                tx_params['maxPriorityFeePerGas'] = Wei(1500000000)

            # Send transaction
            tx_hash = await self.web3.eth.send_transaction(tx_params)
            hex_hash = tx_hash.hex()
            return f"0x{hex_hash}" if not hex_hash.startswith('0x') else hex_hash
        except Web3Exception as e:
            raise TransactionError(f"Transaction failed: {str(e)}")

    async def validate_address(self, address: str) -> bool:
        """Validate an Ethereum address."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        try:
            return self.web3.is_address(address)
        except InvalidAddress:
            return False
        except Web3Exception as e:
            raise ChainConnectionError(f"Failed to validate address: {str(e)}")

    async def get_balance(self, address: str) -> Wei:
        """Get ETH balance for an address."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        try:
            if not await self.validate_address(address):
                raise TransactionError("Invalid address")

            balance = await self.web3.eth.get_balance(address)
            return Wei(int(balance))
        except Web3Exception as e:
            raise ChainConnectionError(f"Failed to get balance: {str(e)}")

    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Get block information from Ethereum."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        try:
            block = await self.web3.eth.get_block(block_identifier)
            return dict(block)
        except Web3Exception as e:
            raise ChainConnectionError(f"Failed to get block: {str(e)}")

    async def get_gas_price(self) -> Wei:
        """Get current gas price on Ethereum with EIP-1559 support."""
        if not self.web3:
            raise ChainConnectionError("Web3 not configured")

        try:
            # Get latest block for base fee
            latest_block = await self.web3.eth.get_block('latest')
            base_fee = latest_block.get('baseFeePerGas', 0)

            # For EIP-1559, return base fee + 1.5 gwei priority fee
            if base_fee:
                return Wei(int(base_fee + 1500000000))  # base fee + 1.5 gwei

            # Fallback to legacy gas price
            gas_price = await self.web3.eth.gas_price
            return Wei(int(gas_price))
        except Web3Exception as e:
            raise ChainConnectionError(f"Failed to get gas price: {str(e)}")
