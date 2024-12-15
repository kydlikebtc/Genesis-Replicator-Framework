"""
Smart contract security manager for Genesis Replicator Framework.
"""
import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from web3 import Web3
from eth_typing import ChecksumAddress

@dataclass
class SecurityCheck:
    """Security check result."""
    name: str
    passed: bool
    details: str

class ContractSecurityManager:
    """Manages smart contract security."""

    def __init__(self, web3: Web3):
        """Initialize contract security manager.

        Args:
            web3: Web3 instance
        """
        self._web3 = web3
        self._verified_contracts: Set[ChecksumAddress] = set()
        self._lock = asyncio.Lock()

    async def verify_contract(
        self,
        address: ChecksumAddress,
        source_code: str,
        bytecode: str
    ) -> List[SecurityCheck]:
        """Verify smart contract security.

        Args:
            address: Contract address
            source_code: Contract source code
            bytecode: Contract bytecode

        Returns:
            List[SecurityCheck]: Security check results
        """
        checks = []

        # Verify bytecode matches deployed code
        deployed_code = await self._get_deployed_bytecode(address)
        if deployed_code != bytecode:
            checks.append(SecurityCheck(
                name="bytecode_verification",
                passed=False,
                details="Bytecode mismatch"
            ))
            return checks

        # Check for common vulnerabilities
        checks.extend(await self._check_reentrancy(source_code))
        checks.extend(await self._check_overflow(source_code))
        checks.extend(await self._check_access_control(source_code))

        if all(check.passed for check in checks):
            async with self._lock:
                self._verified_contracts.add(address)

        return checks

    async def is_verified(self, address: ChecksumAddress) -> bool:
        """Check if contract is verified.

        Args:
            address: Contract address

        Returns:
            bool: True if verified
        """
        return address in self._verified_contracts

    async def _get_deployed_bytecode(
        self,
        address: ChecksumAddress
    ) -> str:
        """Get deployed contract bytecode.

        Args:
            address: Contract address

        Returns:
            str: Deployed bytecode
        """
        return self._web3.eth.get_code(address).hex()

    async def _check_reentrancy(self, source_code: str) -> List[SecurityCheck]:
        """Check for reentrancy vulnerabilities.

        Args:
            source_code: Contract source code

        Returns:
            List[SecurityCheck]: Check results
        """
        checks = []

        # Check for proper state updates before external calls
        if "call.value" in source_code and not "nonReentrant" in source_code:
            checks.append(SecurityCheck(
                name="reentrancy_protection",
                passed=False,
                details="Missing reentrancy guard"
            ))
        else:
            checks.append(SecurityCheck(
                name="reentrancy_protection",
                passed=True,
                details="Reentrancy protection found"
            ))

        return checks

    async def _check_overflow(self, source_code: str) -> List[SecurityCheck]:
        """Check for arithmetic overflow vulnerabilities.

        Args:
            source_code: Contract source code

        Returns:
            List[SecurityCheck]: Check results
        """
        checks = []

        # Check for SafeMath usage
        if "using SafeMath" in source_code or "pragma solidity ^0.8" in source_code:
            checks.append(SecurityCheck(
                name="overflow_protection",
                passed=True,
                details="Overflow protection found"
            ))
        else:
            checks.append(SecurityCheck(
                name="overflow_protection",
                passed=False,
                details="Missing overflow protection"
            ))

        return checks

    async def _check_access_control(self, source_code: str) -> List[SecurityCheck]:
        """Check for proper access control.

        Args:
            source_code: Contract source code

        Returns:
            List[SecurityCheck]: Check results
        """
        checks = []

        # Check for proper modifiers
        if "onlyOwner" in source_code or "AccessControl" in source_code:
            checks.append(SecurityCheck(
                name="access_control",
                passed=True,
                details="Access control found"
            ))
        else:
            checks.append(SecurityCheck(
                name="access_control",
                passed=False,
                details="Missing access control"
            ))

        return checks
