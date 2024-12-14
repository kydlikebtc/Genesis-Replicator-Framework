"""
Priority Manager Module

This module manages priority levels and scheduling for decision-making processes
in the Genesis Replicator Framework.
"""
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import heapq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PriorityTask:
    """Represents a task with priority information."""
    id: str
    priority: int
    created_at: datetime
    deadline: Optional[datetime]
    context: Dict[str, Any]
    status: str = "pending"

class PriorityManager:
    """Manages task priorities and scheduling in the decision engine."""

    def __init__(self):
        """Initialize the PriorityManager."""
        self.task_queue: List[Tuple[int, datetime, str]] = []  # (priority, timestamp, task_id)
        self.tasks: Dict[str, PriorityTask] = {}
        self.priority_levels: Dict[str, int] = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }
        logger.info("Priority Manager initialized")

    def add_task(
        self,
        task_id: str,
        priority_level: str,
        context: Dict[str, Any],
        deadline: Optional[datetime] = None
    ) -> None:
        """
        Add a new task with priority information.

        Args:
            task_id: Unique identifier for the task
            priority_level: Priority level (critical/high/medium/low)
            context: Task context and parameters
            deadline: Optional deadline for task completion
        """
        if task_id in self.tasks:
            raise ValueError(f"Task '{task_id}' already exists")

        if priority_level not in self.priority_levels:
            raise ValueError(f"Invalid priority level: {priority_level}")

        priority = self.priority_levels[priority_level]
        created_at = datetime.now()

        task = PriorityTask(
            id=task_id,
            priority=priority,
            created_at=created_at,
            deadline=deadline,
            context=context
        )

        self.tasks[task_id] = task
        heapq.heappush(self.task_queue, (priority, created_at, task_id))
        logger.info(f"Added task: {task_id} with priority {priority_level}")

    def get_next_task(self) -> Optional[PriorityTask]:
        """
        Get the highest priority task from the queue.

        Returns:
            The next task to process, or None if queue is empty
        """
        while self.task_queue:
            _, _, task_id = heapq.heappop(self.task_queue)
            task = self.tasks.get(task_id)

            if task and task.status == "pending":
                return task

        return None

    def update_task_status(self, task_id: str, status: str) -> None:
        """
        Update the status of a task.

        Args:
            task_id: ID of the task to update
            status: New status (pending/processing/completed/failed)
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        self.tasks[task_id].status = status
        logger.info(f"Updated task {task_id} status to: {status}")

    def get_task_status(self, task_id: str) -> str:
        """
        Get the current status of a task.

        Args:
            task_id: ID of the task

        Returns:
            Current status of the task
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        return self.tasks[task_id].status

    def remove_task(self, task_id: str) -> None:
        """
        Remove a task from the system.

        Args:
            task_id: ID of the task to remove
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        del self.tasks[task_id]
        # Note: Task will be filtered out in get_next_task
        logger.info(f"Removed task: {task_id}")

    def get_overdue_tasks(self) -> List[PriorityTask]:
        """
        Get all tasks that have passed their deadline.

        Returns:
            List of overdue tasks
        """
        now = datetime.now()
        return [
            task for task in self.tasks.values()
            if task.deadline and task.deadline < now and task.status == "pending"
        ]

    def reprioritize_task(self, task_id: str, new_priority_level: str) -> None:
        """
        Update the priority of an existing task.

        Args:
            task_id: ID of the task to update
            new_priority_level: New priority level
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")

        if new_priority_level not in self.priority_levels:
            raise ValueError(f"Invalid priority level: {new_priority_level}")

        task = self.tasks[task_id]
        task.priority = self.priority_levels[new_priority_level]

        # Add task back to queue with new priority
        heapq.heappush(self.task_queue, (task.priority, task.created_at, task_id))
        logger.info(f"Updated task {task_id} priority to: {new_priority_level}")
