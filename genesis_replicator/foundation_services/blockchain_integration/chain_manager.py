"""
Chain Manager Module

This module implements the blockchain chain management system for the Genesis Replicator Framework.
It provides functionality for managing multiple blockchain connections and cross-chain operations.
"""
from typing import List, Dict, Optional
import asyncio
import logging
from web3 import Web3
from web3.middleware import geth_poa_middleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChainConfig:
    """Configuration for blockchain connection"""
    def __init__(self, chain_id: int, rpc_url: str, name: str):
        self.chain_id = chain_id
        self.rpc_url = rpc_url
        self.name = name

class ChainConnection:
    """Represents an active blockchain connection"""
    def __init__(self, config: ChainConfig, web3: Web3):
        self.config = config
        self.web3 = web3
        self.connected = False
        self.last_block = 0

class ChainManager:
    """
    Manages multiple blockchain connections and operations.

    Attributes:
        chains (Dict[str, ChainConnection]): Active chain connections
        default_chain (str): Default chain for operations
    """

    def __init__(self):
        """Initialize the ChainManager"""
        self.chains: Dict[str, ChainConnection] = {}
        self.default_chain: Optional[str] = None
        logger.info("ChainManager initialized")

    async def connect_to_chain(self, config: ChainConfig) -> bool:
        """
        Connect to a blockchain network.

        Args:
            config (ChainConfig): Chain configuration

        Returns:
            bool: True if connection successful
        """
        try:
            web3 = Web3(Web3.HTTPProvider(config.rpc_url))

            # Add PoA middleware for networks like BSC, Polygon
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)

            if not web3.is_connected():
                logger.error(f"Failed to connect to chain {config.name}")
                return False

            connection = ChainConnection(config, web3)
            connection.connected = True
            connection.last_block = await self._get_latest_block(web3)

            self.chains[config.name] = connection

            if not self.default_chain:
                self.default_chain = config.name

            logger.info(f"Successfully connected to chain {config.name}")
            return True

        except Exception as e:
            logger.error(f"Error connecting to chain {config.name}: {str(e)}")
            return False

    async def disconnect_from_chain(self, chain_name: str) -> bool:
        """
        Disconnect from a blockchain network.

        Args:
            chain_name (str): Name of the chain to disconnect

        Returns:
            bool: True if disconnection successful
        """
        if chain_name in self.chains:
            try:
                # Clean up connection
                self.chains[chain_name].connected = False
                del self.chains[chain_name]

                if self.default_chain == chain_name:
                    self.default_chain = next(iter(self.chains)) if self.chains else None

                logger.info(f"Disconnected from chain {chain_name}")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from chain {chain_name}: {str(e)}")
                return False
        return False

    def get_web3(self, chain_name: Optional[str] = None) -> Optional[Web3]:
        """
        Get Web3 instance for a specific chain.

        Args:
            chain_name (Optional[str]): Chain name, uses default if None

        Returns:
            Optional[Web3]: Web3 instance if available
        """
        chain = chain_name or self.default_chain
        if chain and chain in self.chains:
            return self.chains[chain].web3
        return None

    def get_connected_chains(self) -> List[str]:
        """
        Get list of connected chain names.

        Returns:
            List[str]: Names of connected chains
        """
        return list(self.chains.keys())

    def is_connected(self, chain_name: str) -> bool:
        """
        Check if connected to a specific chain.

        Args:
            chain_name (str): Chain to check

        Returns:
            bool: True if connected
        """
        return (
            chain_name in self.chains
            and self.chains[chain_name].connected
            and self.chains[chain_name].web3.is_connected()
        )

    async def _get_latest_block(self, web3: Web3) -> int:
        """
        Get latest block number from chain.

        Args:
            web3 (Web3): Web3 instance

        Returns:
            int: Latest block number
        """
        try:
            return web3.eth.block_number
        except Exception as e:
            logger.error(f"Error getting latest block: {str(e)}")
            return 0


    async def monitor_chain_health(self) -> None:
        """Monitor health of connected chains"""
        while True:
            for chain_name, connection in list(self.chains.items()):
                try:
                    if not connection.web3.is_connected():
                        logger.warning(f"Lost connection to chain {chain_name}")
                        connection.connected = False
                    else:
                        current_block = await self._get_latest_block(connection.web3)
                        if current_block > connection.last_block:
                            connection.last_block = current_block
                            logger.debug(f"Chain {chain_name} at block {current_block}")
                except Exception as e:
                    logger.error(f"Error monitoring chain {chain_name}: {str(e)}")

            await asyncio.sleep(10)  # Check every 10 seconds
