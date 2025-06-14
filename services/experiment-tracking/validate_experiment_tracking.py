#!/usr/bin/env python3
"""
Validation script for Experiment Tracking service architecture
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def validate_directory_structure() -> List[str]:
    """Validate service directory structure"""
    errors = []

    required_dirs = ["api", "api/routes", "core", "models"]

    for directory in required_dirs:
        if not Path(directory).exists():
            errors.append(f"Missing directory: {directory}")

    return errors


def validate_required_files() -> List[str]:
    """Validate required files exist"""
    errors = []

    required_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        "core/__init__.py",
        "core/config.py",
        "core/logging.py",
        "api/__init__.py",
        "api/routes/__init__.py",
        "api/routes/health.py",
        "api/routes/projects.py",
        "models/__init__.py",
        "models/project.py",
        "models/experiment.py",
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            errors.append(f"Missing file: {file_path}")

    return errors


def validate_python_imports() -> List[str]:
    """Validate Python imports work correctly"""
    errors = []

    modules_to_test = [
        "core.config",
        "core.logging",
        "models.project",
        "models.experiment",
        "api.routes.health",
        "api.routes.projects",
    ]

    for module_name in modules_to_test:
        try:
            # Try to import the module
            if Path(f"{module_name.replace('.', '/')}.py").exists():
                spec = importlib.util.spec_from_file_location(
                    module_name, f"{module_name.replace('.', '/')}.py"
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
        except Exception as e:
            errors.append(f"Import error in {module_name}: {str(e)}")

    return errors


def validate_api_structure() -> List[str]:
    """Validate API structure and endpoints"""
    errors = []

    # Check for FastAPI router in routes
    route_files = ["api/routes/health.py", "api/routes/projects.py"]

    for route_file in route_files:
        if Path(route_file).exists():
            try:
                with open(route_file, "r") as f:
                    content = f.read()
                    if "APIRouter" not in content:
                        errors.append(f"{route_file} missing APIRouter")
                    if "router = APIRouter()" not in content:
                        errors.append(f"{route_file} missing router instance")
            except Exception as e:
                errors.append(f"Error reading {route_file}: {str(e)}")

    return errors


def validate_database_models() -> List[str]:
    """Validate database models structure"""
    errors = []

    model_files = ["models/project.py", "models/experiment.py"]

    for model_file in model_files:
        if Path(model_file).exists():
            try:
                with open(model_file, "r") as f:
                    content = f.read()

                    # Check for SQLAlchemy models
                    if "Base = declarative_base()" not in content:
                        errors.append(f"{model_file} missing SQLAlchemy base")

                    # Check for Pydantic models
                    if "BaseModel" not in content:
                        errors.append(f"{model_file} missing Pydantic models")

            except Exception as e:
                errors.append(f"Error reading {model_file}: {str(e)}")

    return errors


def validate_configuration() -> List[str]:
    """Validate configuration setup"""
    errors = []

    if Path("core/config.py").exists():
        try:
            with open("core/config.py", "r") as f:
                content = f.read()

                # Check for required configuration elements
                required_config = [
                    "class Settings",
                    "BaseSettings",
                    "get_settings",
                    "database_url",
                    "registry_service_url",
                    "pipeline_orchestrator_url",
                    "feature_store_url",
                ]

                for item in required_config:
                    if item not in content:
                        errors.append(f"core/config.py missing: {item}")

        except Exception as e:
            errors.append(f"Error reading core/config.py: {str(e)}")

    return errors


def validate_mlops_integration() -> List[str]:
    """Validate MLOps service integration structure"""
    errors = []

    # Check main.py for service integration
    if Path("main.py").exists():
        try:
            with open("main.py", "r") as f:
                content = f.read()

                # Check for FastAPI app setup
                if "FastAPI(" not in content:
                    errors.append("main.py missing FastAPI app setup")

                # Check for router inclusion
                if "include_router" not in content:
                    errors.append("main.py missing router inclusion")

        except Exception as e:
            errors.append(f"Error reading main.py: {str(e)}")

    return errors


def validate_healthcare_integration() -> List[str]:
    """Validate healthcare-specific features"""
    errors = []

    # Check for healthcare-specific models in project.py
    if Path("models/project.py").exists():
        try:
            with open("models/project.py", "r") as f:
                content = f.read()

                if "HealthcareProject" not in content:
                    errors.append("models/project.py missing HealthcareProject model")

                if "healthcare_classification" not in content:
                    errors.append("models/project.py missing healthcare template")

        except Exception as e:
            errors.append(f"Error reading models/project.py: {str(e)}")

    return errors


def generate_report(validation_results: Dict[str, List[str]]) -> Dict[str, Any]:
    """Generate validation report"""

    total_errors = sum(len(errors) for errors in validation_results.values())

    report = {
        "service": "experiment-tracking",
        "validation_timestamp": "2024-01-15T10:30:00Z",
        "overall_status": "PASSED" if total_errors == 0 else "FAILED",
        "total_errors": total_errors,
        "validation_results": validation_results,
        "summary": {
            "directory_structure": (
                "PASSED"
                if len(validation_results["directory_structure"]) == 0
                else "FAILED"
            ),
            "required_files": (
                "PASSED" if len(validation_results["required_files"]) == 0 else "FAILED"
            ),
            "python_imports": (
                "PASSED" if len(validation_results["python_imports"]) == 0 else "FAILED"
            ),
            "api_structure": (
                "PASSED" if len(validation_results["api_structure"]) == 0 else "FAILED"
            ),
            "database_models": (
                "PASSED"
                if len(validation_results["database_models"]) == 0
                else "FAILED"
            ),
            "configuration": (
                "PASSED" if len(validation_results["configuration"]) == 0 else "FAILED"
            ),
            "mlops_integration": (
                "PASSED"
                if len(validation_results["mlops_integration"]) == 0
                else "FAILED"
            ),
            "healthcare_integration": (
                "PASSED"
                if len(validation_results["healthcare_integration"]) == 0
                else "FAILED"
            ),
        },
        "recommendations": [
            "Implement database connection validation in health checks",
            "Add integration tests for MLOps service connectivity",
            "Create comprehensive API documentation",
            "Add monitoring and metrics collection",
            "Implement security and authentication",
        ],
    }

    return report


def main():
    """Main validation function"""
    print("🧪 Validating Experiment Tracking 2.0 Service Architecture...")
    print("=" * 60)

    # Run all validations
    validation_results = {
        "directory_structure": validate_directory_structure(),
        "required_files": validate_required_files(),
        "python_imports": validate_python_imports(),
        "api_structure": validate_api_structure(),
        "database_models": validate_database_models(),
        "configuration": validate_configuration(),
        "mlops_integration": validate_mlops_integration(),
        "healthcare_integration": validate_healthcare_integration(),
    }

    # Generate report
    report = generate_report(validation_results)

    # Print results
    print(f"📊 Overall Status: {report['overall_status']}")
    print(f"🔍 Total Issues: {report['total_errors']}")
    print()

    # Print detailed results
    for category, errors in validation_results.items():
        status = "✅ PASSED" if len(errors) == 0 else "❌ FAILED"
        print(f"{status} {category.replace('_', ' ').title()}")

        if errors:
            for error in errors:
                print(f"  • {error}")
            print()

    # Print summary
    print("📋 Validation Summary:")
    for category, status in report["summary"].items():
        icon = "✅" if status == "PASSED" else "❌"
        print(f"  {icon} {category.replace('_', ' ').title()}: {status}")

    print()
    print("🚀 Next Steps:")
    for i, recommendation in enumerate(report["recommendations"], 1):
        print(f"  {i}. {recommendation}")

    # Save report
    import json

    with open("experiment_tracking_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Report saved to: experiment_tracking_validation_report.json")

    # Exit with appropriate code
    sys.exit(0 if report["overall_status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
