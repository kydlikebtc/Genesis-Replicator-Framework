"""
Plugin Interface definitions for Genesis Replicator Framework.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import asyncio
from web3 import Web3
from web3.types import TxReceipt, Wei


@dataclass
class PluginMetadata:
    """Metadata for plugin identification and verification."""
    name: str
    version: str
    author: str
    description: str
    dependencies: Dict[str, str]
    permissions: list[str]
    checksum: str


class PluginInterface(ABC):
    """Base interface that all plugins must implement."""

    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self._is_enabled = False
        self._context: Dict[str, Any] = {}

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin with required resources."""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Start the plugin's main functionality."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop the plugin's functionality."""
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """Clean up resources used by the plugin."""
        pass

    def is_enabled(self) -> bool:
        """Check if the plugin is currently enabled."""
        return self._is_enabled

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set the plugin's execution context."""
        self._context = context

    def get_context(self) -> Dict[str, Any]:
        """Get the plugin's current execution context."""
        return self._context.copy()

    @abstractmethod
    async def handle_event(self, event_type: str, event_data: Any) -> Optional[Any]:
        """Handle framework events."""
        pass

    @abstractmethod
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass


class BlockchainPlugin(PluginInterface):
    """Base interface for blockchain-specific plugins."""

    @abstractmethod
    async def connect(self, network_url: str, chain_id: int) -> bool:
        """Connect to a blockchain network."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the blockchain network."""
        pass

    @abstractmethod
    async def deploy_contract(self,
                            contract_name: str,
                            bytecode: str,
                            abi: List[Dict[str, Any]],
                            constructor_args: Optional[List[Any]] = None) -> str:
        """Deploy a smart contract to the blockchain."""
        pass

    @abstractmethod
    async def call_contract(self,
                          contract_address: str,
                          function_name: str,
                          abi: List[Dict[str, Any]],
                          args: Optional[List[Any]] = None) -> Any:
        """Call a smart contract function."""
        pass

    @abstractmethod
    async def send_transaction(self,
                             contract_address: str,
                             function_name: str,
                             abi: List[Dict[str, Any]],
                             args: Optional[List[Any]] = None,
                             value: Optional[Wei] = None) -> TxReceipt:
        """Send a transaction to a smart contract."""
        pass

    @abstractmethod
    async def get_events(self,
                        contract_address: str,
                        event_name: str,
                        abi: List[Dict[str, Any]],
                        from_block: Optional[int] = None,
                        to_block: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get events emitted by a smart contract."""
        pass

    @abstractmethod
    async def validate_transaction(self,
                                 tx_hash: str,
                                 required_confirmations: int = 1) -> bool:
        """Validate a transaction has been confirmed."""
        pass

    @abstractmethod
    async def estimate_gas(self,
                          contract_address: str,
                          function_name: str,
                          abi: List[Dict[str, Any]],
                          args: Optional[List[Any]] = None) -> int:
        """Estimate gas cost for a contract function call."""
        pass

    @abstractmethod
    async def get_nonce(self, address: str) -> int:
        """Get the next nonce for an address."""
        pass

    @abstractmethod
    async def get_gas_price(self) -> Wei:
        """Get the current gas price."""
        pass
