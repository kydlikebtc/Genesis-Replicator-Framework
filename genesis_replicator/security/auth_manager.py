"""
Authentication and authorization manager for Genesis Replicator Framework.
"""
import asyncio
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from .crypto_utils import hash_password, verify_password

@dataclass
class UserCredentials:
    """User credentials data class."""
    username: str
    password_hash: str
    roles: List[str]
    last_login: Optional[datetime] = None

class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self, secret_key: str, token_expiry: int = 3600):
        """Initialize auth manager.

        Args:
            secret_key: Key for JWT token signing
            token_expiry: Token expiry time in seconds
        """
        self._secret_key = secret_key
        self._token_expiry = token_expiry
        self._users: Dict[str, UserCredentials] = {}
        self._lock = asyncio.Lock()

    async def register_user(
        self,
        username: str,
        password: str,
        roles: List[str]
    ) -> bool:
        """Register a new user.

        Args:
            username: User identifier
            password: Plain text password
            roles: List of role identifiers

        Returns:
            bool: Success status
        """
        async with self._lock:
            if username in self._users:
                return False

            password_hash = await hash_password(password)
            self._users[username] = UserCredentials(
                username=username,
                password_hash=password_hash,
                roles=roles
            )
            return True

    async def authenticate(
        self,
        username: str,
        password: str
    ) -> Optional[str]:
        """Authenticate user and generate token.

        Args:
            username: User identifier
            password: Plain text password

        Returns:
            Optional[str]: JWT token if authenticated
        """
        user = self._users.get(username)
        if not user:
            return None

        if not await verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.utcnow()

        # Generate JWT token
        payload = {
            'sub': username,
            'roles': user.roles,
            'exp': datetime.utcnow() + timedelta(seconds=self._token_expiry)
        }
        return jwt.encode(payload, self._secret_key, algorithm='HS256')

    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token.

        Args:
            token: JWT token string

        Returns:
            Optional[Dict]: Token payload if valid
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=['HS256']
            )
            return payload
        except jwt.InvalidTokenError:
            return None

    async def check_permission(
        self,
        token: str,
        required_roles: List[str]
    ) -> bool:
        """Check if token has required roles.

        Args:
            token: JWT token string
            required_roles: List of required role identifiers

        Returns:
            bool: True if has permission
        """
        payload = await self.verify_token(token)
        if not payload:
            return False

        user_roles = set(payload.get('roles', []))
        return any(role in user_roles for role in required_roles)
