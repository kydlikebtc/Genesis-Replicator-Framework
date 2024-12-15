"""
Tests for model registry with multi-provider support.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from genesis_replicator.ai_module.model_registry import ModelRegistry
from genesis_replicator.ai_module.providers.base import ModelProviderInterface

@pytest.fixture
async def model_registry():
    registry = ModelRegistry()
    yield registry
    await registry.cleanup()

@pytest.fixture
def mock_provider():
    provider = Mock(spec=ModelProviderInterface)
    provider.initialize = AsyncMock()
    provider.generate_text = AsyncMock(return_value="Generated text")
    provider.get_model_info = AsyncMock(return_value={
        "name": "test-model",
        "provider": "test",
        "capabilities": ["text"]
    })
    return provider

@pytest.mark.asyncio
async def test_provider_registration(model_registry, mock_provider):
    """Test provider registration and initialization."""
    config = {
        "api_key": "test_key",
        "model": "test-model",
        "max_tokens": 1000
    }

    await model_registry.register_provider("test_provider", mock_provider, config)

    mock_provider.initialize.assert_called_once_with(config)
    assert "test_provider" in model_registry.get_providers()

@pytest.mark.asyncio
async def test_model_generation(model_registry, mock_provider):
    """Test text generation with registered provider."""
    await model_registry.register_provider("test_provider", mock_provider, {})

    response = await model_registry.generate_text(
        provider="test_provider",
        prompt="Test prompt",
        max_tokens=100
    )

    assert response == "Generated text"
    mock_provider.generate_text.assert_called_once()

@pytest.mark.asyncio
async def test_provider_fallback(model_registry):
    """Test provider fallback mechanism."""
    primary_provider = Mock(spec=ModelProviderInterface)
    primary_provider.initialize = AsyncMock()
    primary_provider.generate_text = AsyncMock(side_effect=Exception("API Error"))

    fallback_provider = Mock(spec=ModelProviderInterface)
    fallback_provider.initialize = AsyncMock()
    fallback_provider.generate_text = AsyncMock(return_value="Fallback response")

    await model_registry.register_provider("primary", primary_provider, {})
    await model_registry.register_provider("fallback", fallback_provider, {})
    await model_registry.set_fallback("primary", "fallback")

    response = await model_registry.generate_text(
        provider="primary",
        prompt="Test prompt"
    )

    assert response == "Fallback response"
    primary_provider.generate_text.assert_called_once()
    fallback_provider.generate_text.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limiting(model_registry, mock_provider):
    """Test rate limiting functionality."""
    config = {
        "rate_limits": {
            "requests_per_minute": 2,
            "tokens_per_minute": 1000
        }
    }

    await model_registry.register_provider("test_provider", mock_provider, config)

    # Should succeed
    await model_registry.generate_text(
        provider="test_provider",
        prompt="Test 1"
    )
    await model_registry.generate_text(
        provider="test_provider",
        prompt="Test 2"
    )

    # Should be rate limited
    with pytest.raises(Exception, match="Rate limit exceeded"):
        await model_registry.generate_text(
            provider="test_provider",
            prompt="Test 3"
        )

@pytest.mark.asyncio
async def test_model_info(model_registry, mock_provider):
    """Test model information retrieval."""
    await model_registry.register_provider("test_provider", mock_provider, {})

    info = await model_registry.get_model_info("test_provider")
    assert info["name"] == "test-model"
    assert info["provider"] == "test"
    assert "text" in info["capabilities"]

@pytest.mark.asyncio
async def test_provider_cleanup(model_registry, mock_provider):
    """Test provider cleanup on registry shutdown."""
    mock_provider.cleanup = AsyncMock()

    await model_registry.register_provider("test_provider", mock_provider, {})
    await model_registry.cleanup()

    mock_provider.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_concurrent_requests(model_registry, mock_provider):
    """Test concurrent request handling."""
    await model_registry.register_provider("test_provider", mock_provider, {})

    async def generate():
        return await model_registry.generate_text(
            provider="test_provider",
            prompt="Test prompt"
        )

    # Run multiple requests concurrently
    tasks = [generate() for _ in range(5)]
    responses = await asyncio.gather(*tasks)

    assert len(responses) == 5
    assert all(response == "Generated text" for response in responses)
    assert mock_provider.generate_text.call_count == 5
