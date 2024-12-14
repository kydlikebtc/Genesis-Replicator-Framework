"""
Exceptions Module for Client SDK

Custom exceptions for the Genesis Replicator Framework client SDK.
"""

class ClientSDKError(Exception):
    """Base exception for Client SDK errors."""
    pass

class AuthenticationError(ClientSDKError):
    """Raised when authentication fails."""
    pass

class SessionError(ClientSDKError):
    """Raised when there are session-related issues."""
    pass

class APIError(ClientSDKError):
    """Raised when API requests fail."""
    def __init__(self, message: str, status_code: int):
        self.status_code = status_code
        super().__init__(message)

class ConfigurationError(ClientSDKError):
    """Raised when there are configuration issues."""
    pass

class ValidationError(ClientSDKError):
    """Raised when validation fails."""
    pass
