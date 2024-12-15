"""
Base interface for AI model providers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class ModelProviderInterface(ABC):
    """Abstract base class for AI model providers."""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the model provider with configuration.

        Args:
            config: Provider-specific configuration

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If initialization fails
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """Generate text from the model.

        Args:
            prompt: Input prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            stop_sequences: Optional sequences to stop generation
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If generation fails
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def get_token_count(self, text: str) -> int:
        """Get token count for text.

        Args:
            text: Input text

        Returns:
            Number of tokens

        Raises:
            RuntimeError: If token counting fails
        """
        pass

    @abstractmethod
    async def validate_response(self, response: str) -> bool:
        """Validate model response.

        Args:
            response: Generated response to validate

        Returns:
            True if response is valid, False otherwise

        Raises:
            RuntimeError: If validation fails
        """
        pass

    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Dictionary containing model information:
            - name: Model name
            - version: Model version
            - capabilities: List of supported capabilities
            - max_tokens: Maximum context length
            - provider: Provider name

        Raises:
            RuntimeError: If fetching info fails
        """
        pass
