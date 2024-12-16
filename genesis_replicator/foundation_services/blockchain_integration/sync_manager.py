"""
Sync Manager for blockchain integration.

This module manages blockchain synchronization, state management, and reorg handling.
"""
import asyncio
from typing import Dict, List, Optional, Any, Set
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from ...foundation_services.exceptions import (
    BlockchainError,
    ChainConnectionError,
    SyncError
)


class SyncManager:
    """Manages blockchain synchronization and state management."""

    def __init__(self):
        """Initialize the sync manager."""
        self._sync_tasks: Dict[str, asyncio.Task] = {}
        self._sync_states: Dict[str, Dict[str, Any]] = {}
        self._reorg_monitors: Dict[str, asyncio.Task] = {}
        self._processed_blocks: Dict[str, Set[int]] = {}
        self._web3_instances: Dict[str, AsyncWeb3] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the sync manager.

        This method should be called before any other operations.
        """
        if self._initialized:
            return

        async with self._lock:
            self._initialized = True
            self._sync_tasks.clear()
            self._sync_states.clear()
            self._reorg_monitors.clear()
            self._processed_blocks.clear()
            self._web3_instances.clear()

    async def cleanup(self) -> None:
        """Stop and cleanup the sync manager.

        This method should be called during shutdown.
        """
        async with self._lock:
            # Stop all running syncs
            for chain_id in list(self._sync_tasks.keys()):
                await self.stop_sync(chain_id)

            self._initialized = False

    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure the sync manager with chain configurations.

        Args:
            config: Configuration dictionary containing chain settings
        """
        if not self._initialized:
            raise SyncError("Sync manager not initialized")

        async with self._lock:
            for chain_id, chain_config in config.get('chains', {}).items():
                web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(chain_config['rpc_url']))
                self._web3_instances[chain_id] = web3

    async def start_sync(
        self,
        chain_id: str,
        start_block: Optional[int] = None,
        batch_size: int = 100
    ) -> None:
        """Start blockchain synchronization.

        Args:
            chain_id: Chain identifier
            start_block: Starting block number (default: latest - 1000)
            batch_size: Number of blocks to process in each batch

        Raises:
            SyncError: If sync start fails
        """
        if not self._initialized:
            raise SyncError("Sync manager not initialized")

        try:
            async with self._lock:
                if chain_id in self._sync_tasks:
                    raise SyncError(
                        f"Sync already running for chain {chain_id}",
                        details={"chain_id": chain_id}
                    )

                if chain_id not in self._web3_instances:
                    raise SyncError(
                        f"Chain {chain_id} not configured",
                        details={"chain_id": chain_id}
                    )

                web3 = self._web3_instances[chain_id]

                # Initialize sync state
                latest_block = await web3.eth.block_number
                if start_block is None:
                    start_block = max(0, latest_block - 1000)

                self._sync_states[chain_id] = {
                    'current_block': start_block,
                    'latest_block': latest_block,
                    'batch_size': batch_size,
                    'running': True,
                    'reorg_detected': False,
                    'error': None
                }
                self._processed_blocks[chain_id] = set()

                # Start sync task
                self._sync_tasks[chain_id] = asyncio.create_task(
                    self._sync_blockchain(chain_id)
                )

                # Start reorg monitor
                self._reorg_monitors[chain_id] = asyncio.create_task(
                    self._monitor_reorgs(chain_id)
                )

        except Web3Exception as e:
            raise BlockchainError(
                f"Web3 error starting sync: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise BlockchainError(
                f"Unexpected error starting sync: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def stop_sync(self, chain_id: str) -> None:
        """Stop blockchain synchronization.

        Args:
            chain_id: Chain identifier

        Raises:
            SyncError: If sync stop fails
        """
        if not self._initialized:
            raise SyncError("Sync manager not initialized")

        try:
            async with self._lock:
                if chain_id not in self._sync_tasks:
                    raise SyncError(
                        f"No sync running for chain {chain_id}",
                        details={"chain_id": chain_id}
                    )

                # Stop sync state
                self._sync_states[chain_id]['running'] = False

                # Cancel tasks
                self._sync_tasks[chain_id].cancel()
                self._reorg_monitors[chain_id].cancel()

                # Cleanup
                del self._sync_tasks[chain_id]
                del self._sync_states[chain_id]
                del self._reorg_monitors[chain_id]
                del self._processed_blocks[chain_id]

        except Exception as e:
            raise BlockchainError(
                f"Error stopping sync: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def get_sync_status(self, chain_id: str) -> Dict[str, Any]:
        """Get synchronization status.

        Args:
            chain_id: Chain identifier

        Returns:
            Sync status information

        Raises:
            SyncError: If status check fails
        """
        if not self._initialized:
            raise SyncError("Sync manager not initialized")

        try:
            if chain_id not in self._sync_states:
                raise SyncError(
                    f"No sync found for chain {chain_id}",
                    details={"chain_id": chain_id}
                )

            state = self._sync_states[chain_id]
            return {
                'chain_id': chain_id,
                'current_block': state['current_block'],
                'latest_block': state['latest_block'],
                'blocks_remaining': state['latest_block'] - state['current_block'],
                'is_syncing': state['running'],
                'processed_blocks': len(self._processed_blocks[chain_id]),
                'reorg_detected': state.get('reorg_detected', False),
                'error': state.get('error')
            }

        except Exception as e:
            raise SyncError(
                f"Error getting sync status: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )

    async def _sync_blockchain(self, chain_id: str) -> None:
        """Synchronize blockchain data.

        Args:
            chain_id: Chain identifier
        """
        web3 = self._web3_instances[chain_id]
        while self._sync_states[chain_id]['running']:
            try:
                state = self._sync_states[chain_id]
                current_block = state['current_block']
                latest_block = await web3.eth.block_number
                batch_size = state['batch_size']

                # Update latest known block
                state['latest_block'] = latest_block

                # Process blocks in batches
                end_block = min(
                    current_block + batch_size,
                    latest_block + 1
                )

                for block_num in range(current_block, end_block):
                    # Get block data
                    block = await web3.eth.get_block(block_num, full_transactions=True)

                    # Process block data
                    await self._process_block(chain_id, block)

                    # Update processed blocks
                    self._processed_blocks[chain_id].add(block_num)

                # Update current block
                state['current_block'] = end_block

                # Sleep if caught up
                if end_block > latest_block:
                    await asyncio.sleep(1)

            except Exception as e:
                self._sync_states[chain_id]['error'] = str(e)
                await asyncio.sleep(5)

    async def _process_block(self, chain_id: str, block: Dict[str, Any]) -> None:
        """Process a block's data.

        Args:
            chain_id: Chain identifier
            block: Block data
        """
        try:
            # Implement block processing logic
            # This could include:
            # - Processing transactions
            # - Updating state
            # - Triggering events
            pass

        except Exception as e:
            self._sync_states[chain_id]['error'] = f"Error processing block {block['number']}: {e}"

    async def _monitor_reorgs(self, chain_id: str) -> None:
        """Monitor for blockchain reorganizations.

        Args:
            chain_id: Chain identifier
        """
        web3 = self._web3_instances[chain_id]
        last_block = None
        last_block_hash = None

        while self._sync_states[chain_id]['running']:
            try:
                # Get latest block
                latest_block = await web3.eth.get_block('latest')
                current_hash = latest_block['hash'].hex()

                if last_block and last_block_hash:
                    if latest_block['number'] == last_block['number']:
                        if current_hash != last_block_hash:
                            # Reorg detected
                            await self._handle_reorg(
                                chain_id,
                                latest_block['number']
                            )
                    elif latest_block['number'] < last_block['number']:
                        # Potential deep reorg
                        await self._handle_reorg(
                            chain_id,
                            latest_block['number']
                        )

                last_block = latest_block
                last_block_hash = current_hash
                await asyncio.sleep(1)

            except Exception as e:
                self._sync_states[chain_id]['error'] = f"Error in reorg monitor: {e}"
                await asyncio.sleep(5)

    async def _handle_reorg(
        self,
        chain_id: str,
        block_number: int
    ) -> None:
        """Handle blockchain reorganization.

        Args:
            chain_id: Chain identifier
            block_number: Block number where reorg was detected
        """
        try:
            # Mark reorg detected
            self._sync_states[chain_id]['reorg_detected'] = True

            # Remove processed blocks after reorg point
            self._processed_blocks[chain_id] = {
                block for block in self._processed_blocks[chain_id]
                if block < block_number
            }

            # Reset current block to reorg point
            self._sync_states[chain_id]['current_block'] = block_number

        except Exception as e:
            self._sync_states[chain_id]['error'] = f"Error handling reorg: {e}"
