"""
Security tests for blockchain integration components.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from genesis_replicator.foundation_services.blockchain_integration.sync_manager import SyncManager
from genesis_replicator.foundation_services.blockchain_integration.transaction_manager import TransactionManager
from genesis_replicator.foundation_services.blockchain_integration.chain_manager import ChainManager
from genesis_replicator.foundation_services.blockchain_integration.contract_manager import ContractManager
from genesis_replicator.foundation_services.exceptions import SecurityError


@pytest.fixture
async def web3_mock():
    """Create a Web3 mock with proper eth attribute setup."""
    mock = AsyncMock(spec=AsyncWeb3)
    eth_mock = AsyncMock()

    # Setup eth mock methods
    eth_mock.get_transaction_count = AsyncMock(return_value=0)
    eth_mock.send_transaction = AsyncMock(return_value=bytes.fromhex('123'))
    eth_mock.wait_for_transaction_receipt = AsyncMock(return_value={'status': 1})
    eth_mock.get_block = AsyncMock(return_value={'timestamp': 1234567890})
    eth_mock.chain_id = AsyncMock(return_value=1)
    eth_mock.block_number = AsyncMock(return_value=1000)
    eth_mock.get_code = AsyncMock(return_value=bytes.fromhex('123456'))
    eth_mock.contract = AsyncMock()

    # Setup contract mock
    contract_mock = AsyncMock()
    contract_mock.constructor = AsyncMock()
    contract_mock.constructor.return_value.build_transaction = AsyncMock(
        return_value={'data': '0x123456'}
    )
    eth_mock.contract.return_value = contract_mock

    mock.eth = eth_mock
    return mock

@pytest.fixture
async def managers(web3_mock):
    """Create manager instances for testing."""
    sync_manager = SyncManager()
    tx_manager = TransactionManager()
    chain_manager = ChainManager()
    contract_manager = ContractManager()

    await sync_manager.start()
    await chain_manager.start()
    await tx_manager.start()
    await contract_manager.start()

    yield {
        'sync': sync_manager,
        'tx': tx_manager,
        'chain': chain_manager,
        'contract': contract_manager,
        'web3': web3_mock
    }

    await sync_manager.stop()
    await chain_manager.stop()
    await tx_manager.stop()
    await contract_manager.stop()


@pytest.mark.asyncio
async def test_invalid_chain_access(managers):
    """Test protection against unauthorized chain access."""
    chain_manager = managers['chain']

    # Test access to unauthorized chain
    with pytest.raises(SecurityError) as exc_info:
        await chain_manager.connect_chain("unauthorized_chain")
    assert "Unauthorized chain access" in str(exc_info.value)


@pytest.mark.asyncio
async def test_transaction_validation(managers):
    """Test transaction security validation."""
    tx_manager = managers['tx']
    web3 = managers['web3']

    # Test transaction with invalid signature
    invalid_tx = {
        'from': '0x123',
        'to': '0x456',
        'value': 1000,
        'signature': 'invalid'
    }

    with pytest.raises(SecurityError) as exc_info:
        await tx_manager.submit_transaction("test_chain", web3, invalid_tx)
    assert "Invalid transaction signature" in str(exc_info.value)


@pytest.mark.asyncio
async def test_contract_security(managers):
    """Test contract security measures."""
    contract_manager = managers['contract']
    web3 = managers['web3']

    # Test deployment of malicious contract
    malicious_bytecode = "0x123456"  # Simulated malicious code
    abi = [{"type": "function", "name": "malicious"}]

    with pytest.raises(SecurityError) as exc_info:
        await contract_manager.deploy_contract(
            "test_chain", web3, abi, malicious_bytecode, []
        )
    assert "Potential security risk" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sync_authentication(managers):
    """Test sync process authentication."""
    sync_manager = managers['sync']
    web3 = managers['web3']

    # Test sync with invalid credentials
    with pytest.raises(SecurityError) as exc_info:
        await sync_manager.start_sync(
            "test_chain",
            web3,
            900,
            credentials={'invalid': 'credentials'}
        )
    assert "Invalid sync credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rate_limiting(managers):
    """Test rate limiting protection."""
    tx_manager = managers['tx']
    web3 = managers['web3']

    # Attempt rapid transactions
    tasks = []
    for i in range(100):  # Attempt 100 rapid transactions
        tx = {'from': f'0x{i}', 'to': '0x456', 'value': 1000}
        tasks.append(tx_manager.submit_transaction("test_chain", web3, tx))

    with pytest.raises(SecurityError) as exc_info:
        await asyncio.gather(*tasks)
    assert "Rate limit exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_input_sanitization(managers):
    """Test input sanitization."""
    contract_manager = managers['contract']
    web3 = managers['web3']

    # Test with potentially malicious input
    malicious_input = "'; DROP TABLE contracts; --"

    with pytest.raises(SecurityError) as exc_info:
        await contract_manager.get_contract_state(
            "test_chain",
            malicious_input
        )
    assert "Invalid input" in str(exc_info.value)


@pytest.mark.asyncio
async def test_permission_validation(managers):
    """Test permission validation."""
    chain_manager = managers['chain']

    # Test operation without required permissions
    config = {
        "ethereum": {
            "rpc_url": "http://localhost:8545",
            "permissions": ["admin"]
        }
    }

    await chain_manager.configure(config)

    with pytest.raises(SecurityError) as exc_info:
        await chain_manager.connect_chain(
            "ethereum",
            credentials={'role': 'user'}
        )
    assert "Insufficient permissions" in str(exc_info.value)
