"""
Tests for smart contract security.
"""
import pytest
from web3 import Web3

async def test_contract_verification(contract_security, test_contract):
    """Test contract security verification."""
    checks = await contract_security.verify_contract(
        test_contract["address"],
        test_contract["source_code"],
        test_contract["bytecode"]
    )
    assert len(checks) > 0
    assert any(check.name == "access_control" for check in checks)

async def test_reentrancy_check(contract_security):
    """Test reentrancy vulnerability check."""
    vulnerable_code = """
    function withdraw() public {
        uint amount = balances[msg.sender];
        (bool success, ) = msg.sender.call{value: amount}("");
        balances[msg.sender] = 0;
    }
    """
    checks = await contract_security.verify_contract(
        "0x0000000000000000000000000000000000000000",
        vulnerable_code,
        "0x00"
    )
    assert any(
        check.name == "reentrancy_protection" and not check.passed
        for check in checks
    )

async def test_overflow_check(contract_security):
    """Test overflow protection check."""
    safe_code = """
    pragma solidity ^0.8.0;
    contract Test {
        uint256 public value;
        function add(uint256 a) public {
            value += a;
        }
    }
    """
    checks = await contract_security.verify_contract(
        "0x0000000000000000000000000000000000000000",
        safe_code,
        "0x00"
    )
    assert any(
        check.name == "overflow_protection" and check.passed
        for check in checks
    )

async def test_access_control_check(contract_security):
    """Test access control check."""
    protected_code = """
    pragma solidity ^0.8.0;
    import "@openzeppelin/contracts/access/Ownable.sol";
    contract Test is Ownable {
        function sensitiveOperation() public onlyOwner {
        }
    }
    """
    checks = await contract_security.verify_contract(
        "0x0000000000000000000000000000000000000000",
        protected_code,
        "0x00"
    )
    assert any(
        check.name == "access_control" and check.passed
        for check in checks
    )
