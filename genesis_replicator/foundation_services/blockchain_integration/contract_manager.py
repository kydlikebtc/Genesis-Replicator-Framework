"""
Contract Manager for blockchain integration.

This module manages smart contract interactions, deployment, and monitoring.
"""
import asyncio
import json
from typing import Dict, List, Optional, Any
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception, ContractLogicError

from ...foundation_services.exceptions import (
    BlockchainError,
    ChainConnectionError,
    ContractError,
    TransactionError
)


class ContractManager:
    """Manages smart contract operations and monitoring."""

    def __init__(self):
        """Initialize the contract manager."""
        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._abis: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def deploy_contract(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        contract_name: str,
        abi: Dict[str, Any],
        bytecode: str,
        constructor_args: Optional[List[Any]] = None,
        **deploy_args
    ) -> str:
        """Deploy a smart contract.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            contract_name: Name of the contract
            abi: Contract ABI
            bytecode: Contract bytecode
            constructor_args: Constructor arguments
            **deploy_args: Additional deployment arguments

        Returns:
            Deployed contract address

        Raises:
            ContractError: If deployment fails
        """
        try:
            async with self._lock:
                contract = web3.eth.contract(abi=abi, bytecode=bytecode)

                # Prepare constructor arguments
                if constructor_args is None:
                    constructor_args = []

                # Build constructor transaction
                construct_txn = await contract.constructor(*constructor_args).build_transaction(
                    {
                        'from': deploy_args.get('from_address'),
                        'gas': deploy_args.get('gas', 2000000),
                        **deploy_args
                    }
                )

                # Send deployment transaction
                tx_hash = await web3.eth.send_transaction(construct_txn)
                tx_receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)

                if tx_receipt['status'] != 1:
                    raise ContractError(
                        f"Contract deployment failed for {contract_name}",
                        details={
                            "chain_id": chain_id,
                            "transaction_hash": tx_hash.hex(),
                            "status": tx_receipt['status']
                        }
                    )

                contract_address = tx_receipt['contractAddress']

                # Store contract information
                self._contracts[contract_address] = {
                    'name': contract_name,
                    'chain_id': chain_id,
                    'abi': abi,
                    'address': contract_address
                }
                self._abis[contract_name] = abi

                return contract_address

        except Web3Exception as e:
            raise ContractError(
                f"Web3 error during contract deployment: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_name": contract_name,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error during contract deployment: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_name": contract_name,
                    "error": str(e)
                }
            )

    async def load_contract(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        contract_name: str,
        contract_address: str,
        abi: Dict[str, Any]
    ) -> None:
        """Load an existing contract.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            contract_name: Name of the contract
            contract_address: Address of the deployed contract
            abi: Contract ABI

        Raises:
            ContractError: If contract loading fails
        """
        try:
            async with self._lock:
                # Verify contract exists on chain
                code = await web3.eth.get_code(contract_address)
                if code == b'0x' or code == b'':
                    raise ContractError(
                        f"No contract found at address {contract_address}",
                        details={
                            "chain_id": chain_id,
                            "contract_address": contract_address
                        }
                    )

                # Store contract information
                self._contracts[contract_address] = {
                    'name': contract_name,
                    'chain_id': chain_id,
                    'abi': abi,
                    'address': contract_address
                }
                self._abis[contract_name] = abi

        except Web3Exception as e:
            raise ContractError(
                f"Web3 error loading contract: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error loading contract: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "error": str(e)
                }
            )

    async def call_contract_method(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        contract_address: str,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Call a contract method.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            contract_address: Contract address
            method_name: Method to call
            *args: Method arguments
            **kwargs: Additional call arguments

        Returns:
            Method call result

        Raises:
            ContractError: If method call fails
        """
        try:
            if contract_address not in self._contracts:
                raise ContractError(
                    f"Contract not found: {contract_address}",
                    details={
                        "chain_id": chain_id,
                        "contract_address": contract_address
                    }
                )

            contract_data = self._contracts[contract_address]
            contract = web3.eth.contract(
                address=contract_address,
                abi=contract_data['abi']
            )

            # Get contract method
            method = getattr(contract.functions, method_name)
            if method is None:
                raise ContractError(
                    f"Method not found: {method_name}",
                    details={
                        "contract_address": contract_address,
                        "method_name": method_name
                    }
                )

            # Call method
            result = await method(*args).call(**kwargs)
            return result

        except ContractLogicError as e:
            raise ContractError(
                f"Contract logic error: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )
        except Web3Exception as e:
            raise ContractError(
                f"Web3 error calling contract method: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error calling contract method: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )

    async def send_transaction(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        contract_address: str,
        method_name: str,
        *args,
        **kwargs
    ) -> str:
        """Send a transaction to a contract method.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            contract_address: Contract address
            method_name: Method to call
            *args: Method arguments
            **kwargs: Additional transaction arguments

        Returns:
            Transaction hash

        Raises:
            ContractError: If transaction fails
        """
        try:
            if contract_address not in self._contracts:
                raise ContractError(
                    f"Contract not found: {contract_address}",
                    details={
                        "chain_id": chain_id,
                        "contract_address": contract_address
                    }
                )

            contract_data = self._contracts[contract_address]
            contract = web3.eth.contract(
                address=contract_address,
                abi=contract_data['abi']
            )

            # Get contract method
            method = getattr(contract.functions, method_name)
            if method is None:
                raise ContractError(
                    f"Method not found: {method_name}",
                    details={
                        "contract_address": contract_address,
                        "method_name": method_name
                    }
                )

            # Build transaction
            transaction = await method(*args).build_transaction(kwargs)

            # Send transaction
            tx_hash = await web3.eth.send_transaction(transaction)
            return tx_hash.hex()

        except ContractLogicError as e:
            raise ContractError(
                f"Contract logic error in transaction: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )
        except Web3Exception as e:
            raise ContractError(
                f"Web3 error in transaction: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error in transaction: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )

    async def monitor_events(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        contract_address: str,
        event_name: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        argument_filters: Optional[Dict[str, Any]] = None
    ) -> asyncio.Task:
        """Monitor contract events.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            contract_address: Contract address
            event_name: Event to monitor
            from_block: Start block (default: latest)
            to_block: End block (default: latest)
            argument_filters: Event argument filters

        Returns:
            Monitoring task

        Raises:
            ContractError: If monitoring setup fails
        """
        try:
            if contract_address not in self._contracts:
                raise ContractError(
                    f"Contract not found: {contract_address}",
                    details={
                        "chain_id": chain_id,
                        "contract_address": contract_address
                    }
                )

            contract_data = self._contracts[contract_address]
            contract = web3.eth.contract(
                address=contract_address,
                abi=contract_data['abi']
            )

            # Get event
            event = getattr(contract.events, event_name)
            if event is None:
                raise ContractError(
                    f"Event not found: {event_name}",
                    details={
                        "contract_address": contract_address,
                        "event_name": event_name
                    }
                )

            # Create event filter
            event_filter = await event.create_filter(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters=argument_filters
            )


            # Start monitoring task
            async def monitor():
                while True:
                    try:
                        events = await event_filter.get_new_entries()
                        for event in events:
                            # Process event (implement event handling logic)
                            print(f"New event: {event}")
                        await asyncio.sleep(2)  # Poll interval
                    except Exception as e:
                        print(f"Error polling events: {e}")
                        await asyncio.sleep(5)  # Longer interval on error

            task = asyncio.create_task(monitor())
            return task

        except Web3Exception as e:
            raise ContractError(
                f"Web3 error setting up event monitor: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "event_name": event_name,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error setting up event monitor: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "event_name": event_name,
                    "error": str(e)
                }
            )

    async def get_contract_events(
        self,
        chain_id: str,
        web3: AsyncWeb3,
        contract_address: str,
        event_name: str,
        from_block: int,
        to_block: Optional[int] = None,
        argument_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get past contract events.

        Args:
            chain_id: Chain identifier
            web3: Web3 instance for the chain
            contract_address: Contract address
            event_name: Event to fetch
            from_block: Start block
            to_block: End block (default: latest)
            argument_filters: Event argument filters

        Returns:
            List of events

        Raises:
            ContractError: If event fetching fails
        """
        try:
            if contract_address not in self._contracts:
                raise ContractError(
                    f"Contract not found: {contract_address}",
                    details={
                        "chain_id": chain_id,
                        "contract_address": contract_address
                    }
                )

            contract_data = self._contracts[contract_address]
            contract = web3.eth.contract(
                address=contract_address,
                abi=contract_data['abi']
            )

            # Get event
            event = getattr(contract.events, event_name)
            if event is None:
                raise ContractError(
                    f"Event not found: {event_name}",
                    details={
                        "contract_address": contract_address,
                        "event_name": event_name
                    }
                )

            # Get past events
            events = await event.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters=argument_filters
            )

            return [dict(evt) for evt in events]

        except Web3Exception as e:
            raise ContractError(
                f"Web3 error fetching events: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "event_name": event_name,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error fetching events: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "event_name": event_name,
                    "error": str(e)
                }
            )
