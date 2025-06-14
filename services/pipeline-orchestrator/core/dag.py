"""
Directed Acyclic Graph (DAG) implementation for pipeline orchestration
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    """Pipeline trigger types"""

    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"
    WEBHOOK = "webhook"
    DATA_CHANGE = "data_change"
    MODEL_DRIFT = "model_drift"


class ResourceRequirements(BaseModel):
    """Resource requirements for task execution"""

    cpu: float = Field(default=1.0, ge=0.1, le=64.0)
    memory_gb: float = Field(default=2.0, ge=0.1, le=128.0)
    gpu: int = Field(default=0, ge=0, le=8)
    disk_gb: Optional[float] = Field(default=None, ge=0.1)
    timeout_seconds: int = Field(default=3600, ge=1, le=86400)  # Max 24 hours


class RetryPolicy(BaseModel):
    """Retry policy for failed tasks"""

    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)
    exponential_backoff: bool = Field(default=True)
    retry_on_failure_codes: List[int] = Field(default_factory=lambda: [1, 2, 130])


class Task(BaseModel):
    """Individual task in a pipeline"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    operator: str = Field(
        ..., min_length=1
    )  # Type of operator (data_ingestion, model_training, etc.)

    # Task configuration
    parameters: Dict[str, Any] = Field(default_factory=dict)
    environment_variables: Dict[str, str] = Field(default_factory=dict)

    # Dependencies
    upstream_tasks: List[str] = Field(default_factory=list)  # Task IDs this depends on
    downstream_tasks: List[str] = Field(
        default_factory=list
    )  # Tasks that depend on this

    # Execution settings
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    # Conditional execution
    condition: Optional[str] = Field(
        default=None
    )  # Python expression for conditional execution
    trigger_rule: str = Field(
        default="all_success"
    )  # all_success, all_done, one_success, etc.

    # Task metadata
    description: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = Field(default=None)

    # Execution state (runtime)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    retry_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None)
    output_data: Dict[str, Any] = Field(default_factory=dict)

    @validator("trigger_rule")
    def validate_trigger_rule(cls, v):
        """Validate trigger rule"""
        valid_rules = [
            "all_success",
            "all_done",
            "all_failed",
            "one_success",
            "one_failed",
            "none_failed",
            "dummy",
        ]
        if v not in valid_rules:
            raise ValueError(f"trigger_rule must be one of {valid_rules}")
        return v

    def can_run(self, completed_tasks: Set[str], failed_tasks: Set[str]) -> bool:
        """Check if task can run based on dependencies and trigger rule"""
        if self.status in [
            TaskStatus.RUNNING,
            TaskStatus.SUCCESS,
            TaskStatus.CANCELLED,
        ]:
            return False

        if not self.upstream_tasks:
            return True

        upstream_completed = set(self.upstream_tasks) & completed_tasks
        upstream_failed = set(self.upstream_tasks) & failed_tasks

        if self.trigger_rule == "all_success":
            return (
                len(upstream_completed) == len(self.upstream_tasks)
                and not upstream_failed
            )
        elif self.trigger_rule == "all_done":
            return len(upstream_completed) + len(upstream_failed) == len(
                self.upstream_tasks
            )
        elif self.trigger_rule == "all_failed":
            return len(upstream_failed) == len(self.upstream_tasks)
        elif self.trigger_rule == "one_success":
            return len(upstream_completed) > 0
        elif self.trigger_rule == "one_failed":
            return len(upstream_failed) > 0
        elif self.trigger_rule == "none_failed":
            return len(upstream_completed) == len(self.upstream_tasks)
        elif self.trigger_rule == "dummy":
            return True

        return False

    def should_retry(self) -> bool:
        """Check if task should be retried"""
        return (
            self.status == TaskStatus.FAILED
            and self.retry_count < self.retry_policy.max_retries
        )


class Schedule(BaseModel):
    """Schedule configuration for pipeline execution"""

    cron_expression: Optional[str] = Field(default=None)  # Cron-like schedule
    interval_seconds: Optional[int] = Field(default=None)  # Simple interval
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    catchup: bool = Field(default=False)  # Whether to run missed schedules
    max_active_runs: int = Field(default=1)


class Pipeline(BaseModel):
    """Pipeline DAG definition"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    version: str = Field(default="1.0.0")

    # Tasks and dependencies
    tasks: Dict[str, Task] = Field(default_factory=dict)

    # Pipeline configuration
    schedule: Optional[Schedule] = Field(default=None)
    trigger_type: TriggerType = Field(default=TriggerType.MANUAL)

    # Pipeline metadata
    tags: List[str] = Field(default_factory=list)
    owner: str = Field(..., min_length=1)
    team: Optional[str] = Field(default=None)
    project: Optional[str] = Field(default=None)

    # Pipeline settings
    max_concurrent_runs: int = Field(default=1, ge=1, le=10)
    default_retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)

    # State
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_task(self, task: Task) -> None:
        """Add a task to the pipeline"""
        self.tasks[task.id] = task
        self._update_dependencies()

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the pipeline"""
        if task_id in self.tasks:
            # Remove dependencies
            for task in self.tasks.values():
                if task_id in task.upstream_tasks:
                    task.upstream_tasks.remove(task_id)
                if task_id in task.downstream_tasks:
                    task.downstream_tasks.remove(task_id)

            del self.tasks[task_id]

    def add_dependency(self, upstream_task_id: str, downstream_task_id: str) -> None:
        """Add dependency between tasks"""
        if upstream_task_id not in self.tasks or downstream_task_id not in self.tasks:
            raise ValueError("Both tasks must exist in the pipeline")

        if downstream_task_id not in self.tasks[upstream_task_id].downstream_tasks:
            self.tasks[upstream_task_id].downstream_tasks.append(downstream_task_id)

        if upstream_task_id not in self.tasks[downstream_task_id].upstream_tasks:
            self.tasks[downstream_task_id].upstream_tasks.append(upstream_task_id)

    def _update_dependencies(self) -> None:
        """Update task dependencies based on current tasks"""
        self.updated_at = datetime.utcnow()

    def validate_dag(self) -> List[str]:
        """Validate DAG structure and return any errors"""
        errors = []

        # Check for cycles
        if self._has_cycle():
            errors.append("Pipeline contains cycles")

        # Check for orphaned tasks
        orphaned = self._find_orphaned_tasks()
        if orphaned:
            errors.append(f"Orphaned tasks found: {', '.join(orphaned)}")

        # Validate task dependencies
        for task_id, task in self.tasks.items():
            for upstream_id in task.upstream_tasks:
                if upstream_id not in self.tasks:
                    errors.append(
                        f"Task {task_id} depends on non-existent task {upstream_id}"
                    )

        # Check for empty pipeline
        if not self.tasks:
            errors.append("Pipeline must contain at least one task")

        return errors

    def _has_cycle(self) -> bool:
        """Check if the DAG has cycles using DFS"""
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for downstream_id in self.tasks[task_id].downstream_tasks:
                if downstream_id not in visited:
                    if dfs(downstream_id):
                        return True
                elif downstream_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True

        return False

    def _find_orphaned_tasks(self) -> List[str]:
        """Find tasks with no connections"""
        orphaned = []

        for task_id, task in self.tasks.items():
            if (
                not task.upstream_tasks
                and not task.downstream_tasks
                and len(self.tasks) > 1
            ):
                orphaned.append(task_id)

        return orphaned

    def get_root_tasks(self) -> List[str]:
        """Get tasks with no dependencies (root tasks)"""
        return [
            task_id for task_id, task in self.tasks.items() if not task.upstream_tasks
        ]

    def get_leaf_tasks(self) -> List[str]:
        """Get tasks with no downstream dependencies (leaf tasks)"""
        return [
            task_id for task_id, task in self.tasks.items() if not task.downstream_tasks
        ]

    def get_runnable_tasks(
        self, completed_tasks: Set[str], failed_tasks: Set[str]
    ) -> List[str]:
        """Get tasks that can currently run"""
        runnable = []

        for task_id, task in self.tasks.items():
            if task.can_run(completed_tasks, failed_tasks):
                runnable.append(task_id)

        return runnable

    def get_task_level(self, task_id: str) -> int:
        """Get the level of a task in the DAG (0 = root level)"""
        if task_id not in self.tasks:
            return -1

        task = self.tasks[task_id]
        if not task.upstream_tasks:
            return 0

        max_upstream_level = -1
        for upstream_id in task.upstream_tasks:
            upstream_level = self.get_task_level(upstream_id)
            max_upstream_level = max(max_upstream_level, upstream_level)

        return max_upstream_level + 1

    def estimate_duration(self) -> timedelta:
        """Estimate total pipeline duration based on critical path"""
        # Simple estimation - can be made more sophisticated
        max_duration = 0

        for task_id in self.get_leaf_tasks():
            path_duration = self._calculate_path_duration(task_id)
            max_duration = max(max_duration, path_duration)

        return timedelta(seconds=max_duration)

    def _calculate_path_duration(
        self, task_id: str, visited: Optional[Set[str]] = None
    ) -> float:
        """Calculate duration of longest path to this task"""
        if visited is None:
            visited = set()

        if task_id in visited:  # Cycle detection
            return 0

        visited.add(task_id)
        task = self.tasks[task_id]
        task_duration = task.resources.timeout_seconds

        if not task.upstream_tasks:
            return task_duration

        max_upstream_duration = 0
        for upstream_id in task.upstream_tasks:
            upstream_duration = self._calculate_path_duration(
                upstream_id, visited.copy()
            )
            max_upstream_duration = max(max_upstream_duration, upstream_duration)

        return max_upstream_duration + task_duration
