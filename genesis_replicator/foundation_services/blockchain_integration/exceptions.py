"""Custom exceptions for blockchain integration."""

class BlockchainError(Exception):
    """Base exception for blockchain integration errors."""

    def __init__(self, message: str, details: dict = None):
        """Initialize with message and optional details."""
        super().__init__(message)
        self.details = details or {}


class ChainConnectionError(BlockchainError):
    """Raised when chain connection fails."""
    pass


class ConfigurationError(BlockchainError):
    """Raised when chain configuration is invalid."""
    pass


class SecurityError(BlockchainError):
    """Raised when security validation fails."""
    pass


class TransactionError(BlockchainError):
    """Raised when transaction execution fails."""
    pass


class ContractError(BlockchainError):
    """Raised when contract operation fails."""
    pass
