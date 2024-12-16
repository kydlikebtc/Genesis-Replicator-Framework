"""Blockchain integration exceptions."""

from typing import Any, Dict, Optional


class BlockchainError(Exception):
    """Base class for blockchain integration errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.details = details or {}


class ChainConnectionError(BlockchainError):
    """Raised when chain connection fails."""
    pass


class ChainConfigError(BlockchainError):
    """Raised when chain configuration is invalid."""
    pass


class SecurityError(BlockchainError):
    """Raised when security validation fails."""
    pass


class TransactionError(BlockchainError):
    """Raised when transaction execution fails."""
    pass


class ContractError(BlockchainError):
    """Raised when contract interaction fails."""
    pass


class ProtocolError(BlockchainError):
    """Raised when protocol adapter operations fail."""
    pass


class MonitoringError(BlockchainError):
    """Raised when chain monitoring fails."""
    pass


class ValidationError(BlockchainError):
    """Raised when validation fails."""
    pass
