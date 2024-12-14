"""
Rate Limiter Module for API Gateway

Implements rate limiting functionality.
"""
from typing import Dict, Optional
import logging
from datetime import datetime, timedelta
import redis
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int
    burst_size: Optional[int] = None
    key_prefix: str = "rate_limit"

class RateLimiter:
    """Implements token bucket rate limiting."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_config: Optional[RateLimitConfig] = None
    ):
        """
        Initialize the RateLimiter.

        Args:
            redis_url: Redis connection URL
            default_config: Default rate limit configuration
        """
        self.redis = redis.from_url(redis_url)
        self.default_config = default_config or RateLimitConfig(
            requests_per_minute=60
        )
        logger.info("Rate Limiter initialized")

    def _get_key(self, identifier: str, key_prefix: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"{key_prefix}:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        config: Optional[RateLimitConfig] = None
    ) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address)
            config: Optional custom rate limit configuration

        Returns:
            True if request is allowed, False otherwise
        """
        cfg = config or self.default_config
        key = self._get_key(identifier, cfg.key_prefix)

        try:
            current = self.redis.get(key)
            if current is None:
                # First request
                self.redis.setex(
                    key,
                    60,  # 1 minute expiry
                    1
                )
                return True

            count = int(current)
            if count >= cfg.requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded for {identifier}"
                )
                return False


            self.redis.incr(key)
            return True

        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            # Fail open if Redis is unavailable
            return True

    def reset_rate_limit(self, identifier: str) -> None:
        """
        Reset rate limit for an identifier.

        Args:
            identifier: Unique identifier to reset
        """
        key = self._get_key(identifier, self.default_config.key_prefix)
        try:
            self.redis.delete(key)
            logger.info(f"Reset rate limit for {identifier}")
        except redis.RedisError as e:
            logger.error(f"Failed to reset rate limit: {str(e)}")

    def get_remaining_requests(
        self,
        identifier: str,
        config: Optional[RateLimitConfig] = None
    ) -> int:
        """
        Get remaining allowed requests.

        Args:
            identifier: Unique identifier
            config: Optional custom rate limit configuration

        Returns:
            Number of remaining allowed requests
        """
        cfg = config or self.default_config
        key = self._get_key(identifier, cfg.key_prefix)

        try:
            current = self.redis.get(key)
            if current is None:
                return cfg.requests_per_minute

            count = int(current)
            return max(0, cfg.requests_per_minute - count)

        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            return 0
