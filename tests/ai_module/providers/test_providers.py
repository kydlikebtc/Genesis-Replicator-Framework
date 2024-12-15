"""
Tests for AI model providers.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from genesis_replicator.ai_module.providers import (
    ClaudeProvider,
    GPTProvider,
    LlamaProvider
)

@pytest.fixture
def mock_anthropic():
    with patch('anthropic.AsyncAnthropic') as mock:
        mock_client = Mock()
        mock_client.messages.create = AsyncMock(return_value=Mock(content=[Mock(text="Test response")]))
        mock_client.count_tokens = Mock(return_value=10)
        mock.return_value = mock_client
        yield mock

@pytest.fixture
def mock_openai():
    with patch('openai.AsyncOpenAI') as mock:
        mock_client = Mock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=Mock(choices=[Mock(message=Mock(content="Test response"))])
        )
        mock.return_value = mock_client
        yield mock

@pytest.fixture
def mock_replicate():
    with patch('replicate.Client') as mock:
        mock_client = Mock()
        mock_client.async_run = AsyncMock(return_value=["Test response"])
        mock.return_value = mock_client
        yield mock

@pytest.mark.asyncio
async def test_claude_provider(mock_anthropic):
    provider = ClaudeProvider()
    config = {"api_key": "test_key"}
    await provider.initialize(config)

    # Test generation
    response = await provider.generate("Test prompt")
    assert response == "Test response"

    # Test token counting
    tokens = await provider.get_token_count("Test text")
    assert tokens == 10

    # Test response validation
    assert await provider.validate_response("Valid response")
    assert not await provider.validate_response("")

    # Test model info
    info = await provider.get_model_info()
    assert info["provider"] == "Anthropic"
    assert info["name"] == provider.model

@pytest.mark.asyncio
async def test_gpt_provider(mock_openai):
    provider = GPTProvider()
    config = {"api_key": "test_key"}
    await provider.initialize(config)

    # Test generation
    response = await provider.generate("Test prompt")
    assert response == "Test response"

    # Test token counting
    with patch('tiktoken.encoding_for_model') as mock_encoding:
        mock_encoding.return_value.encode.return_value = [1, 2, 3]
        tokens = await provider.get_token_count("Test text")
        assert tokens == 3

    # Test response validation
    assert await provider.validate_response("Valid response")
    assert not await provider.validate_response("")

    # Test model info
    info = await provider.get_model_info()
    assert info["provider"] == "OpenAI"
    assert info["name"] == provider.model

@pytest.mark.asyncio
async def test_llama_provider(mock_replicate):
    provider = LlamaProvider()
    config = {"api_key": "test_key"}
    await provider.initialize(config)

    # Test generation
    response = await provider.generate("Test prompt")
    assert response == "Test response"

    # Test token counting
    tokens = await provider.get_token_count("Test text of 20 chars")
    assert tokens == 5  # Approximately 4 chars per token

    # Test response validation
    assert await provider.validate_response("Valid response")
    assert not await provider.validate_response("")

    # Test model info
    info = await provider.get_model_info()
    assert info["provider"] == "Meta"
    assert "Llama" in info["name"]

@pytest.mark.asyncio
async def test_provider_initialization_errors():
    providers = [ClaudeProvider(), GPTProvider(), LlamaProvider()]

    for provider in providers:
        # Test missing API key
        with pytest.raises(ValueError, match=".*API key.*"):
            await provider.initialize({})

        # Test invalid config
        with pytest.raises(ValueError):
            await provider.initialize({"invalid": "config"})

@pytest.mark.asyncio
async def test_provider_generation_errors():
    providers = [ClaudeProvider(), GPTProvider(), LlamaProvider()]

    for provider in providers:
        # Test generation without initialization
        with pytest.raises(RuntimeError, match=".*not initialized.*"):
            await provider.generate("Test prompt")

        # Test token counting without initialization
        with pytest.raises(RuntimeError, match=".*not initialized.*"):
            await provider.get_token_count("Test text")

        # Test model info without initialization
        with pytest.raises(RuntimeError, match=".*not initialized.*"):
            await provider.get_model_info()
