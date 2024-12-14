"""
Contract Manager Module

This module implements the smart contract management system for the Genesis Replicator Framework.
It provides functionality for contract deployment, interaction, and monitoring.
"""
from typing import Dict, Optional, Any, List
import json
import logging
import asyncio
from pathlib import Path
from web3 import Web3
from web3.contract import Contract

from .chain_manager import ChainManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContractConfig:
    """Configuration for smart contract"""
    def __init__(
        self,
        name: str,
        abi: List[Dict[str, Any]],
        bytecode: str,
        address: Optional[str] = None
    ):
        self.name = name
        self.abi = abi
        self.bytecode = bytecode
        self.address = address

class ContractManager:
    """
    Manages smart contract operations and monitoring.

    Attributes:
        chain_manager (ChainManager): Reference to chain manager
        contracts (Dict[str, Dict[str, Contract]]): Deployed contracts by chain and name
        contract_configs (Dict[str, ContractConfig]): Contract configurations
    """

    def __init__(self, chain_manager: ChainManager):
        """
        Initialize ContractManager.

        Args:
            chain_manager (ChainManager): Chain manager instance
        """
        self.chain_manager = chain_manager
        self.contracts: Dict[str, Dict[str, Contract]] = {}
        self.contract_configs: Dict[str, ContractConfig] = {}
        logger.info("ContractManager initialized")

    def load_contract_config(
        self,
        name: str,
        abi_path: str,
        bytecode_path: Optional[str] = None,
        address: Optional[str] = None
    ) -> bool:
        """
        Load contract configuration from files.

        Args:
            name (str): Contract name
            abi_path (str): Path to ABI JSON file
            bytecode_path (Optional[str]): Path to bytecode file
            address (Optional[str]): Deployed contract address

        Returns:
            bool: True if configuration loaded successfully
        """
        try:
            # Load ABI
            abi_file = Path(abi_path)
            if not abi_file.exists():
                logger.error(f"ABI file not found: {abi_path}")
                return False

            with abi_file.open() as f:
                abi = json.load(f)

            # Load bytecode if provided
            bytecode = ""
            if bytecode_path:
                bytecode_file = Path(bytecode_path)
                if not bytecode_file.exists():
                    logger.error(f"Bytecode file not found: {bytecode_path}")
                    return False

                with bytecode_file.open() as f:
                    bytecode = f.read().strip()

            # Create contract config
            self.contract_configs[name] = ContractConfig(
                name=name,
                abi=abi,
                bytecode=bytecode,
                address=address
            )
            logger.info(f"Loaded contract configuration for {name}")
            return True

        except Exception as e:
            logger.error(f"Error loading contract configuration: {str(e)}")
            return False

    async def deploy_contract(
        self,
        contract_name: str,
        chain_name: Optional[str] = None,
        *args,
        **kwargs
    ) -> Optional[str]:
        """
        Deploy a smart contract.

        Args:
            contract_name (str): Name of contract to deploy
            chain_name (Optional[str]): Target chain name
            *args: Contract constructor arguments
            **kwargs: Additional deployment options

        Returns:
            Optional[str]: Deployed contract address if successful
        """
        if contract_name not in self.contract_configs:
            logger.error(f"Contract configuration not found: {contract_name}")
            return None

        config = self.contract_configs[contract_name]
        if not config.bytecode:
            logger.error(f"No bytecode available for contract: {contract_name}")
            return None

        web3 = self.chain_manager.get_web3(chain_name)
        if not web3:
            logger.error("No Web3 connection available")
            return None

        try:
            # Create contract instance
            contract = web3.eth.contract(
                abi=config.abi,
                bytecode=config.bytecode
            )

            # Get transaction parameters
            gas_price = kwargs.get('gas_price', web3.eth.gas_price)
            from_address = kwargs.get('from_address', web3.eth.accounts[0])

            # Deploy contract
            transaction = await contract.constructor(*args).build_transaction({
                'from': from_address,
                'gas': kwargs.get('gas', 2000000),
                'gasPrice': gas_price,
                'nonce': web3.eth.get_transaction_count(from_address)
            })

            # Sign and send transaction
            signed = web3.eth.account.sign_transaction(
                transaction,
                kwargs.get('private_key')
            )
            tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)

            # Wait for deployment
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            contract_address = receipt.contractAddress

            # Store deployed contract
            chain = chain_name or self.chain_manager.default_chain
            if chain not in self.contracts:
                self.contracts[chain] = {}

            self.contracts[chain][contract_name] = web3.eth.contract(
                address=contract_address,
                abi=config.abi
            )

            logger.info(f"Deployed contract {contract_name} at {contract_address}")
            return contract_address

        except Exception as e:
            logger.error(f"Error deploying contract: {str(e)}")
            return None

    def get_contract(
        self,
        contract_name: str,
        chain_name: Optional[str] = None
    ) -> Optional[Contract]:
        """
        Get deployed contract instance.

        Args:
            contract_name (str): Contract name
            chain_name (Optional[str]): Chain name

        Returns:
            Optional[Contract]: Contract instance if available
        """
        chain = chain_name or self.chain_manager.default_chain
        if not chain:
            logger.error("No chain specified or default chain available")
            return None

        return self.contracts.get(chain, {}).get(contract_name)

    async def call_contract_method(
        self,
        contract_name: str,
        method_name: str,
        chain_name: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Call a contract method.

        Args:
            contract_name (str): Contract name
            method_name (str): Method to call
            chain_name (Optional[str]): Chain name
            *args: Method arguments
            **kwargs: Additional call options

        Returns:
            Any: Method result
        """
        contract = self.get_contract(contract_name, chain_name)
        if not contract:
            logger.error(f"Contract not found: {contract_name}")
            return None

        try:
            method = getattr(contract.functions, method_name)
            if not method:
                logger.error(f"Method not found: {method_name}")
                return None

            # Handle transaction options
            if kwargs.get('transact', False):
                tx = method(*args).build_transaction({
                    'from': kwargs.get('from_address'),
                    'gas': kwargs.get('gas', 2000000),
                    'gasPrice': kwargs.get('gas_price'),
                    'nonce': kwargs.get('nonce')
                })
                return tx
            else:
                return method(*args).call()

        except Exception as e:
            logger.error(f"Error calling contract method: {str(e)}")
            return None

    async def monitor_contract_events(
        self,
        contract_name: str,
        event_name: str,
        chain_name: Optional[str] = None,
        from_block: int = 0
    ) -> None:
        """
        Monitor contract events.

        Args:
            contract_name (str): Contract name
            event_name (str): Event to monitor
            chain_name (Optional[str]): Chain name
            from_block (int): Starting block number
        """
        contract = self.get_contract(contract_name, chain_name)
        if not contract:
            logger.error(f"Contract not found: {contract_name}")
            return

        try:
            event = getattr(contract.events, event_name)
            if not event:
                logger.error(f"Event not found: {event_name}")
                return

            # Create event filter
            event_filter = event.create_filter(fromBlock=from_block)

            while True:
                for event in event_filter.get_new_entries():
                    logger.info(f"New event {event_name}: {event}")
                await asyncio.sleep(2)  # Poll every 2 seconds

        except Exception as e:
            logger.error(f"Error monitoring contract events: {str(e)}")
