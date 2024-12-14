"""
State Persistence Manager for maintaining system state.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class StatePersistenceManager:
    """Manages persistence of system state."""

    def __init__(self, state_dir: str = "state"):
        """Initialize the state persistence manager.

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state_lock = asyncio.Lock()
        self._state_cache: Dict[str, Any] = {}

    async def save_state(self, component: str, state: Dict) -> bool:
        """Save component state to disk.

        Args:
            component: Component identifier
            state: State data to save

        Returns:
            Success status
        """
        async with self._state_lock:
            try:
                state_file = self.state_dir / f"{component}.json"

                # Update cache
                self._state_cache[component] = state

                # Write to disk
                with open(state_file, "w") as f:
                    json.dump(state, f, indent=2)

                return True

            except Exception as e:
                logger.error(f"Failed to save state for {component}: {str(e)}")
                return False

    async def load_state(self, component: str) -> Optional[Dict]:
        """Load component state from disk.

        Args:
            component: Component identifier

        Returns:
            State data or None if not found
        """
        # Check cache first
        if component in self._state_cache:
            return self._state_cache[component]

        async with self._state_lock:
            try:
                state_file = self.state_dir / f"{component}.json"
                if not state_file.exists():
                    return None

                with open(state_file) as f:
                    state = json.load(f)

                # Update cache
                self._state_cache[component] = state
                return state

            except Exception as e:
                logger.error(f"Failed to load state for {component}: {str(e)}")
                return None

    async def delete_state(self, component: str) -> bool:
        """Delete component state from disk.

        Args:
            component: Component identifier

        Returns:
            Success status
        """
        async with self._state_lock:
            try:
                state_file = self.state_dir / f"{component}.json"
                if state_file.exists():
                    state_file.unlink()

                # Remove from cache
                self._state_cache.pop(component, None)
                return True

            except Exception as e:
                logger.error(f"Failed to delete state for {component}: {str(e)}")
                return False

    async def list_components(self) -> list:
        """List all components with saved state.

        Returns:
            List of component identifiers
        """
        components = []
        for state_file in self.state_dir.glob("*.json"):
            components.append(state_file.stem)
        return components

    async def clear_cache(self) -> None:
        """Clear the state cache."""
        async with self._state_lock:
            self._state_cache.clear()
