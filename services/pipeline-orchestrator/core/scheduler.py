"""
Intelligent Pipeline Scheduler
Resource-aware task scheduling with ML-specific optimizations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import uuid4

from core.config import get_settings
from core.dag import Pipeline, TaskStatus
from core.executor import TaskExecutor
from core.resource_manager import ResourceManager

logger = logging.getLogger(__name__)
settings = get_settings()


class PipelineRun:
    """Represents a single pipeline execution"""

    def __init__(
        self,
        pipeline: Pipeline,
        run_id: Optional[str] = None,
        triggered_by: str = "manual",
        parameters: Optional[Dict] = None,
    ):
        self.run_id = run_id or str(uuid4())
        self.pipeline = pipeline
        self.triggered_by = triggered_by
        self.parameters = parameters or {}

        # Execution state
        self.status = "queued"
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.task_states: Dict[str, TaskStatus] = {}
        self.task_outputs: Dict[str, Dict] = {}

        # Initialize task states
        for task_id in pipeline.tasks:
            self.task_states[task_id] = TaskStatus.PENDING

    def get_completed_tasks(self) -> Set[str]:
        """Get set of completed task IDs"""
        return {
            task_id
            for task_id, status in self.task_states.items()
            if status == TaskStatus.SUCCESS
        }

    def get_failed_tasks(self) -> Set[str]:
        """Get set of failed task IDs"""
        return {
            task_id
            for task_id, status in self.task_states.items()
            if status == TaskStatus.FAILED
        }

    def get_running_tasks(self) -> Set[str]:
        """Get set of currently running task IDs"""
        return {
            task_id
            for task_id, status in self.task_states.items()
            if status == TaskStatus.RUNNING
        }

    def is_complete(self) -> bool:
        """Check if pipeline run is complete"""
        return self.status in ["success", "failed", "cancelled"]

    def calculate_progress(self) -> float:
        """Calculate completion percentage"""
        total_tasks = len(self.task_states)
        if total_tasks == 0:
            return 100.0

        completed = len(
            [
                s
                for s in self.task_states.values()
                if s in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED]
            ]
        )
        return (completed / total_tasks) * 100.0


class PipelineScheduler:
    """Intelligent scheduler for pipeline execution"""

    def __init__(self):
        self.is_running = False
        self.active_runs: Dict[str, PipelineRun] = {}
        self.queued_runs: List[PipelineRun] = []
        self.completed_runs: List[PipelineRun] = []

        # Resource management
        self.resource_manager = ResourceManager()
        self.executor = TaskExecutor()

        # Scheduler state
        self.scheduler_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        # Metrics
        self.metrics = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "tasks_executed": 0,
            "avg_run_duration": 0.0,
            "resource_utilization": 0.0,
        }

    async def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting pipeline scheduler")
        self.is_running = True

        # Start background tasks
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        await self.resource_manager.initialize()
        await self.executor.initialize()

        logger.info("Pipeline scheduler started successfully")

    async def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return

        logger.info("Stopping pipeline scheduler")
        self.is_running = False

        # Cancel background tasks
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Stop executor and resource manager
        await self.executor.shutdown()
        await self.resource_manager.shutdown()

        logger.info("Pipeline scheduler stopped")

    async def submit_pipeline(
        self,
        pipeline: Pipeline,
        triggered_by: str = "manual",
        parameters: Optional[Dict] = None,
    ) -> str:
        """Submit a pipeline for execution"""
        # Validate pipeline
        errors = pipeline.validate_dag()
        if errors:
            raise ValueError(f"Pipeline validation failed: {errors}")

        # Create pipeline run
        run = PipelineRun(pipeline, triggered_by=triggered_by, parameters=parameters)

        # Check if we can run immediately or need to queue
        if (
            len(self.active_runs) < settings.MAX_CONCURRENT_RUNS
            and self.resource_manager.has_available_resources()
        ):

            await self._start_pipeline_run(run)
        else:
            logger.info(
                f"Queueing pipeline run {run.run_id} (active: {len(self.active_runs)})"
            )
            self.queued_runs.append(run)

        self.metrics["total_runs"] += 1
        return run.run_id

    async def cancel_pipeline(self, run_id: str) -> bool:
        """Cancel a pipeline run"""
        # Check active runs
        if run_id in self.active_runs:
            run = self.active_runs[run_id]
            await self._cancel_pipeline_run(run)
            return True

        # Check queued runs
        for i, run in enumerate(self.queued_runs):
            if run.run_id == run_id:
                run.status = "cancelled"
                self.queued_runs.pop(i)
                self.completed_runs.append(run)
                logger.info(f"Cancelled queued pipeline run {run_id}")
                return True

        return False

    async def get_run_status(self, run_id: str) -> Optional[Dict]:
        """Get status of a pipeline run"""
        # Check active runs
        if run_id in self.active_runs:
            run = self.active_runs[run_id]
            return self._serialize_run_status(run)

        # Check completed runs
        for run in self.completed_runs:
            if run.run_id == run_id:
                return self._serialize_run_status(run)

        # Check queued runs
        for run in self.queued_runs:
            if run.run_id == run_id:
                return self._serialize_run_status(run)

        return None

    def get_active_run_count(self) -> int:
        """Get number of active runs"""
        return len(self.active_runs)

    def get_queued_task_count(self) -> int:
        """Get number of queued tasks across all runs"""
        count = 0
        for run in self.active_runs.values():
            count += len(
                [s for s in run.task_states.values() if s == TaskStatus.QUEUED]
            )
        return count + len(self.queued_runs)

    def get_completed_runs_count(self, hours: int = 24) -> int:
        """Get number of completed runs in the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return len(
            [
                run
                for run in self.completed_runs
                if run.end_time and run.end_time > cutoff
            ]
        )

    def get_resource_usage(self) -> Dict:
        """Get current resource usage"""
        return self.resource_manager.get_usage_stats()

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Process queued runs
                await self._process_queued_runs()

                # Update active runs
                await self._update_active_runs()

                # Cleanup completed runs
                self._cleanup_old_runs()

                # Update metrics
                self._update_metrics()

                # Sleep before next iteration
                await asyncio.sleep(5)  # 5 second scheduling interval

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Longer sleep on error

    async def _heartbeat_loop(self):
        """Heartbeat loop for monitoring"""
        while self.is_running:
            try:
                logger.debug(
                    f"Scheduler heartbeat - Active: {len(self.active_runs)}, "
                    f"Queued: {len(self.queued_runs)}, "
                    f"Resource usage: {self.resource_manager.get_usage_stats()}"
                )

                await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
                await asyncio.sleep(30)

    async def _process_queued_runs(self):
        """Process queued pipeline runs"""
        if not self.queued_runs:
            return

        # Sort queued runs by priority (can implement priority logic here)
        self.queued_runs.sort(key=lambda x: x.pipeline.created_at)

        # Start runs if we have capacity
        while (
            self.queued_runs
            and len(self.active_runs) < settings.MAX_CONCURRENT_RUNS
            and self.resource_manager.has_available_resources()
        ):

            run = self.queued_runs.pop(0)
            await self._start_pipeline_run(run)

    async def _start_pipeline_run(self, run: PipelineRun):
        """Start executing a pipeline run"""
        logger.info(
            f"Starting pipeline run {run.run_id} for pipeline {run.pipeline.name}"
        )

        run.start_time = datetime.utcnow()
        run.status = "running"
        self.active_runs[run.run_id] = run

        # Schedule initial tasks
        await self._schedule_runnable_tasks(run)

    async def _update_active_runs(self):
        """Update status of active pipeline runs"""
        completed_runs = []

        for run_id, run in self.active_runs.items():
            try:
                # Update task statuses
                await self._update_task_statuses(run)

                # Schedule new runnable tasks
                await self._schedule_runnable_tasks(run)

                # Check if run is complete
                if self._is_run_complete(run):
                    await self._complete_pipeline_run(run)
                    completed_runs.append(run_id)

            except Exception as e:
                logger.error(f"Error updating run {run_id}: {e}", exc_info=True)
                run.status = "failed"
                completed_runs.append(run_id)

        # Move completed runs
        for run_id in completed_runs:
            run = self.active_runs.pop(run_id)
            self.completed_runs.append(run)

    async def _schedule_runnable_tasks(self, run: PipelineRun):
        """Schedule tasks that are ready to run"""
        completed_tasks = run.get_completed_tasks()
        failed_tasks = run.get_failed_tasks()
        running_tasks = run.get_running_tasks()

        runnable_task_ids = run.pipeline.get_runnable_tasks(
            completed_tasks, failed_tasks
        )

        for task_id in runnable_task_ids:
            if (
                run.task_states[task_id] == TaskStatus.PENDING
                and task_id not in running_tasks
            ):

                task = run.pipeline.tasks[task_id]

                # Check resource availability
                if self.resource_manager.can_allocate_resources(task.resources):
                    await self._execute_task(run, task_id)

    async def _execute_task(self, run: PipelineRun, task_id: str):
        """Execute a single task"""
        task = run.pipeline.tasks[task_id]

        logger.info(f"Executing task {task.name} ({task_id}) in run {run.run_id}")

        # Update task status
        run.task_states[task_id] = TaskStatus.RUNNING
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.utcnow()

        # Allocate resources
        await self.resource_manager.allocate_resources(task_id, task.resources)

        # Execute task
        try:
            result = await self.executor.execute_task(
                task, run.parameters, run.task_outputs
            )

            # Task succeeded
            run.task_states[task_id] = TaskStatus.SUCCESS
            task.status = TaskStatus.SUCCESS
            task.end_time = datetime.utcnow()
            task.duration_seconds = (task.end_time - task.start_time).total_seconds()
            run.task_outputs[task_id] = result

            logger.info(f"Task {task.name} completed successfully")
            self.metrics["tasks_executed"] += 1

        except Exception as e:
            # Task failed
            logger.error(f"Task {task.name} failed: {e}")

            run.task_states[task_id] = TaskStatus.FAILED
            task.status = TaskStatus.FAILED
            task.end_time = datetime.utcnow()
            task.error_message = str(e)

            # Check if we should retry
            if task.should_retry():
                task.retry_count += 1
                run.task_states[task_id] = TaskStatus.RETRY
                logger.info(f"Scheduling retry {task.retry_count} for task {task.name}")

                # Schedule retry (with delay)
                retry_delay = task.retry_policy.retry_delay_seconds
                if task.retry_policy.exponential_backoff:
                    retry_delay *= 2 ** (task.retry_count - 1)

                asyncio.create_task(
                    self._retry_task_after_delay(run, task_id, retry_delay)
                )

        finally:
            # Release resources
            await self.resource_manager.release_resources(task_id)

    async def _retry_task_after_delay(
        self, run: PipelineRun, task_id: str, delay_seconds: int
    ):
        """Retry a task after a delay"""
        await asyncio.sleep(delay_seconds)

        if run.run_id in self.active_runs:  # Make sure run is still active
            run.task_states[task_id] = TaskStatus.PENDING
            logger.info(f"Retrying task {task_id} in run {run.run_id}")

    async def _update_task_statuses(self, run: PipelineRun):
        """Update task statuses from executor"""
        # This would typically check with the executor for status updates
        # For now, we rely on the execute_task method to update statuses

    def _is_run_complete(self, run: PipelineRun) -> bool:
        """Check if a pipeline run is complete"""
        # All tasks must be in a terminal state
        terminal_states = {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED}

        for status in run.task_states.values():
            if status not in terminal_states:
                return False

        return True

    async def _complete_pipeline_run(self, run: PipelineRun):
        """Complete a pipeline run"""
        run.end_time = datetime.utcnow()

        # Determine final status
        if any(status == TaskStatus.FAILED for status in run.task_states.values()):
            run.status = "failed"
            self.metrics["failed_runs"] += 1
        else:
            run.status = "success"
            self.metrics["successful_runs"] += 1

        logger.info(f"Pipeline run {run.run_id} completed with status: {run.status}")

        # Update metrics
        duration = (run.end_time - run.start_time).total_seconds()
        self._update_avg_duration(duration)

    async def _cancel_pipeline_run(self, run: PipelineRun):
        """Cancel an active pipeline run"""
        logger.info(f"Cancelling pipeline run {run.run_id}")

        # Cancel running tasks
        for task_id, status in run.task_states.items():
            if status == TaskStatus.RUNNING:
                await self.executor.cancel_task(task_id)
                run.task_states[task_id] = TaskStatus.CANCELLED
                await self.resource_manager.release_resources(task_id)

        run.status = "cancelled"
        run.end_time = datetime.utcnow()

    def _cleanup_old_runs(self):
        """Clean up old completed runs to save memory"""
        # Keep only last 1000 completed runs
        if len(self.completed_runs) > 1000:
            self.completed_runs = self.completed_runs[-1000:]

    def _update_metrics(self):
        """Update scheduler metrics"""
        self.metrics["resource_utilization"] = (
            self.resource_manager.get_utilization_percentage()
        )

    def _update_avg_duration(self, duration: float):
        """Update average run duration"""
        total_completed = self.metrics["successful_runs"] + self.metrics["failed_runs"]
        if total_completed == 1:
            self.metrics["avg_run_duration"] = duration
        else:
            # Running average
            current_avg = self.metrics["avg_run_duration"]
            self.metrics["avg_run_duration"] = (
                current_avg * (total_completed - 1) + duration
            ) / total_completed

    def _serialize_run_status(self, run: PipelineRun) -> Dict:
        """Serialize pipeline run status"""
        return {
            "run_id": run.run_id,
            "pipeline_name": run.pipeline.name,
            "status": run.status,
            "triggered_by": run.triggered_by,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "progress": run.calculate_progress(),
            "task_states": {
                task_id: status.value for task_id, status in run.task_states.items()
            },
            "parameters": run.parameters,
        }
