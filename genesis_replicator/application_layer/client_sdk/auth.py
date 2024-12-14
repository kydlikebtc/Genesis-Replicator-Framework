"""
Authentication Module for Client SDK

Handles authentication and session management for the Genesis Replicator Framework.
"""
from typing import Dict, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Session:
    """Represents an authenticated session."""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    token: str
    metadata: Dict[str, Any]

class AuthManager:
    """Manages authentication and session handling."""

    def __init__(self, secret_key: str = "your-secret-key"):
        """Initialize the AuthManager."""
        self.secret_key = secret_key
        self.active_sessions: Dict[str, Session] = {}
        logger.info("Auth Manager initialized")

    def authenticate(
        self,
        credentials: Dict[str, str]
    ) -> Optional[Session]:
        """
        Authenticate a user with provided credentials.

        Args:
            credentials: Dictionary containing authentication credentials

        Returns:
            Session object if authentication successful, None otherwise
        """
        # Validate required credentials
        if not all(k in credentials for k in ["user_id", "api_key"]):
            logger.error("Missing required credentials")
            return None

        try:
            # Create session with JWT token
            session_id = str(uuid.uuid4())
            created_at = datetime.now()
            expires_at = created_at + timedelta(hours=24)

            payload = {
                "session_id": session_id,
                "user_id": credentials["user_id"],
                "exp": int(expires_at.timestamp())
            }

            token = jwt.encode(payload, self.secret_key, algorithm="HS256")

            session = Session(
                session_id=session_id,
                user_id=credentials["user_id"],
                created_at=created_at,
                expires_at=expires_at,
                token=token,
                metadata={"api_key": credentials["api_key"]}
            )

            self.active_sessions[session_id] = session
            logger.info(f"Authentication successful for user: {credentials['user_id']}")
            return session

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return None

    def validate_session(self, token: str) -> Optional[Session]:
        """
        Validate a session token.

        Args:
            token: JWT token to validate

        Returns:
            Session object if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            session_id = payload["session_id"]

            if session_id not in self.active_sessions:
                logger.warning(f"Session not found: {session_id}")
                return None

            session = self.active_sessions[session_id]
            if datetime.now() > session.expires_at:
                logger.warning(f"Session expired: {session_id}")
                self.revoke_session(session_id)
                return None

            return session

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None

    def revoke_session(self, session_id: str) -> None:
        """
        Revoke an active session.

        Args:
            session_id: ID of the session to revoke
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Session revoked: {session_id}")

    def refresh_session(self, token: str) -> Optional[Session]:
        """
        Refresh a session token.

        Args:
            token: Current session token

        Returns:
            New session object if refresh successful, None otherwise
        """
        current_session = self.validate_session(token)
        if not current_session:
            return None

        # Create new session with extended expiration
        new_session_id = str(uuid.uuid4())
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=24)

        payload = {
            "session_id": new_session_id,
            "user_id": current_session.user_id,
            "exp": int(expires_at.timestamp())
        }

        new_token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        new_session = Session(
            session_id=new_session_id,
            user_id=current_session.user_id,
            created_at=created_at,
            expires_at=expires_at,
            token=new_token,
            metadata=current_session.metadata
        )

        # Revoke old session and store new one
        self.revoke_session(current_session.session_id)
        self.active_sessions[new_session_id] = new_session

        logger.info(f"Session refreshed for user: {current_session.user_id}")
        return new_session
