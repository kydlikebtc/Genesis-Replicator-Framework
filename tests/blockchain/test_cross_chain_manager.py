"""
Tests for cross-chain transaction manager.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from genesis_replicator.blockchain.cross_chain_manager import (
    CrossChainManager,
    CrossChainTransaction
)

@pytest.fixture
def chain_manager():
    manager = Mock()
    manager.is_chain_supported = AsyncMock(return_value=True)
    manager.get_transaction_confirmations = AsyncMock(return_value=12)
    return manager

@pytest.fixture
def transaction_manager():
    manager = Mock()
    manager.submit_transaction = AsyncMock(return_value={"hash": "0x123"})
    manager.prepare_transaction = AsyncMock(return_value={"data": "prepared"})
    return manager

@pytest.fixture
def contract_security():
    security = Mock()
    security.validate_transaction = AsyncMock()
    return security

@pytest.fixture
def cross_chain_manager(chain_manager, transaction_manager, contract_security):
    return CrossChainManager(
        chain_manager,
        transaction_manager,
        contract_security
    )

@pytest.mark.asyncio
async def test_initiate_cross_chain_transaction(cross_chain_manager):
    source_tx = {"method": "transfer", "params": {"to": "0x456", "amount": 100}}
    target_tx = {"method": "mint", "params": {"to": "0x789", "amount": 100}}

    tx_id = await cross_chain_manager.initiate_cross_chain_transaction(
        "ethereum",
        "bnb",
        source_tx,
        target_tx
    )

    assert tx_id is not None
    status = await cross_chain_manager.get_transaction_status(tx_id)
    assert status["status"] == "pending"
    assert status["source_chain"] == "ethereum"
    assert status["target_chain"] == "bnb"

@pytest.mark.asyncio
async def test_execute_transaction(cross_chain_manager):
    # Initialize transaction
    tx_id = await cross_chain_manager.initiate_cross_chain_transaction(
        "ethereum",
        "bnb",
        {"method": "transfer"},
        {"method": "mint"}
    )

    # Execute transaction
    await cross_chain_manager.execute_transaction(tx_id)

    # Verify status
    status = await cross_chain_manager.get_transaction_status(tx_id)
    assert status["status"] == "completed"

@pytest.mark.asyncio
async def test_transaction_with_dependencies(cross_chain_manager):
    # Create first transaction
    tx1_id = await cross_chain_manager.initiate_cross_chain_transaction(
        "ethereum",
        "bnb",
        {"method": "transfer"},
        {"method": "mint"}
    )

    # Create dependent transaction
    tx2_id = await cross_chain_manager.initiate_cross_chain_transaction(
        "ethereum",
        "bnb",
        {"method": "transfer"},
        {"method": "mint"},
        dependencies={tx1_id}
    )

    # Execute first transaction
    await cross_chain_manager.execute_transaction(tx1_id)

    # Execute dependent transaction
    await cross_chain_manager.execute_transaction(tx2_id)

    # Verify both completed
    status1 = await cross_chain_manager.get_transaction_status(tx1_id)
    status2 = await cross_chain_manager.get_transaction_status(tx2_id)
    assert status1["status"] == "completed"
    assert status2["status"] == "completed"

@pytest.mark.asyncio
async def test_invalid_chain(cross_chain_manager, chain_manager):
    chain_manager.is_chain_supported.return_value = False

    with pytest.raises(ValueError):
        await cross_chain_manager.initiate_cross_chain_transaction(
            "invalid",
            "bnb",
            {},
            {}
        )

@pytest.mark.asyncio
async def test_transaction_failure(cross_chain_manager, transaction_manager):
    transaction_manager.submit_transaction.side_effect = RuntimeError("Transaction failed")

    tx_id = await cross_chain_manager.initiate_cross_chain_transaction(
        "ethereum",
        "bnb",
        {},
        {}
    )

    with pytest.raises(RuntimeError):
        await cross_chain_manager.execute_transaction(tx_id)

    status = await cross_chain_manager.get_transaction_status(tx_id)
    assert status["status"] == "failed"
