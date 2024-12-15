"""
Fallback manager for AI model providers.
"""
from typing import Dict, List, Optional, Any, Tuple
import logging
from .providers.base import ModelProviderInterface

class FallbackManager:
    """Manages fallback strategies for AI model providers."""

    def __init__(self):
        """Initialize fallback manager."""
        self._providers: Dict[str, List[ModelProviderInterface]] = {}
        self._fallback_chains: Dict[str, List[str]] = {
            "gpt-4": ["claude-3", "llama-2-70b", "mistral-large", "gemini-pro"],
            "claude-3": ["gpt-4", "llama-2-70b", "mistral-large", "gemini-pro"],
            "llama-2-70b": ["claude-3", "gpt-4", "mistral-large", "gemini-pro"],
            "mistral-large": ["claude-3", "gpt-4", "llama-2-70b", "gemini-pro"],
            "gemini-pro": ["claude-3", "gpt-4", "llama-2-70b", "mistral-large"]
        }
        self._logger = logging.getLogger(__name__)

    def register_provider(self, model: str, provider: ModelProviderInterface, priority: int = 0) -> None:
        """Register a provider for a model.

        Args:
            model: Model identifier
            provider: Provider instance
            priority: Priority level (higher = more preferred)
        """
        if model not in self._providers:
            self._providers[model] = []
        self._providers[model].append(provider)
        self._providers[model].sort(key=lambda x: id(x), reverse=True)  # Sort by priority

    async def execute_with_fallback(
        self,
        primary_model: str,
        operation: str,
        *args: Any,
        max_retries: int = 3,
        **kwargs: Any
    ) -> Tuple[str, ModelProviderInterface]:
        """Execute operation with fallback support.

        Args:
            primary_model: Primary model to try first
            operation: Operation name (e.g., 'generate')
            *args: Operation arguments
            max_retries: Maximum number of retries
            **kwargs: Operation keyword arguments

        Returns:
            Tuple of (result, successful provider)

        Raises:
            RuntimeError: If all providers fail
        """
        errors = []
        tried_models = set()

        # Try primary model first
        if primary_model in self._providers:
            for provider in self._providers[primary_model]:
                try:
                    result = await getattr(provider, operation)(*args, **kwargs)
                    return result, provider
                except Exception as e:
                    errors.append((primary_model, str(e)))
                    self._logger.warning(f"Primary model {primary_model} failed: {e}")
            tried_models.add(primary_model)

        # Try fallback chain
        fallback_chain = self._fallback_chains.get(primary_model, [])
        for fallback_model in fallback_chain:
            if fallback_model in tried_models:
                continue

            if fallback_model in self._providers:
                for provider in self._providers[fallback_model]:
                    try:
                        result = await getattr(provider, operation)(*args, **kwargs)
                        self._logger.info(f"Fallback to {fallback_model} successful")
                        return result, provider
                    except Exception as e:
                        errors.append((fallback_model, str(e)))
                        self._logger.warning(f"Fallback model {fallback_model} failed: {e}")
            tried_models.add(fallback_model)

        error_msg = "All providers failed:\n" + "\n".join(
            f"- {model}: {error}" for model, error in errors
        )
        raise RuntimeError(error_msg)
