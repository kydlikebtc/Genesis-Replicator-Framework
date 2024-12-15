"""
Meta's Llama model provider implementation.
"""
from typing import Any, Dict, List, Optional
import replicate

from .base import ModelProviderInterface

class LlamaProvider(ModelProviderInterface):
    """Provider for Meta's Llama models."""

    def __init__(self):
        """Initialize Llama provider."""
        self.client = None
        self.model = "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3"
        self.initialized = False

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize Replicate client for Llama.

        Args:
            config: Configuration with API key and optional model version

        Raises:
            ValueError: If API key is missing
            RuntimeError: If initialization fails
        """
        if 'api_key' not in config:
            raise ValueError("Replicate API key required")

        try:
            self.client = replicate.Client(api_token=config['api_key'])
            if 'model' in config:
                self.model = config['model']
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Llama client: {str(e)}")

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """Generate text using Llama model.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences
            **kwargs: Additional parameters

        Returns:
            Generated text

        Raises:
            RuntimeError: If generation fails
        """
        if not self.initialized:
            raise RuntimeError("Provider not initialized")

        try:
            output = await self.client.async_run(
                self.model,
                input={
                    "prompt": prompt,
                    "max_length": max_tokens or 512,
                    "temperature": temperature,
                    "stop_sequences": stop_sequences or [],
                    **kwargs
                }
            )
            return output[0] if isinstance(output, list) else str(output)
        except Exception as e:
            raise RuntimeError(f"Text generation failed: {str(e)}")

    async def get_token_count(self, text: str) -> int:
        """Get approximate token count for text.

        Args:
            text: Input text

        Returns:
            Approximate number of tokens

        Raises:
            RuntimeError: If token counting fails
        """
        if not self.initialized:
            raise RuntimeError("Provider not initialized")

        try:
            # Approximate token count (4 chars per token)
            return len(text) // 4
        except Exception as e:
            raise RuntimeError(f"Token counting failed: {str(e)}")

    async def validate_response(self, response: str) -> bool:
        """Validate Llama response.

        Args:
            response: Generated response to validate

        Returns:
            True if response is valid

        Raises:
            RuntimeError: If validation fails
        """
        if not response or len(response.strip()) == 0:
            return False

        try:
            # Basic validation - ensure response is not empty and within reasonable length
            token_count = await self.get_token_count(response)
            return 0 < token_count < 4096  # Llama's typical response limit
        except Exception as e:
            raise RuntimeError(f"Response validation failed: {str(e)}")

    async def get_model_info(self) -> Dict[str, Any]:
        """Get Llama model information.

        Returns:
            Dictionary with model information

        Raises:
            RuntimeError: If fetching info fails
        """
        if not self.initialized:
            raise RuntimeError("Provider not initialized")

        return {
            "name": "Llama-2-70B",
            "version": "2",
            "capabilities": [
                "text_generation",
                "code_generation",
                "analysis",
                "reasoning"
            ],
            "max_tokens": 4096,
            "provider": "Meta"
        }
