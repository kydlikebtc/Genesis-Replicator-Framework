"""
Lifecycle Manager Module

This module manages the lifecycle of agents in the Genesis Replicator Framework.
It handles agent initialization, state management, and termination.
"""
from typing import Dict, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum
from time import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Enumeration of possible agent states"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"
    ERROR = "error"

@dataclass
class AgentInfo:
    """Data class for storing agent information"""
    state: AgentState
    config: Dict[str, Any]
    resources: Dict[str, Any]
    last_active: float
    error: Optional[str] = None

class LifecycleManager:
    """
    Manages agent lifecycles including initialization, state transitions, and termination.

    Attributes:
        agents (Dict[str, AgentInfo]): Dictionary storing agent information
    """

    def __init__(self):
        """Initialize the LifecycleManager."""
        self.agents: Dict[str, AgentInfo] = {}
        logger.info("LifecycleManager initialized")

    def initialize_agent(self, agent_id: str, config: Dict[str, Any]) -> str:
        """
        Initialize a new agent with the given configuration.

        Args:
            agent_id (str): Unique identifier for the agent
            config (Dict[str, Any]): Configuration parameters for the agent

        Returns:
            str: Status message indicating success or failure

        Raises:
            ValueError: If agent_id already exists
        """
        try:
            if agent_id in self.agents:
                raise ValueError(f"Agent {agent_id} already exists")

            agent_info = AgentInfo(
                state=AgentState.INITIALIZED,
                config=config,
                resources={},
                last_active=time()
            )
            self.agents[agent_id] = agent_info

            logger.info(f"Agent {agent_id} initialized successfully")
            return f"Agent {agent_id} initialized"

        except Exception as e:
            logger.error(f"Failed to initialize agent {agent_id}: {str(e)}")
            raise

    def start_agent(self, agent_id: str) -> str:
        """
        Start a previously initialized agent.

        Args:
            agent_id (str): Agent identifier

        Returns:
            str: Status message

        Raises:
            ValueError: If agent not found or in invalid state
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            if agent.state != AgentState.INITIALIZED and agent.state != AgentState.PAUSED:
                raise ValueError(f"Agent {agent_id} in invalid state: {agent.state}")

            agent.state = AgentState.RUNNING
            agent.last_active = time()

            logger.info(f"Agent {agent_id} started successfully")
            return f"Agent {agent_id} started"

        except Exception as e:
            logger.error(f"Failed to start agent {agent_id}: {str(e)}")
            raise

    def pause_agent(self, agent_id: str) -> str:
        """
        Pause a running agent.

        Args:
            agent_id (str): Agent identifier

        Returns:
            str: Status message

        Raises:
            ValueError: If agent not found or not running
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            if agent.state != AgentState.RUNNING:
                raise ValueError(f"Agent {agent_id} not running")

            agent.state = AgentState.PAUSED
            agent.last_active = time()

            logger.info(f"Agent {agent_id} paused successfully")
            return f"Agent {agent_id} paused"

        except Exception as e:
            logger.error(f"Failed to pause agent {agent_id}: {str(e)}")
            raise

    def terminate_agent(self, agent_id: str) -> str:
        """
        Terminate an agent and clean up its resources.

        Args:
            agent_id (str): Agent identifier

        Returns:
            str: Status message

        Raises:
            ValueError: If agent not found
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            agent.state = AgentState.TERMINATED
            agent.last_active = time()

            # Clean up resources
            self._cleanup_agent_resources(agent_id)
            del self.agents[agent_id]

            logger.info(f"Agent {agent_id} terminated successfully")
            return f"Agent {agent_id} terminated"

        except Exception as e:
            logger.error(f"Failed to terminate agent {agent_id}: {str(e)}")
            raise

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of an agent.

        Args:
            agent_id (str): Agent identifier

        Returns:
            Optional[Dict[str, Any]]: Agent status information or None if not found
        """
        try:
            if agent_id not in self.agents:
                return None

            agent = self.agents[agent_id]
            return {
                "state": agent.state.value,
                "config": agent.config,
                "resources": agent.resources,
                "last_active": agent.last_active,
                "error": agent.error
            }

        except Exception as e:
            logger.error(f"Error getting status for agent {agent_id}: {str(e)}")
            return None

    def update_agent_config(self, agent_id: str, config_updates: Dict[str, Any]) -> str:
        """
        Update an agent's configuration.

        Args:
            agent_id (str): Agent identifier
            config_updates (Dict[str, Any]): Configuration updates to apply

        Returns:
            str: Status message

        Raises:
            ValueError: If agent not found
        """
        try:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} not found")

            agent = self.agents[agent_id]
            agent.config.update(config_updates)
            agent.last_active = time()

            logger.info(f"Configuration updated for agent {agent_id}")
            return f"Agent {agent_id} configuration updated"

        except Exception as e:
            logger.error(f"Failed to update config for agent {agent_id}: {str(e)}")
            raise

    def _cleanup_agent_resources(self, agent_id: str) -> None:
        """
        Clean up resources associated with an agent.

        Args:
            agent_id (str): Agent identifier
        """
        try:
            agent = self.agents[agent_id]
            for resource in agent.resources.values():
                try:
                    # Implement resource cleanup logic here
                    pass
                except Exception as e:
                    logger.warning(f"Failed to clean up resource for agent {agent_id}: {str(e)}")

            agent.resources.clear()

        except Exception as e:
            logger.error(f"Error during resource cleanup for agent {agent_id}: {str(e)}")
