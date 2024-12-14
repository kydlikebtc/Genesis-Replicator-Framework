"""
Client SDK Module

Main client interface for the Genesis Replicator Framework.
"""
from typing import Dict, Any, Optional, List
import logging
import requests
from datetime import datetime
from .auth import AuthManager, Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClientSDK:
    """Main client interface for interacting with the framework."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        auth_manager: Optional[AuthManager] = None
    ):
        """
        Initialize the ClientSDK.

        Args:
            base_url: Base URL for API endpoints
            auth_manager: Optional custom auth manager
        """
        self.base_url = base_url.rstrip('/')
        self.auth_manager = auth_manager or AuthManager()
        self.session: Optional[Session] = None
        logger.info("Client SDK initialized")

    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with the framework.

        Args:
            credentials: Dictionary containing authentication credentials

        Returns:
            True if authentication successful, False otherwise
        """
        self.session = self.auth_manager.authenticate(credentials)
        return self.session is not None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.session:
            headers["Authorization"] = f"Bearer {self.session.token}"
        return headers

    async def create_agent(
        self,
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new agent instance.

        Args:
            agent_config: Configuration for the new agent

        Returns:
            Created agent details
        """
        if not self.session:
            raise ValueError("Not authenticated")

        try:
            response = requests.post(
                f"{self.base_url}/agents",
                json=agent_config,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get status of an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Agent status information
        """
        if not self.session:
            raise ValueError("Not authenticated")

        try:
            response = requests.get(
                f"{self.base_url}/agents/{agent_id}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get agent status: {str(e)}")
            raise

    async def update_agent_config(
        self,
        agent_id: str,
        config_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update agent configuration.

        Args:
            agent_id: ID of the agent to update
            config_updates: Configuration updates to apply

        Returns:
            Updated agent configuration
        """
        if not self.session:
            raise ValueError("Not authenticated")

        try:
            response = requests.patch(
                f"{self.base_url}/agents/{agent_id}/config",
                json=config_updates,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update agent config: {str(e)}")
            raise

    async def list_agents(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all agents matching the filters.

        Args:
            filters: Optional filters to apply

        Returns:
            List of matching agents
        """
        if not self.session:
            raise ValueError("Not authenticated")

        try:
            response = requests.get(
                f"{self.base_url}/agents",
                params=filters,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list agents: {str(e)}")
            raise

    def refresh_auth(self) -> bool:
        """
        Refresh the authentication token.

        Returns:
            True if refresh successful, False otherwise
        """
        if not self.session:
            return False

        new_session = self.auth_manager.refresh_session(self.session.token)
        if new_session:
            self.session = new_session
            return True
        return False

    def logout(self) -> None:
        """Log out and invalidate the current session."""
        if self.session:
            self.auth_manager.revoke_session(self.session.session_id)
            self.session = None
            logger.info("Logged out successfully")
