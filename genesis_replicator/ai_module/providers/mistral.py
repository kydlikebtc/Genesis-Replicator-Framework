"""
Mistral AI model provider implementation.
"""
from typing import Any, Dict, List, Optional
import mistralai

from .base import ModelProviderInterface

class MistralProvider(ModelProviderInterface):
    """Provider for Mistral AI models."""

    def __init__(self):
        """Initialize Mistral provider."""
        self.client = None
        self.model = "mistral-large-latest"
        self.initialized = False

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize Mistral client with API key.

        Args:
            config: Configuration with API key and optional model version

        Raises:
            ValueError: If API key is missing
            RuntimeError: If initialization fails
        """
        if 'api_key' not in config:
            raise ValueError("Mistral API key required")

        try:
            self.client = mistralai.AsyncMistralClient(api_key=config['api_key'])
            if 'model' in config:
                self.model = config['model']
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Mistral client: {str(e)}")

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any
    ) -> str:
        """Generate text using Mistral model.

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
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop_sequences,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Text generation failed: {str(e)}")

    async def get_token_count(self, text: str) -> int:
        """Get token count for text.

        Args:
            text: Input text

        Returns:
            Number of tokens

        Raises:
            RuntimeError: If token counting fails
        """
        if not self.initialized:
            raise RuntimeError("Provider not initialized")

        try:
            # Mistral's tokenizer approximation (similar to GPT tokenization)
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception as e:
            raise RuntimeError(f"Token counting failed: {str(e)}")

    async def validate_response(self, response: str) -> bool:
        """Validate Mistral response.

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
            return 0 < token_count < 4096  # Mistral's typical response limit
        except Exception as e:
            raise RuntimeError(f"Response validation failed: {str(e)}")

    async def get_model_info(self) -> Dict[str, Any]:
        """Get Mistral model information.

        Returns:
            Dictionary with model information

        Raises:
            RuntimeError: If fetching info fails
        """
        if not self.initialized:
            raise RuntimeError("Provider not initialized")

        return {
            "name": self.model,
            "version": "latest",
            "capabilities": [
                "text_generation",
                "code_generation",
                "analysis",
                "reasoning"
            ],
            "max_tokens": 32768,  # Mistral's context window
            "provider": "Mistral AI"
        }
