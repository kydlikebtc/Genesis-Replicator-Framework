"""
Memory management and optimization for Genesis Replicator Framework.
"""
import asyncio
import gc
import sys
import psutil
import weakref
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

@dataclass
class MemoryStats:
    """Memory statistics."""
    total: int
    available: int
    used: int
    cached: int

class MemoryManager:
    """Manages memory optimization."""

    def __init__(
        self,
        max_cache_size: int = 1024 * 1024 * 1024,  # 1GB
        gc_threshold: float = 0.85  # 85% memory usage
    ):
        """Initialize memory manager.

        Args:
            max_cache_size: Maximum cache size in bytes
            gc_threshold: Memory usage threshold for GC
        """
        self._max_cache_size = max_cache_size
        self._gc_threshold = gc_threshold
        self._cache: Dict[str, Any] = {}
        self._cache_size = 0
        self._weak_refs: Dict[str, weakref.ref] = {}
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)

    async def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics.

        Returns:
            MemoryStats: Memory statistics
        """
        mem = psutil.virtual_memory()
        return MemoryStats(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            cached=mem.cached
        )

    async def cache_object(
        self,
        key: str,
        obj: Any,
        weak: bool = False
    ) -> bool:
        """Cache object in memory.

        Args:
            key: Cache key
            obj: Object to cache
            weak: Use weak reference

        Returns:
            bool: Success status
        """
        async with self._lock:
            # Check memory usage
            if await self._should_collect_garbage():
                await self.collect_garbage()

            # Store object
            if weak:
                self._weak_refs[key] = weakref.ref(obj)
            else:
                self._cache[key] = obj
                self._cache_size += self._estimate_size(obj)

            return True

    async def get_cached_object(self, key: str) -> Optional[Any]:
        """Get cached object.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached object if exists
        """
        # Check weak refs first
        if key in self._weak_refs:
            obj = self._weak_refs[key]()
            if obj is not None:
                return obj
            del self._weak_refs[key]

        return self._cache.get(key)

    async def clear_cache(self) -> None:
        """Clear memory cache."""
        async with self._lock:
            self._cache.clear()
            self._weak_refs.clear()
            self._cache_size = 0

    async def collect_garbage(self) -> None:
        """Force garbage collection."""
        gc.collect()
        self._logger.info("Garbage collection completed")

    async def _should_collect_garbage(self) -> bool:
        """Check if garbage collection needed.

        Returns:
            bool: True if GC needed
        """
        stats = await self.get_memory_stats()
        usage = stats.used / stats.total
        return usage > self._gc_threshold

    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes.

        Args:
            obj: Object to measure

        Returns:
            int: Estimated size in bytes
        """
        return sys.getsizeof(obj)
