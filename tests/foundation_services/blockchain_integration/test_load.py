"""
Load testing for blockchain integration components.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

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

    await sync_manager.start()
    await chain_manager.start()

    yield {
        'sync': sync_manager,
        'tx': tx_manager,
        'chain': chain_manager,
        'contract': contract_manager
    }

    await sync_manager.stop()
    await chain_manager.stop()


@pytest.mark.asyncio
async def test_concurrent_chain_sync(managers):
    """Test synchronizing multiple chains concurrently."""
    sync_manager = managers['sync']

    # Setup multiple mock Web3 instances
    chains = {
        'chain1': AsyncMock(spec=AsyncWeb3),
        'chain2': AsyncMock(spec=AsyncWeb3),
        'chain3': AsyncMock(spec=AsyncWeb3)
    }

    for chain_id, web3 in chains.items():
        web3.eth = AsyncMock()
        web3.eth.block_number = AsyncMock(return_value=1000)
        web3.eth.get_block = AsyncMock(return_value={
            'number': 900,
            'hash': f'0x{chain_id}',
            'transactions': []
        })

    # Start sync on multiple chains
    tasks = []
    for chain_id, web3 in chains.items():
        tasks.append(sync_manager.start_sync(chain_id, web3, 900))

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.1)  # Allow sync to process

    # Verify all chains are syncing
    for chain_id in chains:
        status = await sync_manager.get_sync_status(chain_id)
        assert status['is_running']
        assert status['current_block'] == 900
        await sync_manager.stop_sync(chain_id)


@pytest.mark.asyncio
async def test_transaction_batch_load(managers):
    """Test processing large transaction batches."""
    tx_manager = managers['tx']
    web3 = AsyncMock(spec=AsyncWeb3)
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
    web3 = AsyncMock(spec=AsyncWeb3)
    web3.eth = AsyncMock()
    web3.eth.contract = AsyncMock()
    web3.eth.get_contract_code = AsyncMock()

    # Deploy multiple contracts concurrently
    chain_id = "test_chain"
    abi = [{"type": "function", "name": "test"}]
    bytecode = "0x123456"

    async def deploy_contract(i):
        address = f"0x{i}"
        mock_contract = AsyncMock()
        mock_contract.address = address
        web3.eth.contract.return_value.constructor.return_value.transact.return_value = address
        return await contract_manager.deploy_contract(
            chain_id, web3, abi, bytecode, []
        )

    # Deploy 50 contracts concurrently
    tasks = [deploy_contract(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    assert all(isinstance(addr, str) for addr in results)




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
        'chain1': AsyncMock(spec=AsyncWeb3),
        'chain2': AsyncMock(spec=AsyncWeb3)
    }

    for chain_id, web3 in chains.items():
        web3.eth = AsyncMock()
        web3.eth.block_number = AsyncMock(return_value=1000)
        web3.eth.get_block = AsyncMock()
        await sync_manager.start_sync(chain_id, web3, 900)

    # Simulate crash
    for chain_id in chains:
        sync_manager._sync_states[chain_id]['running'] = False

    # Recover system
    for chain_id, web3 in chains.items():
        await sync_manager.start_sync(chain_id, web3, 900)
        status = await sync_manager.get_sync_status(chain_id)
        assert status['is_running']
        await sync_manager.stop_sync(chain_id)
