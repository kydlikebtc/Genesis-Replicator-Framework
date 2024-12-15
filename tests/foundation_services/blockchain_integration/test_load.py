"""
Load testing for blockchain integration components.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from web3 import AsyncWeb3

from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager
from genesis_replicator.foundation_services.blockchain_integration.transaction_manager import TransactionManager
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager


@pytest.fixture
async def managers():
    """Create manager instances for testing."""
    sync_manager = SyncManager()
    tx_manager = TransactionManager()
    chain_manager = ChainManager()
    contract_manager = ContractManager()

    # Initialize all managers
    await sync_manager.start()
    await tx_manager.start()
    await chain_manager.start()
    await contract_manager.start()

    # Return managers with cleanup
    try:
        yield {
            'sync': sync_manager,
            'tx': tx_manager,
            'chain': chain_manager,
            'contract': contract_manager
        }
    finally:
        # Cleanup all managers
        await asyncio.gather(
            sync_manager.stop(),
            tx_manager.stop(),
            chain_manager.stop(),
            contract_manager.stop()
        )


@pytest.mark.asyncio
async def test_concurrent_chain_sync(managers):
    """Test synchronizing multiple chains concurrently."""
    sync_manager = managers['sync']

    # Setup multiple mock Web3 instances
    chains = {}
    for i in range(3):
        chain_id = f'chain{i}'
        web3 = AsyncMock()
        web3.__class__ = AsyncWeb3
        web3.eth = AsyncMock()
        web3.eth.block_number = AsyncMock(return_value=1000)
        web3.eth.get_block = AsyncMock(return_value={
            'number': 900,
            'hash': f'0x{chain_id}',
            'transactions': []
        })
        web3.is_connected = AsyncMock(return_value=True)
        chains[chain_id] = web3

    # Configure chains
    config = {
        chain_id: {
            'rpc_url': f'http://localhost:{8545+i}',
            'chain_id': i
        }
        for i, chain_id in enumerate(chains)
    }
    await sync_manager.configure(config)

    try:
        # Start sync on multiple chains
        sync_tasks = []
        for chain_id in chains:
            sync_tasks.append(sync_manager.start_sync(chain_id))
        await asyncio.gather(*sync_tasks)
        await asyncio.sleep(0.1)  # Allow sync to process

        # Verify all chains are syncing
        for chain_id in chains:
            status = await sync_manager.get_sync_status(chain_id)
            assert status['is_syncing']
            assert status['current_block'] >= 900
    finally:
        # Cleanup
        stop_tasks = []
        for chain_id in chains:
            stop_tasks.append(sync_manager.stop_sync(chain_id))
        await asyncio.gather(*stop_tasks)


@pytest.mark.asyncio
async def test_transaction_batch_load(managers):
    """Test processing large transaction batches."""
    tx_manager = managers['tx']
    web3 = AsyncMock()
    web3.__class__ = AsyncWeb3
    web3.eth = AsyncMock()
    web3.eth.get_transaction_count = AsyncMock(return_value=1)
    web3.eth.send_transaction = AsyncMock()
    web3.eth.wait_for_transaction_receipt = AsyncMock()

    # Create large batch of transactions
    chain_id = "test_chain"
    batch_id = "test_batch"
    transactions = [
        {'from': f'0x{i}', 'to': f'0x{i+1}', 'value': 1000}
        for i in range(100)  # Test with 100 transactions
    ]

    # Process batch in parallel
    await tx_manager.create_transaction_batch(batch_id, chain_id, transactions)
    results = await tx_manager.submit_transaction_batch(
        chain_id, web3, batch_id, parallel=True
    )

    assert len(results) == 100


@pytest.mark.asyncio
async def test_contract_deployment_load(managers):
    """Test deploying multiple contracts concurrently."""
    contract_manager = managers['contract']
    chain_manager = managers['chain']

    # Setup mock Web3
    web3 = AsyncMock()
    web3.__class__ = AsyncWeb3
    web3.eth = AsyncMock()
    web3.eth.chain_id = AsyncMock(return_value=1)
    web3.eth.get_code = AsyncMock(return_value='0x123456')
    web3.eth.get_transaction_receipt = AsyncMock(return_value={'status': 1})
    web3.is_connected = AsyncMock(return_value=True)
    web3.eth.contract = AsyncMock()
    web3.eth.send_transaction = AsyncMock(return_value='0xtxhash')
    web3.eth.wait_for_transaction_receipt = AsyncMock(return_value={'contractAddress': '0xcontract'})

    # Configure chain
    chain_id = "test_chain"
    await chain_manager.configure({
        chain_id: {
            'rpc_url': 'http://localhost:8545',
            'chain_id': 1
        }
    })

    try:
        # Deploy multiple contracts concurrently
        tasks = []
        contract_abi = [{"type": "constructor", "inputs": []}]
        contract_bytecode = "0x123456"
        for i in range(50):
            tasks.append(
                contract_manager.deploy_contract(
                    f"contract_{i}",
                    contract_abi,
                    contract_bytecode,
                    chain_id
                )
            )

        results = await asyncio.gather(*tasks)
        assert len(results) == 50
        assert all(isinstance(addr, str) for addr in results)
    finally:
        # Cleanup registered contracts
        for i in range(50):
            await contract_manager.unregister_contract(f"contract_{i}")


@pytest.mark.asyncio
async def test_chain_manager_load(managers):
    """Test chain manager under load conditions."""
    chain_manager = managers['chain']

    # Configure multiple chains
    chains = {
        f"chain_{i}": {
            "rpc_url": f"http://localhost:{8545+i}",
            "chain_id": i,
            "sync_interval": 15
        }
        for i in range(10)  # Test with 10 chains
    }

    # Configure all chains
    await chain_manager.configure(chains)
    configured_chains = chain_manager.get_supported_chains()

    assert len(configured_chains) == 10
    assert all(f"chain_{i}" in configured_chains for i in range(10))


@pytest.mark.asyncio
async def test_system_recovery(managers):
    """Test system recovery under load conditions."""
    sync_manager = managers['sync']
    chain_manager = managers['chain']

    # Simulate system crash during multi-chain sync
    chains = {
        'chain1': AsyncMock(),
        'chain2': AsyncMock()
    }

    try:
        for chain_id, web3 in chains.items():
            web3.__class__ = AsyncWeb3
            web3.eth = AsyncMock()
            web3.eth.block_number = AsyncMock(return_value=1000)
            web3.eth.get_block = AsyncMock()
            web3.is_connected = AsyncMock(return_value=True)
            await sync_manager.start_sync(chain_id, web3, 900)

        # Simulate crash
        for chain_id in chains:
            sync_manager._sync_states[chain_id]['running'] = False
            await asyncio.sleep(0.1)  # Allow state change to propagate

        # Recover system
        recovery_tasks = []
        for chain_id, web3 in chains.items():
            recovery_tasks.append(sync_manager.start_sync(chain_id, web3, 900))
        await asyncio.gather(*recovery_tasks)

        # Verify recovery
        for chain_id in chains:
            status = await sync_manager.get_sync_status(chain_id)
            assert status['is_running']
    finally:
        # Cleanup
        stop_tasks = []
        for chain_id in chains:
            stop_tasks.append(sync_manager.stop_sync(chain_id))
        await asyncio.gather(*stop_tasks)
