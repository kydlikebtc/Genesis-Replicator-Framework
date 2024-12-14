"""
Sync Manager Module

This module implements the blockchain data synchronization system for the Genesis Replicator Framework.
It provides functionality for state synchronization and data consistency management.
"""
from typing import Dict, Optional, Any, List
import asyncio
import logging
from datetime import datetime
from web3 import Web3
from web3.types import BlockData

from .chain_manager import ChainManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncConfig:
    """Configuration for blockchain synchronization"""
    def __init__(
        self,
        start_block: Optional[int] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        sync_interval: int = 15
    ):
        self.start_block = start_block
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.sync_interval = sync_interval

class BlockRange:
    """Represents a range of blocks to sync"""
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end
        self.completed = False
        self.retries = 0

class SyncManager:
    """
    Manages blockchain data synchronization and state management.

    Attributes:
        chain_manager (ChainManager): Reference to chain manager
        sync_states (Dict): Tracks sync state for each chain
        active_syncs (Dict): Currently active sync operations
    """

    def __init__(self, chain_manager: ChainManager):
        """
        Initialize SyncManager.

        Args:
            chain_manager (ChainManager): Chain manager instance
        """
        self.chain_manager = chain_manager
        self.sync_states: Dict[str, Dict[str, Any]] = {}
        self.active_syncs: Dict[str, bool] = {}
        self.default_config = SyncConfig()
        logger.info("SyncManager initialized")

    async def start_sync(
        self,
        chain_name: Optional[str] = None,
        config: Optional[SyncConfig] = None
    ) -> bool:
        """
        Start blockchain synchronization.

        Args:
            chain_name (Optional[str]): Chain to sync
            config (Optional[SyncConfig]): Sync configuration

        Returns:
            bool: True if sync started successfully
        """
        chain = chain_name or self.chain_manager.default_chain
        if not chain:
            logger.error("No chain specified or default chain available")
            return False

        if chain in self.active_syncs and self.active_syncs[chain]:
            logger.warning(f"Sync already active for chain {chain}")
            return False

        try:
            web3 = self.chain_manager.get_web3(chain)
            if not web3:
                logger.error(f"No Web3 connection available for chain {chain}")
                return False

            config = config or self.default_config
            current_block = web3.eth.block_number
            start_block = config.start_block or self._get_last_synced_block(chain) + 1

            if start_block > current_block:
                logger.info(f"Chain {chain} already synced to latest block")
                return True

            self.active_syncs[chain] = True
            self.sync_states[chain] = {
                'start_block': start_block,
                'current_block': start_block,
                'latest_block': current_block,
                'last_update': datetime.now(),
                'config': config
            }

            # Start sync process
            asyncio.create_task(self._sync_process(chain))
            logger.info(f"Started sync for chain {chain} from block {start_block}")
            return True

        except Exception as e:
            logger.error(f"Error starting sync: {str(e)}")
            return False


    async def stop_sync(self, chain_name: Optional[str] = None) -> bool:
        """
        Stop blockchain synchronization.

        Args:
            chain_name (Optional[str]): Chain to stop syncing

        Returns:
            bool: True if sync stopped successfully
        """
        chain = chain_name or self.chain_manager.default_chain
        if chain in self.active_syncs:
            self.active_syncs[chain] = False
            logger.info(f"Stopped sync for chain {chain}")
            return True
        return False

    def get_sync_status(self, chain_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get current sync status.

        Args:
            chain_name (Optional[str]): Chain name

        Returns:
            Optional[Dict[str, Any]]: Sync status information
        """
        chain = chain_name or self.chain_manager.default_chain
        return self.sync_states.get(chain)

    async def _sync_process(self, chain_name: str) -> None:
        """
        Main sync process for a chain.

        Args:
            chain_name (str): Chain to sync
        """
        while self.active_syncs.get(chain_name, False):
            try:
                state = self.sync_states[chain_name]
                config = state['config']
                web3 = self.chain_manager.get_web3(chain_name)

                current_block = state['current_block']
                latest_block = web3.eth.block_number
                batch_end = min(current_block + config.batch_size, latest_block)

                if current_block >= latest_block:
                    # Up to date, wait for new blocks
                    await asyncio.sleep(config.sync_interval)
                    continue

                # Process batch of blocks
                blocks = await self._fetch_blocks(
                    web3,
                    current_block,
                    batch_end,
                    config.max_retries
                )

                if blocks:
                    await self._process_blocks(chain_name, blocks)
                    state['current_block'] = batch_end + 1
                    state['last_update'] = datetime.now()
                    logger.info(f"Synced blocks {current_block} to {batch_end} on {chain_name}")

            except Exception as e:
                logger.error(f"Error in sync process: {str(e)}")
                await asyncio.sleep(config.sync_interval)

    async def _fetch_blocks(
        self,
        web3: Web3,
        start: int,
        end: int,
        max_retries: int
    ) -> Optional[List[BlockData]]:
        """
        Fetch a range of blocks.

        Args:
            web3 (Web3): Web3 instance
            start (int): Start block
            end (int): End block
            max_retries (int): Maximum retry attempts

        Returns:
            Optional[List[BlockData]]: List of block data
        """
        retries = 0
        while retries < max_retries:
            try:
                return [
                    web3.eth.get_block(block_num, full_transactions=True)
                    for block_num in range(start, end + 1)
                ]
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    logger.error(f"Failed to fetch blocks {start}-{end}: {str(e)}")
                    return None
                await asyncio.sleep(2 ** retries)  # Exponential backoff

    async def _process_blocks(self, chain_name: str, blocks: List[BlockData]) -> None:
        """
        Process fetched blocks.

        Args:
            chain_name (str): Chain name
            blocks (List[BlockData]): Blocks to process
        """
        for block in blocks:
            try:
                # Process block data
                # This is where you would implement specific processing logic
                # such as updating state, triggering events, etc.
                pass
            except Exception as e:
                logger.error(f"Error processing block {block.number}: {str(e)}")

    def _get_last_synced_block(self, chain_name: str) -> int:
        """
        Get last successfully synced block.

        Args:
            chain_name (str): Chain name

        Returns:
            int: Last synced block number
        """
        return self.sync_states.get(chain_name, {}).get('current_block', -1)
