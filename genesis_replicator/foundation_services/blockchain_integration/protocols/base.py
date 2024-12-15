"""
Base protocol adapter for blockchain integration.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from web3 import Web3
from web3.types import TxParams, Wei

class BaseProtocolAdapter(ABC):
    """Base class for blockchain protocol adapters."""

    def __init__(self):
        self.web3: Optional[Web3] = None
        self.chain_id: Optional[int] = None
        self.native_currency: str = ""
        self.block_time: int = 0  # Average block time in seconds

    @abstractmethod
    async def configure_web3(self, provider_url: str) -> None:
        """Configure Web3 instance for the protocol."""
        pass

    @abstractmethod
    async def estimate_gas(self, tx_params: TxParams) -> Wei:
        """Estimate gas for a transaction."""
        pass

    @abstractmethod
    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction receipt."""
        pass

    @abstractmethod
    async def send_transaction(self, tx_params: TxParams) -> str:
        """Send a transaction to the network."""
        pass

    @abstractmethod
    async def validate_address(self, address: str) -> bool:
        """Validate an address for the protocol."""
        pass

    @abstractmethod
    async def get_balance(self, address: str) -> Wei:
        """Get balance for an address."""
        pass

    @abstractmethod
    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Get block information."""
        pass

    @abstractmethod
    async def get_gas_price(self) -> Wei:
        """Get current gas price."""
        pass
