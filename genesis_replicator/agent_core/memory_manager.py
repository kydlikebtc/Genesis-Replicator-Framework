"""
Memory Manager Module

This module manages agent memory allocation and retrieval in the Genesis Replicator Framework.
It handles both short-term and long-term memory storage with proper resource management.
"""
from typing import Dict, Optional, Any, List
import logging
from dataclasses import dataclass
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    """Data class for storing memory entries"""
    data: Any
    timestamp: datetime
    tags: List[str]
    priority: int = 0

class MemoryManager:
    """
    Manages agent memory allocation and retrieval with support for different memory types.

    Attributes:
        short_term_memory (Dict): Short-term memory storage
        long_term_memory (Dict): Long-term memory storage
        memory_limits (Dict): Memory size limits
    """

    def __init__(self, short_term_limit: int = 1000, long_term_limit: int = 10000):
        """
        Initialize the MemoryManager.

        Args:
            short_term_limit (int): Maximum entries in short-term memory
            long_term_limit (int): Maximum entries in long-term memory
        """
        self.short_term_memory: Dict[str, Dict[str, MemoryEntry]] = {}
        self.long_term_memory: Dict[str, Dict[str, MemoryEntry]] = {}
        self.memory_limits = {
            "short": short_term_limit,
            "long": long_term_limit
        }
        logger.info("MemoryManager initialized")

    def allocate_memory(
        self,
        agent_id: str,
        key: str,
        data: Any,
        memory_type: str = "short",
        tags: List[str] = None,
        priority: int = 0
    ) -> bool:
        """
        Allocate memory for an agent.

        Args:
            agent_id (str): Agent identifier
            key (str): Memory entry key
            data (Any): Data to store
            memory_type (str): Memory type ("short" or "long")
            tags (List[str]): Tags for categorizing memory
            priority (int): Priority level for memory management

        Returns:
            bool: Success status

        Raises:
            ValueError: If invalid memory type or memory limit exceeded
        """
        try:
            if memory_type not in ["short", "long"]:
                raise ValueError(f"Invalid memory type: {memory_type}")

            memory_store = (
                self.short_term_memory if memory_type == "short"
                else self.long_term_memory
            )

            # Initialize agent memory if not exists
            if agent_id not in memory_store:
                memory_store[agent_id] = {}

            # Check memory limits
            if len(memory_store[agent_id]) >= self.memory_limits[memory_type]:
                self._cleanup_memory(agent_id, memory_type)

            # Create memory entry
            entry = MemoryEntry(
                data=data,
                timestamp=datetime.now(),
                tags=tags or [],
                priority=priority
            )

            memory_store[agent_id][key] = entry
            logger.info(f"Memory allocated for agent {agent_id}: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to allocate memory for agent {agent_id}: {str(e)}")
            return False

    def retrieve_memory(
        self,
        agent_id: str,
        key: str,
        memory_type: str = "short"
    ) -> Optional[Any]:
        """
        Retrieve memory data for an agent.

        Args:
            agent_id (str): Agent identifier
            key (str): Memory entry key
            memory_type (str): Memory type ("short" or "long")

        Returns:
            Optional[Any]: Retrieved data or None if not found
        """
        try:
            memory_store = (
                self.short_term_memory if memory_type == "short"
                else self.long_term_memory
            )

            if agent_id not in memory_store or key not in memory_store[agent_id]:
                return None

            entry = memory_store[agent_id][key]
            logger.debug(f"Memory retrieved for agent {agent_id}: {key}")
            return entry.data

        except Exception as e:
            logger.error(f"Error retrieving memory for agent {agent_id}: {str(e)}")
            return None

    def search_memory(
        self,
        agent_id: str,
        tags: List[str] = None,
        memory_type: str = "both"
    ) -> Dict[str, Any]:
        """
        Search memory entries by tags.

        Args:
            agent_id (str): Agent identifier
            tags (List[str]): Tags to search for
            memory_type (str): Memory type to search ("short", "long", or "both")

        Returns:
            Dict[str, Any]: Matching memory entries
        """
        try:
            results = {}

            if memory_type in ["short", "both"]:
                self._search_memory_store(
                    agent_id, tags, self.short_term_memory, results
                )

            if memory_type in ["long", "both"]:
                self._search_memory_store(
                    agent_id, tags, self.long_term_memory, results
                )

            return results

        except Exception as e:
            logger.error(f"Error searching memory for agent {agent_id}: {str(e)}")
            return {}

    def clear_memory(
        self,
        agent_id: str,
        memory_type: str = "short"
    ) -> bool:
        """
        Clear all memory entries for an agent.

        Args:
            agent_id (str): Agent identifier
            memory_type (str): Memory type to clear

        Returns:
            bool: Success status
        """
        try:
            if memory_type == "short":
                self.short_term_memory.pop(agent_id, None)
            elif memory_type == "long":
                self.long_term_memory.pop(agent_id, None)
            else:
                self.short_term_memory.pop(agent_id, None)
                self.long_term_memory.pop(agent_id, None)

            logger.info(f"Memory cleared for agent {agent_id}: {memory_type}")
            return True

        except Exception as e:
            logger.error(f"Error clearing memory for agent {agent_id}: {str(e)}")
            return False

    def _cleanup_memory(self, agent_id: str, memory_type: str) -> None:
        """
        Clean up old memory entries based on priority and age.

        Args:
            agent_id (str): Agent identifier
            memory_type (str): Memory type to clean up
        """
        try:
            memory_store = (
                self.short_term_memory if memory_type == "short"
                else self.long_term_memory
            )

            if agent_id not in memory_store:
                return

            entries = list(memory_store[agent_id].items())
            entries.sort(
                key=lambda x: (x[1].priority, x[1].timestamp)
            )

            # Remove oldest, lowest priority entries
            target_size = self.memory_limits[memory_type] * 0.8  # Keep 80% capacity
            while len(memory_store[agent_id]) > target_size:
                key, _ = entries.pop(0)
                del memory_store[agent_id][key]

        except Exception as e:
            logger.error(f"Error during memory cleanup for agent {agent_id}: {str(e)}")

    def _search_memory_store(
        self,
        agent_id: str,
        tags: List[str],
        memory_store: Dict,
        results: Dict
    ) -> None:
        """
        Search a specific memory store for matching entries.

        Args:
            agent_id (str): Agent identifier
            tags (List[str]): Tags to search for
            memory_store (Dict): Memory store to search
            results (Dict): Dictionary to store results
        """
        if not tags or agent_id not in memory_store:
            return

        for key, entry in memory_store[agent_id].items():
            if any(tag in entry.tags for tag in tags):
                results[key] = entry.data
