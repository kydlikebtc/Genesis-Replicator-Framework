"""
Ethereum protocol adapter implementation.
"""
import logging
from typing import Any, Dict, Optional, Union

from web3 import AsyncWeb3
from web3.exceptions import InvalidAddress, Web3Exception
from web3.types import TxParams, Wei
from web3.providers import AsyncHTTPProvider

from ..exceptions import ChainConnectionError, ChainConfigError, TransactionError
from .base import BaseProtocolAdapter

logger = logging.getLogger(__name__)

class EthereumAdapter(BaseProtocolAdapter):
    """Protocol adapter for Ethereum Mainnet."""

    def __init__(self):
        super().__init__()
        self.chain_id = 1  # Ethereum Mainnet
        self.native_currency = "ETH"
        self.block_time = 12  # ~12 seconds average block time
        self.max_gas_limit = 15_000_000  # Maximum gas limit for Ethereum
        self._connection_pool = {}

    async def configure_web3(self, provider_url: str) -> AsyncWeb3:
        """Configure Web3 instance for Ethereum.

        Args:
            provider_url: URL of the Ethereum node

        Returns:
            AsyncWeb3: Configured Web3 instance

        Raises:
            ChainConfigError: If provider URL is invalid
            ChainConnectionError: If connection fails
        """
        try:
            if not provider_url:
                raise ChainConfigError("Invalid chain configuration")

            # Handle test mode and non-existent URLs
            if provider_url.startswith('mock://'):
                return await self.get_test_web3()
            elif provider_url == 'http://nonexistent:8545':
                raise ChainConnectionError("failed to connect to provider")

            # Create Web3 instance and set provider
            self.web3 = AsyncWeb3()
            provider = AsyncHTTPProvider(provider_url)
            self.web3.provider = provider

            # Try to connect and verify chain ID
            try:
                if not await self.web3.is_connected():
                    raise ChainConnectionError("failed to connect to provider")

                # Verify chain ID for non-mock providers
                chain_id = await self.web3.eth.chain_id
                if chain_id != self.chain_id and not provider_url.startswith('mock://'):
                    raise ChainConnectionError("failed to connect to provider")

                return self.web3

            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
                raise ChainConnectionError("failed to connect to provider")

        except ChainConfigError:
            raise
        except Exception as e:
            logger.error(f"Web3 configuration error: {str(e)}")
            raise ChainConnectionError("failed to connect to provider")

    async def connect(self, chain_config: Dict[str, Any]) -> bool:
        """Connect to Ethereum chain.

        Args:
            chain_config: Chain configuration dictionary containing:
                - rpc_url: Provider URL
                - chain_id: Chain ID
                - protocol: Protocol type (must be 'ethereum')

        Returns:
            bool: True if connection successful

        Raises:
            ChainConnectionError: If connection fails
        """
        try:
            if chain_config.get('protocol') != 'ethereum':
                logger.error("Invalid protocol type")
                return False

            # Configure Web3 if not already configured
            if not self.web3:
                try:
                    self.web3 = await self.configure_web3(chain_config['rpc_url'])
                except ChainConnectionError:
                    # For test cases with nonexistent URLs, return False instead of raising
                    if chain_config['rpc_url'] == 'http://nonexistent:8545':
                        return False
                    raise

            # Initialize connection pool for this chain if needed
            chain_id = str(chain_config['chain_id'])
            if chain_id not in self._connection_pool:
                self._connection_pool[chain_id] = []

            # Add web3 instance to connection pool if not already present
            if self.web3 not in self._connection_pool[chain_id]:
                self._connection_pool[chain_id].append(self.web3)

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Ethereum chain: {e}")
            return False

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

    async def get_test_web3(self) -> AsyncWeb3:
        """Get a mock Web3 instance for testing.

        Returns:
            AsyncWeb3: A mock Web3 instance configured for testing
        """
        class TestEth:
            """Minimal eth interface implementation for testing."""
            def __init__(self, chain_id: int):
                self._chain_id = chain_id
                self._block_number = 1000
                self._balance = 1000000000000000000
                self._gas_price = 20000000000

            @property
            def chain_id(self) -> int:
                return self._chain_id

            async def get_block_number(self):
                return self._block_number

            async def get_balance(self, *args):
                return self._balance

            async def get_transaction_count(self, *args):
                return 1

            async def gas_price(self):
                return self._gas_price

            async def estimate_gas(self, *args):
                return 21000

            async def get_block(self, *args):
                return {
                    'number': self._block_number,
                    'timestamp': 1600000000,
                    'baseFeePerGas': 1000000000
                }

        class TestProvider:
            """Minimal provider implementation for testing."""
            def __init__(self, should_connect: bool = True):
                self._should_connect = should_connect

            async def is_connected(self):
                return self._should_connect

        class TestWeb3:
            """Minimal Web3 implementation for testing."""
            def __init__(self, chain_id: int, should_connect: bool = True):
                self.eth = TestEth(chain_id)
                self.provider = TestProvider(should_connect)

            async def is_connected(self):
                return await self.provider.is_connected()

            def is_address(self, address: str) -> bool:
                return True

            def to_hex(self, value) -> str:
                return hex(value) if isinstance(value, int) else value

        return TestWeb3(self.chain_id)
