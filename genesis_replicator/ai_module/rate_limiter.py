"""
Rate limiter for AI model API calls.
"""
import asyncio
import time
from typing import Dict, Optional

class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self):
        """Initialize rate limiter."""
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_call: Dict[str, float] = {}
        self._call_counts: Dict[str, int] = {}
        self._provider_limits = {
            "openai": {"calls_per_minute": 60, "min_interval": 1.0},
            "anthropic": {"calls_per_minute": 50, "min_interval": 1.2},
            "replicate": {"calls_per_minute": 40, "min_interval": 1.5},
            "mistral": {"calls_per_minute": 45, "min_interval": 1.3},
            "google": {"calls_per_minute": 55, "min_interval": 1.1}
        }

    async def acquire(self, provider: str) -> None:
        """Acquire permission to make an API call.

        Args:
            provider: Provider name

        Raises:
            RuntimeError: If rate limit exceeded
        """
        if provider not in self._locks:
            self._locks[provider] = asyncio.Lock()
            self._last_call[provider] = 0
            self._call_counts[provider] = 0

        async with self._locks[provider]:
            current_time = time.time()
            elapsed = current_time - self._last_call[provider]

            # Reset counter if a minute has passed
            if elapsed >= 60:
                self._call_counts[provider] = 0
                self._last_call[provider] = current_time

            # Check rate limits
            limits = self._provider_limits.get(provider, {"calls_per_minute": 30, "min_interval": 2.0})
            if self._call_counts[provider] >= limits["calls_per_minute"]:
                raise RuntimeError(f"Rate limit exceeded for {provider}")

            # Enforce minimum interval
            if elapsed < limits["min_interval"]:
                await asyncio.sleep(limits["min_interval"] - elapsed)

            self._call_counts[provider] += 1
            self._last_call[provider] = time.time()

    def get_remaining_calls(self, provider: str) -> int:
        """Get remaining API calls for the current minute.

        Args:
            provider: Provider name

        Returns:
            Number of remaining calls
        """
        if provider not in self._call_counts:
            return self._provider_limits.get(provider, {"calls_per_minute": 30})["calls_per_minute"]

        limits = self._provider_limits.get(provider, {"calls_per_minute": 30})
        return max(0, limits["calls_per_minute"] - self._call_counts[provider])
