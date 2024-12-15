"""
Tests for AI model fallback manager.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from genesis_replicator.ai_module.fallback_manager import FallbackManager
from genesis_replicator.ai_module.providers.base import ModelProviderInterface

class MockProvider(ModelProviderInterface):
    def __init__(self, success=True):
        self.success = success
        self.generate = AsyncMock(side_effect=self._generate)
        self.initialize = AsyncMock()
        self.get_token_count = AsyncMock(return_value=10)
        self.validate_response = AsyncMock(return_value=True)
        self.get_model_info = AsyncMock(return_value={})

    async def _generate(self, *args, **kwargs):
        if not self.success:
            raise RuntimeError("Generation failed")
        return "Test response"

@pytest.fixture
def fallback_manager():
    return FallbackManager()

@pytest.mark.asyncio
async def test_fallback_manager_primary_success(fallback_manager):
    # Test successful primary provider
    primary = MockProvider(success=True)
    fallback_manager.register_provider("gpt-4", primary)

    result, provider = await fallback_manager.execute_with_fallback(
        "gpt-4", "generate", "test prompt"
    )

    assert result == "Test response"
    assert provider == primary
    primary.generate.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_manager_primary_failure(fallback_manager):
    # Test primary failure with successful fallback
    primary = MockProvider(success=False)
    fallback = MockProvider(success=True)

    fallback_manager.register_provider("gpt-4", primary)
    fallback_manager.register_provider("claude-3", fallback)

    result, provider = await fallback_manager.execute_with_fallback(
        "gpt-4", "generate", "test prompt"
    )

    assert result == "Test response"
    assert provider == fallback
    primary.generate.assert_called_once()
    fallback.generate.assert_called_once()

@pytest.mark.asyncio
async def test_fallback_manager_all_failures(fallback_manager):
    # Test all providers failing
    providers = [MockProvider(success=False) for _ in range(3)]

    for i, provider in enumerate(providers):
        fallback_manager.register_provider(f"model-{i}", provider)

    with pytest.raises(RuntimeError, match="All providers failed"):
        await fallback_manager.execute_with_fallback(
            "model-0", "generate", "test prompt"
        )

@pytest.mark.asyncio
async def test_fallback_manager_priority(fallback_manager):
    # Test provider priority
    high_priority = MockProvider(success=True)
    low_priority = MockProvider(success=True)

    fallback_manager.register_provider("gpt-4", low_priority, priority=0)
    fallback_manager.register_provider("gpt-4", high_priority, priority=1)

    result, provider = await fallback_manager.execute_with_fallback(
        "gpt-4", "generate", "test prompt"
    )

    assert provider == high_priority
    high_priority.generate.assert_called_once()
    low_priority.generate.assert_not_called()
