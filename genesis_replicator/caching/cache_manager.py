"""
Cache manager for handling distributed caching operations.
"""
import asyncio
import logging
from typing import Any, Dict, Optional, List, Set, Tuple
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger(__name__)

class CacheEntry:
    """Represents a cached item with metadata."""
    def __init__(
        self,
        key: str,
        value: Any,
        ttl: int,
        tags: Set[str]
    ):
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl)
        self.tags = tags
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return datetime.now() > self.expires_at

    def update_access(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now()

class CacheManager:
    """Manages distributed caching operations."""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        cleanup_interval: int = 300
    ):
        """Initialize cache manager.

        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default time-to-live in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._tag_index: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info("Cache manager initialized")

    async def start(self) -> None:
        """Start cache manager and cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Cache manager started")

    async def stop(self) -> None:
        """Stop cache manager and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache manager stopped")

    async def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        async with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return default

            if entry.is_expired():
                await self._remove_entry(key)
                return default

            entry.update_access()
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            tags: Optional tags for grouping entries
        """
        ttl = ttl or self._default_ttl
        tags = tags or set()

        async with self._lock:
            # Check size limit
            if len(self._cache) >= self._max_size:
                await self._evict_entries()

            # Create entry
            entry = CacheEntry(key, value, ttl, tags)
            self._cache[key] = entry

            # Update tag index
            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(key)

    async def invalidate(
        self,
        key: str
    ) -> None:
        """Invalidate a cache entry.

        Args:
            key: Cache key
        """
        async with self._lock:
            await self._remove_entry(key)

    async def invalidate_by_tag(
        self,
        tag: str
    ) -> None:
        """Invalidate all entries with given tag.

        Args:
            tag: Tag to invalidate
        """
        async with self._lock:
            keys = self._tag_index.get(tag, set()).copy()
            for key in keys:
                await self._remove_entry(key)

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for e in self._cache.values() if e.is_expired())
            total_tags = len(self._tag_index)

            access_stats = {
                "total_hits": sum(e.access_count for e in self._cache.values()),
                "entries_by_access": {
                    "high": sum(1 for e in self._cache.values() if e.access_count > 100),
                    "medium": sum(1 for e in self._cache.values() if 10 < e.access_count <= 100),
                    "low": sum(1 for e in self._cache.values() if e.access_count <= 10)
                }
            }

            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "total_tags": total_tags,
                "access_stats": access_stats,
                "memory_usage": self._estimate_memory_usage()
            }

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache.

        Returns:
            Estimated memory usage in bytes
        """
        total_size = 0
        for entry in self._cache.values():
            # Estimate size of key and value
            total_size += len(entry.key.encode())
            total_size += len(json.dumps(entry.value).encode())
            # Add overhead for metadata
            total_size += sum(len(tag.encode()) for tag in entry.tags)
            total_size += 64  # Approximate size of timestamps and counters
        return total_size

    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")

    async def _cleanup_expired(self) -> None:
        """Clean up expired cache entries."""
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                await self._remove_entry(key)

    async def _evict_entries(self) -> None:
        """Evict entries when cache is full."""
        # First remove expired entries
        await self._cleanup_expired()

        # If still need to evict, use LRU strategy
        if len(self._cache) >= self._max_size:
            entries = sorted(
                self._cache.items(),
                key=lambda x: (x[1].last_accessed, -x[1].access_count)
            )
            # Remove 10% of entries
            to_remove = entries[:max(1, len(entries) // 10)]
            for key, _ in to_remove:
                await self._remove_entry(key)

    async def _remove_entry(self, key: str) -> None:
        """Remove a cache entry and update indexes.

        Args:
            key: Cache key to remove
        """
        if key in self._cache:
            entry = self._cache[key]
            # Remove from tag index
            for tag in entry.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(key)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]
            # Remove entry
            del self._cache[key]
