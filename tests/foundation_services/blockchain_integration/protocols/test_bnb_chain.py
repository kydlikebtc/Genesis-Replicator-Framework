"""
Tests for BNB Chain protocol adapter.
"""
import pytest
from web3 import Web3
from web3.types import Wei

from genesis_replicator.foundation_services.blockchain_integration.protocols.bnb_chain import (
    BNBChainAdapter,
)

@pytest.fixture
async def bnb_adapter():
    adapter = BNBChainAdapter()
    await adapter.configure_web3("https://bsc-dataseed.binance.org/")
    return adapter

@pytest.mark.asyncio
async def test_chain_configuration():
    adapter = BNBChainAdapter()
    assert adapter.chain_id == 56
    assert adapter.native_currency == "BNB"
    assert adapter.block_time == 3

@pytest.mark.asyncio
async def test_web3_configuration(bnb_adapter):
    assert isinstance(bnb_adapter.web3, Web3)
    assert bnb_adapter.web3.is_connected()
    chain_id = await bnb_adapter.web3.eth.chain_id
    assert chain_id == 56

@pytest.mark.asyncio
async def test_validate_address(bnb_adapter):
    valid_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    invalid_address = "0xinvalid"

    assert await bnb_adapter.validate_address(valid_address)
    assert not await bnb_adapter.validate_address(invalid_address)

@pytest.mark.asyncio
async def test_get_gas_price(bnb_adapter):
    gas_price = await bnb_adapter.get_gas_price()
    assert isinstance(gas_price, Wei)
    assert gas_price > 0

@pytest.mark.asyncio
async def test_get_block(bnb_adapter):
    block = await bnb_adapter.get_block('latest')
    assert isinstance(block, dict)
    assert 'number' in block
    assert 'hash' in block
    assert 'timestamp' in block

@pytest.mark.asyncio
async def test_estimate_gas(bnb_adapter):
    tx_params = {
        'from': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'value': Wei(100000),
    }
    gas = await bnb_adapter.estimate_gas(tx_params)
    assert isinstance(gas, Wei)
    assert gas > 0

@pytest.mark.asyncio
async def test_send_transaction_validation(bnb_adapter):
    tx_params = {
        'gas': 31_000_000,  # Exceeds max gas limit
        'to': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        'value': Wei(100000),
    }
    with pytest.raises(ValueError, match="Gas limit exceeds maximum allowed"):
        await bnb_adapter.send_transaction(tx_params)

@pytest.mark.asyncio
async def test_get_balance_validation(bnb_adapter):
    invalid_address = "0xinvalid"
    with pytest.raises(ValueError, match="Invalid address"):
        await bnb_adapter.get_balance(invalid_address)
