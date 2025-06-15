"""
Resource Manager for Pipeline Orchestration
Intelligent resource allocation and monitoring for ML workloads
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import psutil
from core.config import get_settings
from core.dag import ResourceRequirements

logger = logging.getLogger(__name__)
settings = get_settings()


class ResourceAllocation:
    """Represents a resource allocation for a task"""

    def __init__(self, task_id: str, requirements: ResourceRequirements):
        self.task_id = task_id
        self.requirements = requirements
        self.allocated_at = datetime.utcnow()
        self.cpu_cores = requirements.cpu
        self.memory_gb = requirements.memory_gb
        self.gpu_count = requirements.gpu
        self.disk_gb = requirements.disk_gb or 0

    def get_allocation_duration(self) -> timedelta:
        """Get how long resources have been allocated"""
        return datetime.utcnow() - self.allocated_at


class ResourcePool:
    """Manages available system resources"""

    def __init__(self):
        self.total_cpu_cores = settings.MAX_CPU_CORES
        self.total_memory_gb = settings.MAX_MEMORY_GB
        self.total_gpu_count = settings.MAX_GPU_COUNT

        # Current allocations
        self.allocated_cpu = 0.0
        self.allocated_memory = 0.0
        self.allocated_gpu = 0
        self.allocated_disk = 0.0

        # Track allocations by task
        self.allocations: Dict[str, ResourceAllocation] = {}

        # Resource usage history for optimization
        self.usage_history: List[Dict] = []
        self.last_usage_update = datetime.utcnow()

    def get_available_cpu(self) -> float:
        """Get available CPU cores"""
        return max(0, self.total_cpu_cores - self.allocated_cpu)

    def get_available_memory(self) -> float:
        """Get available memory in GB"""
        return max(0, self.total_memory_gb - self.allocated_memory)

    def get_available_gpu(self) -> int:
        """Get available GPU count"""
        return max(0, self.total_gpu_count - self.allocated_gpu)

    def get_utilization_stats(self) -> Dict:
        """Get current resource utilization statistics"""
        return {
            "cpu": {
                "total": self.total_cpu_cores,
                "allocated": self.allocated_cpu,
                "available": self.get_available_cpu(),
                "utilization_percent": (self.allocated_cpu / self.total_cpu_cores)
                * 100,
            },
            "memory": {
                "total_gb": self.total_memory_gb,
                "allocated_gb": self.allocated_memory,
                "available_gb": self.get_available_memory(),
                "utilization_percent": (self.allocated_memory / self.total_memory_gb)
                * 100,
            },
            "gpu": {
                "total": self.total_gpu_count,
                "allocated": self.allocated_gpu,
                "available": self.get_available_gpu(),
                "utilization_percent": (
                    (self.allocated_gpu / self.total_gpu_count) * 100
                    if self.total_gpu_count > 0
                    else 0
                ),
            },
            "active_tasks": len(self.allocations),
        }

    def can_allocate(self, requirements: ResourceRequirements) -> bool:
        """Check if resources can be allocated"""
        return (
            self.get_available_cpu() >= requirements.cpu
            and self.get_available_memory() >= requirements.memory_gb
            and self.get_available_gpu() >= requirements.gpu
        )

    def allocate(self, task_id: str, requirements: ResourceRequirements) -> bool:
        """Allocate resources for a task"""
        if not self.can_allocate(requirements):
            return False

        if task_id in self.allocations:
            logger.warning(f"Task {task_id} already has resource allocation")
            return False

        # Allocate resources
        allocation = ResourceAllocation(task_id, requirements)
        self.allocations[task_id] = allocation

        self.allocated_cpu += requirements.cpu
        self.allocated_memory += requirements.memory_gb
        self.allocated_gpu += requirements.gpu

        logger.info(
            f"Allocated resources for task {task_id}: "
            f"CPU={requirements.cpu}, Memory={requirements.memory_gb}GB, "
            f"GPU={requirements.gpu}"
        )

        return True

    def release(self, task_id: str) -> bool:
        """Release resources for a task"""
        if task_id not in self.allocations:
            logger.warning(f"No resource allocation found for task {task_id}")
            return False

        allocation = self.allocations.pop(task_id)

        self.allocated_cpu -= allocation.cpu_cores
        self.allocated_memory -= allocation.memory_gb
        self.allocated_gpu -= allocation.gpu_count

        duration = allocation.get_allocation_duration()

        logger.info(f"Released resources for task {task_id} after {duration}")

        return True

    def update_usage_history(self):
        """Update resource usage history"""
        now = datetime.utcnow()

        # Only update every minute to avoid too much data
        if now - self.last_usage_update < timedelta(minutes=1):
            return

        # Get actual system usage
        system_cpu = psutil.cpu_percent(interval=1)
        system_memory = psutil.virtual_memory()

        usage_record = {
            "timestamp": now.isoformat(),
            "allocated_cpu": self.allocated_cpu,
            "allocated_memory_gb": self.allocated_memory,
            "allocated_gpu": self.allocated_gpu,
            "system_cpu_percent": system_cpu,
            "system_memory_percent": system_memory.percent,
            "system_memory_available_gb": system_memory.available / (1024**3),
            "active_tasks": len(self.allocations),
        }

        self.usage_history.append(usage_record)

        # Keep only last 24 hours of data
        cutoff = now - timedelta(hours=24)
        self.usage_history = [
            record
            for record in self.usage_history
            if datetime.fromisoformat(record["timestamp"]) > cutoff
        ]

        self.last_usage_update = now

    def get_optimization_recommendations(self) -> List[str]:
        """Get resource optimization recommendations"""
        recommendations = []
        stats = self.get_utilization_stats()

        # CPU recommendations
        cpu_util = stats["cpu"]["utilization_percent"]
        if cpu_util > 90:
            recommendations.append(
                "High CPU utilization - consider adding more CPU cores or "
                "reducing concurrent tasks"
            )
        elif cpu_util < 20:
            recommendations.append(
                "Low CPU utilization - could increase concurrent tasks for "
                "better throughput"
            )

        # Memory recommendations
        memory_util = stats["memory"]["utilization_percent"]
        if memory_util > 85:
            recommendations.append(
                "High memory utilization - consider adding more RAM or "
                "optimizing memory usage"
            )
        elif memory_util < 30:
            recommendations.append(
                "Low memory utilization - could run more memory-intensive "
                "tasks concurrently"
            )

        # GPU recommendations
        if self.total_gpu_count > 0:
            gpu_util = stats["gpu"]["utilization_percent"]
            if gpu_util > 90:
                recommendations.append(
                    "High GPU utilization - consider optimizing GPU workloads "
                    "or adding more GPUs"
                )
            elif gpu_util < 20:
                recommendations.append(
                    "Low GPU utilization - could schedule more " "GPU-intensive tasks"
                )

        return recommendations


class ResourceManager:
    """Main resource management system"""

    def __init__(self):
        self.resource_pool = ResourcePool()
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_running = False

        # Resource prediction and optimization
        self.task_resource_profiles: Dict[str, Dict] = (
            {}
        )  # Historical resource usage by operator type
        self.load_balancing_enabled = True

        # Metrics
        self.allocation_history: List[Dict] = []

    async def initialize(self):
        """Initialize the resource manager"""
        logger.info("Initializing Resource Manager")

        # Detect system resources
        await self._detect_system_resources()

        # Start monitoring
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info(
            f"Resource Manager initialized - "
            f"CPU: {self.resource_pool.total_cpu_cores} cores, "
            f"Memory: {self.resource_pool.total_memory_gb}GB, "
            f"GPU: {self.resource_pool.total_gpu_count}"
        )

    async def shutdown(self):
        """Shutdown the resource manager"""
        logger.info("Shutting down Resource Manager")
        self.is_running = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Release any remaining allocations
        for task_id in list(self.resource_pool.allocations.keys()):
            self.resource_pool.release(task_id)

        logger.info("Resource Manager shutdown complete")

    async def _detect_system_resources(self):
        """Detect available system resources"""
        try:
            # CPU detection
            cpu_count = psutil.cpu_count(logical=True)
            self.resource_pool.total_cpu_cores = min(cpu_count, settings.MAX_CPU_CORES)

            # Memory detection
            memory = psutil.virtual_memory()
            system_memory_gb = memory.total / (1024**3)
            self.resource_pool.total_memory_gb = min(
                system_memory_gb * 0.8, settings.MAX_MEMORY_GB
            )  # Use 80% of system memory

            # GPU detection (basic - would need nvidia-ml-py for detailed info)
            try:
                import GPUtil

                gpus = GPUtil.getGPUs()
                detected_gpu_count = len(gpus)
                self.resource_pool.total_gpu_count = min(
                    detected_gpu_count, settings.MAX_GPU_COUNT
                )
            except ImportError:
                logger.info("GPUtil not available - GPU detection disabled")
                self.resource_pool.total_gpu_count = 0
            except Exception as e:
                logger.warning(f"GPU detection failed: {e}")
                self.resource_pool.total_gpu_count = 0

        except Exception as e:
            logger.error(f"Error detecting system resources: {e}")
            # Fall back to configured limits

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                # Update resource usage history
                self.resource_pool.update_usage_history()

                # Check for stuck allocations
                await self._check_stuck_allocations()

                # Update task resource profiles
                self._update_task_profiles()

                # Sleep before next iteration
                await asyncio.sleep(60)  # Monitor every minute

            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _check_stuck_allocations(self):
        """Check for allocations that have been active too long"""
        max_allocation_time = timedelta(hours=6)  # 6 hour max
        stuck_tasks = []

        for task_id, allocation in self.resource_pool.allocations.items():
            if allocation.get_allocation_duration() > max_allocation_time:
                stuck_tasks.append(task_id)

        if stuck_tasks:
            logger.warning(f"Found {len(stuck_tasks)} stuck resource allocations")
            # Could implement automatic cleanup here

    def _update_task_profiles(self):
        """Update historical resource usage profiles for different task
        types"""
        # This would analyze completed tasks to build profiles
        # For now, just placeholder

    def has_available_resources(
        self, min_cpu: float = 1.0, min_memory: float = 1.0
    ) -> bool:
        """Check if minimum resources are available"""
        return (
            self.resource_pool.get_available_cpu() >= min_cpu
            and self.resource_pool.get_available_memory() >= min_memory
        )

    def can_allocate_resources(self, requirements: ResourceRequirements) -> bool:
        """Check if specific resources can be allocated"""
        return self.resource_pool.can_allocate(requirements)

    async def allocate_resources(
        self, task_id: str, requirements: ResourceRequirements
    ) -> bool:
        """Allocate resources for a task"""
        # Optimize requirements based on historical data
        optimized_requirements = self._optimize_requirements(requirements)

        success = self.resource_pool.allocate(task_id, optimized_requirements)

        if success:
            # Record allocation
            allocation_record = {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": optimized_requirements.cpu,
                "memory_gb": optimized_requirements.memory_gb,
                "gpu": optimized_requirements.gpu,
            }
            self.allocation_history.append(allocation_record)

        return success

    async def release_resources(self, task_id: str) -> bool:
        """Release resources for a task"""
        return self.resource_pool.release(task_id)

    def _optimize_requirements(
        self, requirements: ResourceRequirements
    ) -> ResourceRequirements:
        """Optimize resource requirements based on historical data"""
        # For now, just return original requirements
        # Could implement ML-based optimization here
        return requirements

    def get_usage_stats(self) -> Dict:
        """Get current resource usage statistics"""
        return self.resource_pool.get_utilization_stats()

    def get_utilization_percentage(self) -> float:
        """Get overall resource utilization percentage"""
        stats = self.get_usage_stats()

        # Weighted average of CPU, memory, and GPU utilization
        cpu_weight = 0.4
        memory_weight = 0.4
        gpu_weight = 0.2

        cpu_util = stats["cpu"]["utilization_percent"]
        memory_util = stats["memory"]["utilization_percent"]
        gpu_util = stats["gpu"]["utilization_percent"]

        return (
            cpu_util * cpu_weight + memory_util * memory_weight + gpu_util * gpu_weight
        )

    def get_optimization_recommendations(self) -> List[str]:
        """Get resource optimization recommendations"""
        return self.resource_pool.get_optimization_recommendations()

    def get_resource_forecast(self, hours_ahead: int = 1) -> Dict:
        """Forecast resource usage (placeholder for ML-based forecasting)"""
        current_stats = self.get_usage_stats()

        # Simple forecast - just return current usage
        # In practice, this would use historical data and ML models
        return {
            "forecast_hours": hours_ahead,
            "predicted_cpu_utilization": current_stats["cpu"]["utilization_percent"],
            "predicted_memory_utilization": current_stats["memory"][
                "utilization_percent"
            ],
            "predicted_gpu_utilization": current_stats["gpu"]["utilization_percent"],
            "confidence": 0.7,  # Placeholder confidence
            "recommendations": self.get_optimization_recommendations(),
        }
