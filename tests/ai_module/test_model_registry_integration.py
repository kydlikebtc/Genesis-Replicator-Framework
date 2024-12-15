"""
Integration tests for model registry with actual providers.
"""
import pytest
import asyncio
from genesis_replicator.ai_module.model_registry import ModelRegistry
from genesis_replicator.ai_module.providers.gpt import GPTProvider
from genesis_replicator.ai_module.providers.claude import ClaudeProvider
from genesis_replicator.ai_module.providers.llama import LlamaProvider
from genesis_replicator.ai_module.providers.mistral import MistralProvider
from genesis_replicator.ai_module.providers.gemini import GeminiProvider

@pytest.fixture
async def model_registry():
    registry = ModelRegistry()
    yield registry
    await registry.cleanup()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_gpt_integration(model_registry):
    """Test GPT provider integration."""
    config = {
        "model": "gpt-4",
        "max_tokens": 1000,
        "temperature": 0.7
    }

    await model_registry.register_provider(
        "gpt",
        GPTProvider(),
        config
    )

    response = await model_registry.generate_text(
        provider="gpt",
        prompt="Explain quantum computing in simple terms."
    )

    assert response is not None
    assert len(response) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_claude_integration(model_registry):
    """Test Claude provider integration."""
    config = {
        "model": "claude-3-opus",
        "max_tokens": 1000,
        "temperature": 0.7
    }

    await model_registry.register_provider(
        "claude",
        ClaudeProvider(),
        config
    )

    response = await model_registry.generate_text(
        provider="claude",
        prompt="Explain the concept of neural networks."
    )

    assert response is not None
    assert len(response) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_llama_integration(model_registry):
    """Test LLaMA provider integration."""
    config = {
        "model": "llama-2-70b",
        "max_tokens": 1000,
        "temperature": 0.7
    }

    await model_registry.register_provider(
        "llama",
        LlamaProvider(),
        config
    )

    response = await model_registry.generate_text(
        provider="llama",
        prompt="Describe the process of photosynthesis."
    )

    assert response is not None
    assert len(response) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_mistral_integration(model_registry):
    """Test Mistral provider integration."""
    config = {
        "model": "mistral-large",
        "max_tokens": 1000,
        "temperature": 0.7
    }

    await model_registry.register_provider(
        "mistral",
        MistralProvider(),
        config
    )

    response = await model_registry.generate_text(
        provider="mistral",
        prompt="Explain how blockchain technology works."
    )

    assert response is not None
    assert len(response) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_integration(model_registry):
    """Test Gemini provider integration."""
    config = {
        "model": "gemini-pro",
        "max_tokens": 1000,
        "temperature": 0.7
    }

    await model_registry.register_provider(
        "gemini",
        GeminiProvider(),
        config
    )

    response = await model_registry.generate_text(
        provider="gemini",
        prompt="Describe the process of machine learning."
    )

    assert response is not None
    assert len(response) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_fallback_chain(model_registry):
    """Test fallback chain across multiple providers."""
    # Register providers with fallbacks
    providers = [
        ("gpt", GPTProvider(), "claude"),
        ("claude", ClaudeProvider(), "mistral"),
        ("mistral", MistralProvider(), "gemini"),
        ("gemini", GeminiProvider(), None)
    ]

    for name, provider, fallback in providers:
        await model_registry.register_provider(
            name,
            provider,
            {"model": f"{name}-model"}
        )
        if fallback:
            await model_registry.set_fallback(name, fallback)

    # Test fallback chain
    response = await model_registry.generate_text(
        provider="gpt",
        prompt="Test fallback chain"
    )

    assert response is not None
    assert len(response) > 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_multi_provider(model_registry):
    """Test concurrent requests across multiple providers."""
    providers = {
        "gpt": GPTProvider(),
        "claude": ClaudeProvider(),
        "mistral": MistralProvider(),
        "gemini": GeminiProvider()
    }

    # Register all providers
    for name, provider in providers.items():
        await model_registry.register_provider(
            name,
            provider,
            {"model": f"{name}-model"}
        )

    async def generate(provider: str):
        return await model_registry.generate_text(
            provider=provider,
            prompt=f"Test prompt for {provider}"
        )

    # Run concurrent requests
    tasks = [
        generate(provider)
        for provider in providers.keys()
        for _ in range(2)  # 2 requests per provider
    ]

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    successful = [r for r in responses if isinstance(r, str)]

    assert len(successful) > 0  # At least some requests should succeed
