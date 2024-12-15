"""
Tests for AI model rate limiter.
"""
import pytest
import asyncio
from genesis_replicator.ai_module.rate_limiter import RateLimiter

@pytest.fixture
def rate_limiter():
    return RateLimiter()

@pytest.mark.asyncio
async def test_rate_limiter_basic(rate_limiter):
    # Test basic rate limiting
    await rate_limiter.acquire("openai")
    assert rate_limiter.get_remaining_calls("openai") == 59

@pytest.mark.asyncio
async def test_rate_limiter_provider_limits(rate_limiter):
    # Test different provider limits
    providers = ["openai", "anthropic", "replicate", "mistral", "google"]
    for provider in providers:
        await rate_limiter.acquire(provider)
        limits = rate_limiter._provider_limits[provider]
        assert rate_limiter.get_remaining_calls(provider) == limits["calls_per_minute"] - 1

@pytest.mark.asyncio
async def test_rate_limiter_exceeds_limit(rate_limiter):
    # Test exceeding rate limit
    provider = "openai"
    limit = rate_limiter._provider_limits[provider]["calls_per_minute"]

    # Make calls up to limit
    for _ in range(limit):
        await rate_limiter.acquire(provider)

    # Next call should raise error
    with pytest.raises(RuntimeError, match="Rate limit exceeded"):
        await rate_limiter.acquire(provider)

@pytest.mark.asyncio
async def test_rate_limiter_concurrent_access():
    limiter = RateLimiter()
    provider = "openai"

    async def make_call():
        await limiter.acquire(provider)
        await asyncio.sleep(0.1)  # Simulate API call

    # Test concurrent access
    tasks = [make_call() for _ in range(5)]
    await asyncio.gather(*tasks)

    assert limiter.get_remaining_calls(provider) == 55  # 60 - 5
