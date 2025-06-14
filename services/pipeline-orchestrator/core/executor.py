"""
Task Executor for Pipeline Orchestration
Executes different types of ML tasks and operators
"""

import asyncio
import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.config import get_settings
from core.dag import Task

logger = logging.getLogger(__name__)
settings = get_settings()


class TaskResult:
    """Result of task execution"""

    def __init__(
        self,
        task_id: str,
        success: bool,
        output_data: Optional[Dict] = None,
        error_message: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ):
        self.task_id = task_id
        self.success = success
        self.output_data = output_data or {}
        self.error_message = error_message
        self.artifacts = artifacts or []
        self.execution_time = datetime.utcnow()
        self.execution_id = str(uuid4())


class BaseOperator:
    """Base class for all task operators"""

    def __init__(self, operator_type: str):
        self.operator_type = operator_type
        self.logger = logging.getLogger(f"operator.{operator_type}")

    async def execute(
        self, task: Task, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> TaskResult:
        """Execute the operator"""
        raise NotImplementedError("Subclasses must implement execute method")

    def validate_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate operator parameters and return list of errors"""
        return []

    async def cleanup(self, task_id: str):
        """Clean up resources after task execution"""


class DataIngestionOperator(BaseOperator):
    """Operator for data ingestion tasks"""

    def __init__(self):
        super().__init__("data_ingestion")

    async def execute(
        self, task: Task, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> TaskResult:
        """Execute data ingestion"""
        self.logger.info(f"Starting data ingestion for task {task.name}")

        try:
            # Extract parameters
            source_type = parameters.get("source_type", "file")
            source_path = parameters.get("source_path")
            output_path = parameters.get("output_path")
            data_format = parameters.get("format", "json")

            if not source_path:
                raise ValueError("source_path parameter is required")

            # Simulate data ingestion process
            await asyncio.sleep(2)  # Simulate processing time

            # Mock data ingestion result
            rows_processed = parameters.get("expected_rows", 1000)

            output_data = {
                "source_type": source_type,
                "source_path": source_path,
                "output_path": output_path,
                "rows_processed": rows_processed,
                "data_format": data_format,
                "file_size_mb": rows_processed * 0.001,  # Mock file size
                "ingestion_timestamp": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                f"Data ingestion completed: {rows_processed} rows processed"
            )

            return TaskResult(
                task_id=task.id,
                success=True,
                output_data=output_data,
                artifacts=[output_path] if output_path else [],
            )

        except Exception as e:
            self.logger.error(f"Data ingestion failed: {e}")
            return TaskResult(task_id=task.id, success=False, error_message=str(e))


class DataValidationOperator(BaseOperator):
    """Operator for data validation tasks"""

    def __init__(self):
        super().__init__("data_validation")

    async def execute(
        self, task: Task, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> TaskResult:
        """Execute data validation"""
        self.logger.info(f"Starting data validation for task {task.name}")

        try:
            # Get input data from previous task
            input_data_path = parameters.get("input_path")
            validation_rules = parameters.get("validation_rules", {})

            # Simulate validation process
            await asyncio.sleep(1)

            # Mock validation results
            total_records = context.get("data_ingestion", {}).get(
                "rows_processed", 1000
            )
            validation_errors = max(0, int(total_records * 0.02))  # 2% error rate

            output_data = {
                "total_records": total_records,
                "valid_records": total_records - validation_errors,
                "validation_errors": validation_errors,
                "error_rate": (
                    validation_errors / total_records if total_records > 0 else 0
                ),
                "validation_rules_applied": len(validation_rules),
                "validation_timestamp": datetime.utcnow().isoformat(),
            }

            # Fail if error rate is too high
            max_error_rate = parameters.get("max_error_rate", 0.05)
            if output_data["error_rate"] > max_error_rate:
                raise ValueError(
                    f"Validation error rate {output_data['error_rate']:.2%} exceeds threshold {max_error_rate:.2%}"
                )

            self.logger.info(
                f"Data validation completed: {output_data['valid_records']} valid records"
            )

            return TaskResult(task_id=task.id, success=True, output_data=output_data)

        except Exception as e:
            self.logger.error(f"Data validation failed: {e}")
            return TaskResult(task_id=task.id, success=False, error_message=str(e))


class ModelTrainingOperator(BaseOperator):
    """Operator for model training tasks"""

    def __init__(self):
        super().__init__("model_training")

    async def execute(
        self, task: Task, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> TaskResult:
        """Execute model training"""
        self.logger.info(f"Starting model training for task {task.name}")

        try:
            # Extract training parameters
            model_type = parameters.get("model_type", "classification")
            algorithm = parameters.get("algorithm", "random_forest")
            hyperparameters = parameters.get("hyperparameters", {})
            training_data_path = parameters.get("training_data_path")

            # Simulate training process (longer for ML tasks)
            training_duration = parameters.get("training_duration_seconds", 10)
            await asyncio.sleep(training_duration)

            # Mock training results
            output_data = {
                "model_type": model_type,
                "algorithm": algorithm,
                "hyperparameters": hyperparameters,
                "training_samples": context.get("data_validation", {}).get(
                    "valid_records", 800
                ),
                "training_duration_seconds": training_duration,
                "model_metrics": {
                    "accuracy": 0.85
                    + (hash(task.id) % 100) / 1000,  # Mock but deterministic
                    "precision": 0.83 + (hash(task.id) % 80) / 1000,
                    "recall": 0.82 + (hash(task.id) % 90) / 1000,
                    "f1_score": 0.84 + (hash(task.id) % 70) / 1000,
                },
                "model_size_mb": 15.5,
                "feature_count": hyperparameters.get("n_features", 100),
                "model_path": f"/models/{task.id}/model.pkl",
                "training_completed_at": datetime.utcnow().isoformat(),
            }

            # Check if model meets quality threshold
            min_accuracy = parameters.get("min_accuracy", 0.8)
            if output_data["model_metrics"]["accuracy"] < min_accuracy:
                raise ValueError(
                    f"Model accuracy {output_data['model_metrics']['accuracy']:.3f} below threshold {min_accuracy}"
                )

            self.logger.info(
                f"Model training completed with accuracy: {output_data['model_metrics']['accuracy']:.3f}"
            )

            return TaskResult(
                task_id=task.id,
                success=True,
                output_data=output_data,
                artifacts=[output_data["model_path"]],
            )

        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            return TaskResult(task_id=task.id, success=False, error_message=str(e))


class ModelRegistrationOperator(BaseOperator):
    """Operator for registering models in the model registry"""

    def __init__(self):
        super().__init__("model_registration")

    async def execute(
        self, task: Task, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> TaskResult:
        """Execute model registration"""
        self.logger.info(f"Starting model registration for task {task.name}")

        try:
            # Get model info from training task
            training_output = context.get("model_training", {})
            if not training_output:
                raise ValueError("No model training output found in context")

            # Registration parameters
            model_name = parameters.get("model_name", f"model-{task.id}")
            model_version = parameters.get("model_version", "1.0.0")
            description = parameters.get(
                "description", "Model trained by pipeline orchestrator"
            )
            tags = parameters.get("tags", [])

            # Simulate model registry API call
            await asyncio.sleep(2)

            # Mock registration response
            output_data = {
                "model_id": str(uuid4()),
                "model_name": model_name,
                "model_version": model_version,
                "description": description,
                "tags": tags,
                "framework": "sklearn",  # Mock framework
                "model_metrics": training_output.get("model_metrics", {}),
                "model_size_mb": training_output.get("model_size_mb", 0),
                "model_path": training_output.get("model_path"),
                "registry_url": f"{settings.MODEL_REGISTRY_URL}/api/v1/models",
                "registered_at": datetime.utcnow().isoformat(),
                "stage": "development",
            }

            self.logger.info(
                f"Model registered successfully: {model_name} v{model_version}"
            )

            return TaskResult(task_id=task.id, success=True, output_data=output_data)

        except Exception as e:
            self.logger.error(f"Model registration failed: {e}")
            return TaskResult(task_id=task.id, success=False, error_message=str(e))


class CustomScriptOperator(BaseOperator):
    """Operator for executing custom scripts"""

    def __init__(self):
        super().__init__("custom_script")

    async def execute(
        self, task: Task, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> TaskResult:
        """Execute custom script"""
        self.logger.info(f"Starting custom script execution for task {task.name}")

        try:
            script_type = parameters.get("script_type", "python")
            script_content = parameters.get("script_content")
            script_path = parameters.get("script_path")

            if not script_content and not script_path:
                raise ValueError(
                    "Either script_content or script_path must be provided"
                )

            # Create temporary script file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=f".{script_type}", delete=False
            ) as f:
                if script_content:
                    f.write(script_content)
                elif script_path:
                    with open(script_path, "r") as source:
                        f.write(source.read())

                temp_script_path = f.name

            try:
                # Execute script
                if script_type == "python":
                    cmd = ["python3", temp_script_path]
                elif script_type == "bash":
                    cmd = ["bash", temp_script_path]
                else:
                    raise ValueError(f"Unsupported script type: {script_type}")

                # Add environment variables
                env = {**task.environment_variables}

                # Add context as environment variables
                for key, value in context.items():
                    if isinstance(value, dict):
                        env[f"CONTEXT_{key.upper()}"] = json.dumps(value)
                    else:
                        env[f"CONTEXT_{key.upper()}"] = str(value)

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=task.resources.timeout_seconds
                )

                if process.returncode != 0:
                    raise RuntimeError(
                        f"Script failed with exit code {process.returncode}: {stderr.decode()}"
                    )

                output_data = {
                    "script_type": script_type,
                    "exit_code": process.returncode,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "executed_at": datetime.utcnow().isoformat(),
                }

                self.logger.info(f"Custom script executed successfully")

                return TaskResult(
                    task_id=task.id, success=True, output_data=output_data
                )

            finally:
                # Clean up temporary file
                Path(temp_script_path).unlink(missing_ok=True)

        except Exception as e:
            self.logger.error(f"Custom script execution failed: {e}")
            return TaskResult(task_id=task.id, success=False, error_message=str(e))


class TaskExecutor:
    """Main task execution engine"""

    def __init__(self):
        self.operators = {
            "data_ingestion": DataIngestionOperator(),
            "data_validation": DataValidationOperator(),
            "model_training": ModelTrainingOperator(),
            "model_registration": ModelRegistrationOperator(),
            "custom_script": CustomScriptOperator(),
        }

        # Track running tasks
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_contexts: Dict[str, Dict] = {}

    async def initialize(self):
        """Initialize the task executor"""
        logger.info("Initializing Task Executor")
        logger.info(f"Available operators: {list(self.operators.keys())}")

    async def shutdown(self):
        """Shutdown the task executor"""
        logger.info("Shutting down Task Executor")

        # Cancel running tasks
        for task_id, task_coroutine in self.running_tasks.items():
            task_coroutine.cancel()
            try:
                await task_coroutine
            except asyncio.CancelledError:
                pass

        self.running_tasks.clear()
        self.task_contexts.clear()

    async def execute_task(
        self,
        task: Task,
        pipeline_parameters: Dict[str, Any],
        task_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single task"""
        logger.info(f"Executing task {task.name} ({task.operator})")

        # Get operator
        if task.operator not in self.operators:
            raise ValueError(f"Unknown operator: {task.operator}")

        operator = self.operators[task.operator]

        # Validate parameters
        validation_errors = operator.validate_parameters(task.parameters)
        if validation_errors:
            raise ValueError(f"Parameter validation failed: {validation_errors}")

        # Build context from previous task outputs
        context = {}
        for upstream_task_id in task.upstream_tasks:
            if upstream_task_id in task_outputs:
                # Use task name as context key if available, otherwise use task ID
                context_key = upstream_task_id  # Could be improved to use task names
                context[context_key] = task_outputs[upstream_task_id]

        # Merge pipeline parameters
        merged_parameters = {**pipeline_parameters, **task.parameters}

        try:
            # Execute task
            start_time = time.time()
            result = await operator.execute(task, merged_parameters, context)
            execution_time = time.time() - start_time

            if result.success:
                logger.info(
                    f"Task {task.name} completed successfully in {execution_time:.2f}s"
                )
                return result.output_data
            else:
                logger.error(f"Task {task.name} failed: {result.error_message}")
                raise RuntimeError(result.error_message)

        except Exception as e:
            logger.error(f"Task {task.name} execution failed: {e}")
            raise

        finally:
            # Cleanup
            await operator.cleanup(task.id)

    async def cancel_task(self, task_id: str):
        """Cancel a running task"""
        if task_id in self.running_tasks:
            task_coroutine = self.running_tasks.pop(task_id)
            task_coroutine.cancel()
            logger.info(f"Cancelled task {task_id}")

    def add_operator(self, operator_type: str, operator: BaseOperator):
        """Add a custom operator"""
        self.operators[operator_type] = operator
        logger.info(f"Added custom operator: {operator_type}")

    def get_available_operators(self) -> List[str]:
        """Get list of available operators"""
        return list(self.operators.keys())

    def get_operator_info(self, operator_type: str) -> Optional[Dict]:
        """Get information about an operator"""
        if operator_type not in self.operators:
            return None

        operator = self.operators[operator_type]
        return {
            "type": operator_type,
            "class": operator.__class__.__name__,
            "description": operator.__doc__ or "No description available",
        }
