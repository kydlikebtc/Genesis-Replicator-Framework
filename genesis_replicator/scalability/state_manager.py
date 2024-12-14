"""
State Manager implementation for Genesis Replicator Framework.

Handles state replication and consistency across cluster nodes.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID
import json
import hashlib

logger = logging.getLogger(__name__)

class StateManager:
    """Manages state replication and consistency across the cluster."""

    def __init__(self):
        """Initialize the state manager."""
        self._state: Dict[str, Any] = {}
        self._state_versions: Dict[str, int] = {}
        self._state_hashes: Dict[str, str] = {}
        self._replicas: Dict[UUID, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the state manager service."""
        logger.info("Starting state manager service...")

    async def stop(self) -> None:
        """Stop the state manager service."""
        logger.info("Stopping state manager service...")

    async def set_state(self, key: str, value: Any, node_id: UUID) -> None:
        """Set state value with versioning and replication."""
        async with self._lock:
            # Update version
            version = self._state_versions.get(key, 0) + 1
            self._state_versions[key] = version

            # Update state
            self._state[key] = value

            # Calculate new hash
            state_hash = self._calculate_hash(value)
            self._state_hashes[key] = state_hash

            # Track replica
            if node_id not in self._replicas:
                self._replicas[node_id] = set()
            self._replicas[node_id].add(key)

            logger.info(f"Updated state for key {key} (version {version})")

    async def get_state(self, key: str) -> Optional[Any]:
        """Get state value."""
        async with self._lock:
            return self._state.get(key)

    async def get_version(self, key: str) -> int:
        """Get current version of a state key."""
        async with self._lock:
            return self._state_versions.get(key, 0)

    async def verify_consistency(self, key: str, value: Any) -> bool:
        """Verify state consistency using hash comparison."""
        async with self._lock:
            if key not in self._state_hashes:
                return False
            current_hash = self._calculate_hash(value)
            return current_hash == self._state_hashes[key]

    async def remove_replica(self, node_id: UUID) -> None:
        """Remove a node's replicas when it leaves the cluster."""
        async with self._lock:
            if node_id in self._replicas:
                del self._replicas[node_id]
                logger.info(f"Removed replicas for node {node_id}")

    def _calculate_hash(self, value: Any) -> str:
        """Calculate hash for state value."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, sort_keys=True)
        return hashlib.sha256(str(value).encode()).hexdigest()
