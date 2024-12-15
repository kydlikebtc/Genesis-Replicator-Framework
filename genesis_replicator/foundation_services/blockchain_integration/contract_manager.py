"""
Contract Manager for blockchain integration.

This module manages smart contract interactions, deployment, and monitoring.
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, AsyncGenerator
from web3 import AsyncWeb3, Web3
from web3.exceptions import Web3Exception, ContractLogicError
from web3.types import BlockData

from ...foundation_services.exceptions import (
    BlockchainError,
    ChainConnectionError,
    ContractError,
    SecurityError,
    TransactionError
)


class ContractManager:
    """Manages smart contract operations and monitoring."""

    def __init__(self):
        """Initialize the contract manager."""
        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._abis: Dict[str, Dict[str, Any]] = {}
        self._web3_instances: Dict[str, AsyncWeb3] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._deployment_semaphore = asyncio.Semaphore(5)  # Limit concurrent deployments

    async def start(self) -> None:
        """Initialize and start the contract manager.

        This method should be called before any other operations.

        Raises:
            ContractError: If initialization fails
        """
        if self._initialized:
            return

        try:
            async with self._lock:
                self._initialized = True
                self._contracts.clear()
                self._abis.clear()
                self._web3_instances.clear()
        except Exception as e:
            raise ContractError(
                "Failed to initialize contract manager",
                details={"error": str(e)}
            )

    async def stop(self) -> None:
        """Stop and cleanup the contract manager."""
        async with self._lock:
            self._contracts.clear()
            self._abis.clear()
            self._web3_instances.clear()
            self._initialized = False

    async def get_contract_state(
        self,
        chain_id: str,
        contract_address: str,
        sanitize: bool = True
    ) -> Dict[str, Any]:
        """Get contract state with input sanitization.

        Args:
            chain_id: Chain identifier
            contract_address: Contract address
            sanitize: Whether to sanitize inputs

        Returns:
            Contract state information

        Raises:
            SecurityError: If input validation fails
            ContractError: If contract not found
        """
        if sanitize and not self._validate_input(contract_address):
            raise SecurityError(
                "Invalid input",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address
                }
            )

        if contract_address not in self._contracts:
            raise ContractError(
                f"Contract not found: {contract_address}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address
                }
            )

        contract_data = self._contracts[contract_address]
        return {
            'address': contract_address,
            'name': contract_data['name'],
            'chain_id': contract_data['chain_id']
        }

    def _validate_input(self, input_str: str) -> bool:
        """Validate and sanitize input strings.

        Args:
            input_str: Input string to validate

        Returns:
            True if input is valid, False otherwise
        """
        import re
        return bool(re.match(r'^[0-9a-fA-F]{40}$', input_str.replace('0x', '')))

    async def deploy_contract(
        self,
        contract_id: str,
        contract_name: str,
        credentials: Optional[Dict[str, Any]] = None,
        chain_id: str = "default",
        **kwargs
    ) -> str:
        """Deploy a new contract.

        Args:
            contract_id: Unique identifier for the contract
            contract_name: Name of the contract to deploy
            credentials: Optional security credentials
            chain_id: Chain identifier
            **kwargs: Additional deployment parameters

        Returns:
            Deployed contract address

        Raises:
            ContractError: If deployment fails
            SecurityError: If authentication fails
        """
        if not self._initialized:
            raise ContractError("Contract manager not initialized")

        try:
            async with self._deployment_semaphore:
                async with self._lock:
                    if contract_id in self._contracts:
                        raise ContractError(
                            f"Contract {contract_id} already exists",
                            details={"contract_id": contract_id}
                        )

                    if chain_id not in self._web3_instances:
                        raise ChainConnectionError(
                            f"Chain {chain_id} not connected",
                            details={"chain_id": chain_id}
                        )

                    # Validate credentials
                    if not credentials or 'role' not in credentials or credentials['role'] != 'admin':
                        raise SecurityError(
                            "Invalid deployment credentials",
                            details={
                                "contract_id": contract_id,
                                "chain_id": chain_id
                            }
                        )

                    web3 = self._web3_instances[chain_id]

                    # Deploy contract (mock implementation for testing)
                    contract_address = f"0x{contract_id}{'0' * 40}"

                    self._contracts[contract_id] = {
                        'address': contract_address,
                        'name': contract_name,
                        'chain_id': chain_id,
                        'deployed_at': await web3.eth.block_number,
                        'owner': kwargs.get('from_address', '0x0')
                    }

                    return contract_address

        except (Web3Exception, ContractLogicError) as e:
            raise ContractError(
                f"Contract deployment failed: {str(e)}",
                details={
                    "contract_id": contract_id,
                    "contract_name": contract_name,
                    "chain_id": chain_id,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                "Unexpected error during contract deployment",
                details={
                    "contract_id": contract_id,
                    "contract_name": contract_name,
                    "chain_id": chain_id,
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
        contract_address: str,
        method_name: str,
        args: Optional[List[Any]] = None,
        gas_limit: Optional[int] = None,
        gas_price: Optional[int] = None,
        value: int = 0,
        nonce: Optional[int] = None,
        **kwargs
    ) -> str:
        """Send a contract transaction with gas estimation.

        Args:
            chain_id: Chain identifier
            contract_address: Contract address
            method_name: Method to call
            args: Method arguments
            gas_limit: Optional gas limit override
            gas_price: Optional gas price override
            value: Amount of native currency to send
            nonce: Optional nonce override
            **kwargs: Additional transaction parameters

        Returns:
            Transaction hash

        Raises:
            ContractError: If transaction fails
            SecurityError: If security validation fails
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

            web3 = self._web3_instances[chain_id]
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
            args = args or []
            tx_params = {
                'from': kwargs.get('from_address'),
                'value': value
            }

            # Estimate gas if not provided
            if gas_limit is None:
                gas_limit = await method(*args).estimate_gas(tx_params)
                # Add 10% buffer for BNB Chain
                if chain_id == 'bnb':
                    gas_limit = int(gas_limit * 1.1)

            tx_params['gas'] = gas_limit

            # Get gas price if not provided
            if gas_price is None:
                gas_price = await web3.eth.gas_price
                # Add 5% buffer for BNB Chain
                if chain_id == 'bnb':
                    gas_price = int(gas_price * 1.05)

            tx_params['gasPrice'] = gas_price

            # Get nonce if not provided
            if nonce is None and 'from_address' in kwargs:
                nonce = await web3.eth.get_transaction_count(
                    kwargs['from_address'], 'pending'
                )
                tx_params['nonce'] = nonce

            # Build and send transaction
            tx = await method(*args).build_transaction(tx_params)
            signed_tx = web3.eth.account.sign_transaction(
                tx, private_key=kwargs.get('private_key')
            )
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash.hex()

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
                f"Web3 error sending transaction: {str(e)}",
                details={
                    "chain_id": chain_id,
                    "contract_address": contract_address,
                    "method_name": method_name,
                    "error": str(e)
                }
            )
        except Exception as e:
            raise ContractError(
                f"Unexpected error sending transaction: {str(e)}",
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
        contract_address: str,
        event_name: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        batch_size: int = 1000,
        filters: Optional[Dict[str, Any]] = None,
        retry_interval: int = 5,
        max_retries: int = 3
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Monitor contract events with batching and error handling.

        Args:
            chain_id: Chain identifier
            contract_address: Contract address to monitor
            event_name: Event name to monitor
            from_block: Starting block number (default: latest - 1000)
            to_block: Ending block number (default: latest)
            batch_size: Number of blocks to process in each batch
            filters: Event filter parameters
            retry_interval: Seconds between retry attempts
            max_retries: Maximum number of retry attempts

        Yields:
            Event data dictionaries

        Raises:
            ContractError: If event monitoring fails
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

            web3 = self._web3_instances[chain_id]
            contract_data = self._contracts[contract_address]
            contract = web3.eth.contract(
                address=contract_address,
                abi=contract_data['abi']
            )

            # Get event object
            event = getattr(contract.events, event_name)
            if event is None:
                raise ContractError(
                    f"Event not found: {event_name}",
                    details={
                        "contract_address": contract_address,
                        "event_name": event_name
                    }
                )

            # Set up monitoring parameters
            latest_block = await web3.eth.block_number
            start_block = from_block if from_block is not None else max(0, latest_block - 1000)
            end_block = to_block if to_block is not None else latest_block

            # Process events in batches with retry logic
            async def monitor():
                current_block = start_block
                while current_block <= end_block:
                    batch_end = min(current_block + batch_size, end_block)
                    retry_count = 0

                    while retry_count < max_retries:
                        try:
                            # Add chain-specific handling for BNB Chain
                            if chain_id == 'bnb':
                                # BNB Chain has different block time, adjust batch size
                                adjusted_batch_size = min(batch_size, 100)
                                batch_end = min(current_block + adjusted_batch_size, end_block)

                            events = await event.get_logs(
                                fromBlock=current_block,
                                toBlock=batch_end,
                                argument_filters=filters
                            )

                            for evt in events:
                                block = await web3.eth.get_block(evt.blockNumber)
                                yield {
                                    'event': event_name,
                                    'args': dict(evt.args),
                                    'block_number': evt.blockNumber,
                                    'transaction_hash': evt.transactionHash.hex(),
                                    'log_index': evt.logIndex,
                                    'chain_id': chain_id,
                                    'timestamp': block.timestamp,
                                    'block_hash': evt.blockHash.hex()
                                }
                            break  # Success, exit retry loop

                        except Exception as e:
                            retry_count += 1
                            if retry_count >= max_retries:
                                print(f"Error processing events in block range {current_block}-{batch_end}: {str(e)}")
                                break
                            await asyncio.sleep(retry_interval)

                    current_block = batch_end + 1

            async for event_data in monitor():
                yield event_data

        except Exception as e:
            raise ContractError(
                f"Failed to monitor events: {str(e)}",
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
