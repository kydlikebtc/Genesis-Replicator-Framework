"""
Recovery Manager for handling system recovery procedures.
"""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

class RecoveryStatus(Enum):
    """Status of recovery procedure."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class RecoveryProcedure:
    """Represents a recovery procedure."""

    def __init__(
        self,
        name: str,
        handler: Callable,
        dependencies: Optional[List[str]] = None,
        timeout: int = 300
    ):
        """Initialize recovery procedure.

        Args:
            name: Procedure name
            handler: Async function to execute
            dependencies: Required procedures
            timeout: Maximum execution time in seconds
        """
        self.name = name
        self.handler = handler
        self.dependencies = dependencies or []
        self.timeout = timeout
        self.status = RecoveryStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error: Optional[str] = None

class RecoveryManager:
    """Manages system recovery procedures."""

    def __init__(self):
        """Initialize the recovery manager."""
        self._procedures: Dict[str, RecoveryProcedure] = {}
        self._recovery_lock = asyncio.Lock()

    def register_procedure(
        self,
        name: str,
        handler: Callable,
        dependencies: Optional[List[str]] = None,
        timeout: int = 300
    ) -> None:
        """Register a recovery procedure.

        Args:
            name: Procedure name
            handler: Async function to execute
            dependencies: Required procedures
            timeout: Maximum execution time in seconds
        """
        if name in self._procedures:
            raise ValueError(f"Procedure {name} already registered")

        procedure = RecoveryProcedure(
            name=name,
            handler=handler,
            dependencies=dependencies,
            timeout=timeout
        )
        self._procedures[name] = procedure

    async def execute_procedure(self, name: str) -> bool:
        """Execute a recovery procedure.

        Args:
            name: Procedure name

        Returns:
            Success status
        """
        if name not in self._procedures:
            raise ValueError(f"Procedure {name} not found")

        procedure = self._procedures[name]

        # Check dependencies
        for dep in procedure.dependencies:
            if dep not in self._procedures:
                raise ValueError(f"Dependency {dep} not found")
            if self._procedures[dep].status != RecoveryStatus.COMPLETED:
                raise ValueError(f"Dependency {dep} not completed")

        async with self._recovery_lock:
            try:
                procedure.status = RecoveryStatus.IN_PROGRESS
                procedure.start_time = datetime.now()

                # Execute with timeout
                try:
                    await asyncio.wait_for(
                        procedure.handler(),
                        timeout=procedure.timeout
                    )
                    procedure.status = RecoveryStatus.COMPLETED
                    return True

                except asyncio.TimeoutError:
                    procedure.error = "Procedure timed out"
                    procedure.status = RecoveryStatus.FAILED
                    return False

            except Exception as e:
                procedure.error = str(e)
                procedure.status = RecoveryStatus.FAILED
                logger.error(f"Recovery procedure failed: {str(e)}")
                return False

            finally:
                procedure.end_time = datetime.now()

    async def execute_all(self) -> bool:
        """Execute all recovery procedures in dependency order.

        Returns:
            Overall success status
        """
        # Build dependency graph
        graph = {name: proc.dependencies for name, proc in self._procedures.items()}

        # Topological sort
        visited = set()
        temp = set()
        order = []

        def visit(name: str):
            if name in temp:
                raise ValueError("Circular dependency detected")
            if name in visited:
                return

            temp.add(name)
            for dep in graph[name]:
                visit(dep)
            temp.remove(name)
            visited.add(name)
            order.append(name)

        try:
            for name in graph:
                if name not in visited:
                    visit(name)
        except ValueError as e:
            logger.error(f"Dependency resolution failed: {str(e)}")
            return False

        # Execute procedures in order
        success = True
        for name in order:
            if not await self.execute_procedure(name):
                success = False
                break

        return success

    def get_procedure_status(self, name: str) -> RecoveryStatus:
        """Get status of a recovery procedure.

        Args:
            name: Procedure name

        Returns:
            Current status
        """
        if name not in self._procedures:
            raise ValueError(f"Procedure {name} not found")
        return self._procedures[name].status

    def list_procedures(self) -> Dict[str, RecoveryStatus]:
        """List all procedures and their status.

        Returns:
            Dictionary of procedure names and status
        """
        return {name: proc.status for name, proc in self._procedures.items()}
