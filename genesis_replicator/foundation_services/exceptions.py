"""
Base exceptions for Genesis Replicator Framework.

This module defines the exception hierarchy for the framework, providing
standardized error handling across all components.
"""
from typing import Optional, Dict, Any


class GenesisError(Exception):
    """Base exception for all framework errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Initialize the base error.

        Args:
            message: Human-readable error description
            error_code: Unique error identifier (e.g., 'EVT001')
            details: Additional error context
        """
        self.message = message
        self.error_code = error_code or 'GEN000'
        self.details = details or {}
        super().__init__(f"[{self.error_code}] {message}")


class FoundationError(GenesisError):
    """Base exception for foundation services."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'FND000'
        super().__init__(message, error_code, details)


class EventSystemError(FoundationError):
    """Event system specific errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'EVT000'
        super().__init__(message, error_code, details)


class EventNotFoundError(EventSystemError):
    """Raised when an event type is not found."""
    def __init__(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Event type '{event_type}' not found",
            'EVT001',
            details
        )


class EventValidationError(EventSystemError):
    """Raised when event validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'EVT002', details)


class EventHandlerError(EventSystemError):
    """Raised when an event handler fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'EVT003', details)


class EventRouterError(EventSystemError):
    """Raised for event router operational errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'EVT004', details)


class BlockchainError(FoundationError):
    """Blockchain integration errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'BCH000'
        super().__init__(message, error_code, details)


class ChainConnectionError(BlockchainError):
    """Raised when blockchain connection fails."""
    def __init__(self, chain_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Failed to connect to blockchain {chain_id}",
            'BCH001',
            details
        )


class ContractError(BlockchainError):
    """Raised for smart contract related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'BCH002', details)


class TransactionError(BlockchainError):
    """Raised for transaction-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'BCH003', details)


class ChainConfigError(BlockchainError):
    """Raised for blockchain configuration errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'BCH005', details)


class SyncError(BlockchainError):
    """Raised for blockchain synchronization errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'BCH004', details)


class AgentError(GenesisError):
    """Base exception for agent-related errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'AGT000'
        super().__init__(message, error_code, details)


class AgentStateError(AgentError):
    """Raised for agent state-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'AGT001', details)


class ResourceError(AgentError):
    """Raised for resource management errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'AGT002', details)


class DecisionEngineError(GenesisError):
    """Base exception for decision engine errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'DEC000'
        super().__init__(message, error_code, details)


class RuleEngineError(DecisionEngineError):
    """Raised for rule engine specific errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'DEC001', details)


class StrategyError(DecisionEngineError):
    """Raised for strategy-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'DEC002', details)


class AIModuleError(GenesisError):
    """Base exception for AI module errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'AIM000'
        super().__init__(message, error_code, details)


class ModelError(AIModuleError):
    """Raised for AI model-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'AIM001', details)


class TrainingError(AIModuleError):
    """Raised for model training errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'AIM002', details)


class PredictionError(AIModuleError):
    """Raised for prediction-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'AIM003', details)


class SecurityError(GenesisError):
    """Base exception for security-related errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'SEC000'
        super().__init__(message, error_code, details)


class AuthenticationError(SecurityError):
    """Raised for authentication failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'SEC001', details)


class AuthorizationError(SecurityError):
    """Raised for authorization failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'SEC002', details)


class CryptoError(SecurityError):
    """Raised for cryptographic operation failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'SEC003', details)


class ConfigurationError(GenesisError):
    """Base exception for configuration errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'CFG000'
        super().__init__(message, error_code, details)


class ValidationError(ConfigurationError):
    """Raised for configuration validation errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'CFG001', details)


class EnvironmentError(ConfigurationError):
    """Raised for environment-related configuration errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'CFG002', details)


class PluginError(GenesisError):
    """Base exception for plugin system errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'PLG000'
        super().__init__(message, error_code, details)


class PluginLoadError(PluginError):
    """Raised when plugin loading fails."""
    def __init__(self, plugin_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Failed to load plugin: {plugin_name}",
            'PLG001',
            details
        )


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'PLG002', details)


class MonitoringError(GenesisError):
    """Base exception for monitoring system errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_code = error_code or 'MON000'
        super().__init__(message, error_code, details)


class MetricsError(MonitoringError):
    """Raised for metrics collection errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'MON001', details)


class AlertError(MonitoringError):
    """Raised for alerting system errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 'MON002', details)
