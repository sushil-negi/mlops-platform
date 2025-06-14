#!/usr/bin/env python3
"""
Phase 1 MLOps Infrastructure Validation Script
Tests all critical components end-to-end
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def test_component(name, test_func):
    """Test a component and return result"""
    print(f"🧪 Testing {name}...")
    try:
        result = test_func()
        print(f"✅ {name}: {'PASSED' if result else 'FAILED'}")
        return result
    except Exception as e:
        print(f"❌ {name}: ERROR - {e}")
        return False


def test_github_actions_syntax():
    """Test GitHub Actions workflow syntax"""
    import yaml

    workflows = [
        ".github/workflows/ci-cd.yml",
        ".github/workflows/model-training.yml",
        ".github/workflows/security-scan.yml",
    ]

    for workflow in workflows:
        if not os.path.exists(workflow):
            return False

        with open(workflow, "r") as f:
            yaml.safe_load(f)

    return True


def test_observability_configs():
    """Test observability stack configurations"""
    import yaml

    configs = [
        "docker-compose.logging.yml",
        "infrastructure/docker/elasticsearch/elasticsearch.yml",
        "infrastructure/docker/kibana/kibana.yml",
        "infrastructure/docker/alertmanager/alertmanager.yml",
    ]

    for config in configs:
        if not os.path.exists(config):
            return False

        with open(config, "r") as f:
            yaml.safe_load(f)

    return True


def test_healthcare_ai_service():
    """Test healthcare AI service functionality"""
    sys.path.append("models/healthcare-ai-k8s/src")

    try:
        from healthcare_ai_engine import HealthcareAIEngine

        # Test basic functionality
        engine = HealthcareAIEngine()

        # Test different categories
        test_cases = [
            ("I need help with mobility", "adl"),
            ("I want to hurt myself", "crisis"),
            ("Need caregiver support", "respite_care"),
        ]

        for query, expected_category in test_cases:
            result = engine.generate_response(query)
            if result.get("category") != expected_category:
                print(
                    f"   Category mismatch: {query} -> {result.get('category')} (expected {expected_category})"
                )
                return False

        return True

    except Exception as e:
        print(f"   Healthcare AI service error: {e}")
        return False


def test_data_drift_detector():
    """Test data drift detection"""
    try:
        # Create test data
        test_data = [
            {"text": "I need mobility help", "category": "adl"},
            {"text": "Feeling anxious", "category": "mental_health"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        # Run drift detector
        result = subprocess.run(
            [
                "python3",
                "scripts/data_drift_detector.py",
                "--reference-data",
                temp_file,
                "--hours",
                "1",
            ],
            capture_output=True,
            text=True,
        )

        # Clean up
        os.unlink(temp_file)

        return (
            result.returncode == 0 or result.returncode == 1
        )  # 1 = drift detected (OK)

    except Exception as e:
        print(f"   Drift detector error: {e}")
        return False


def test_monitoring_dashboards():
    """Test monitoring dashboard configs"""
    dashboards = [
        "infrastructure/docker/grafana/provisioning/dashboards/healthcare-ai-dashboard.json",
        "infrastructure/docker/grafana/provisioning/dashboards/model-performance-dashboard.json",
    ]

    for dashboard_path in dashboards:
        if not os.path.exists(dashboard_path):
            return False

        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        # Check basic structure
        if "dashboard" not in dashboard:
            return False

        panels = dashboard["dashboard"].get("panels", [])
        if len(panels) == 0:
            return False

    return True


def test_docker_compose_configs():
    """Test Docker Compose configurations"""
    try:
        # Test main docker-compose
        result = subprocess.run(
            ["docker", "compose", "config", "--quiet"], capture_output=True, text=True
        )

        if result.returncode != 0:
            return False

        # Test logging docker-compose
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.logging.yml",
                "config",
                "--quiet",
            ],
            capture_output=True,
            text=True,
        )

        return result.returncode == 0

    except Exception:
        return False


def test_kubernetes_manifests():
    """Test Kubernetes manifest syntax"""
    import yaml

    manifest_dirs = [
        "gitops/manifests/healthcare-ai-staging/",
        "gitops/manifests/healthcare-ai-production/",
    ]

    for manifest_dir in manifest_dirs:
        if not os.path.exists(manifest_dir):
            continue

        for yaml_file in Path(manifest_dir).glob("*.yaml"):
            with open(yaml_file, "r") as f:
                content = f.read()
                # Handle multiple documents in a single file
                documents = content.split("---")
                for doc in documents:
                    doc = doc.strip()
                    if doc:  # Skip empty documents
                        yaml.safe_load(doc)

    return True


def generate_validation_report(results):
    """Generate validation report"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "phase": "Phase 1 - Critical MLOps Foundation",
        "total_tests": len(results),
        "passed": sum(1 for r in results.values() if r),
        "failed": sum(1 for r in results.values() if not r),
        "success_rate": f"{sum(1 for r in results.values() if r) / len(results) * 100:.1f}%",
        "test_results": results,
        "overall_status": "PASSED" if all(results.values()) else "FAILED",
    }

    return report


def main():
    """Run all Phase 1 validation tests"""
    print("🚀 Phase 1 MLOps Infrastructure Validation")
    print("=" * 50)

    # Define all tests
    tests = {
        "GitHub Actions Workflows": test_github_actions_syntax,
        "Observability Configurations": test_observability_configs,
        "Healthcare AI Service": test_healthcare_ai_service,
        "Data Drift Detection": test_data_drift_detector,
        "Monitoring Dashboards": test_monitoring_dashboards,
        "Docker Compose Configs": test_docker_compose_configs,
        "Kubernetes Manifests": test_kubernetes_manifests,
    }

    # Run all tests
    results = {}
    for test_name, test_func in tests.items():
        results[test_name] = test_component(test_name, test_func)

    print("\n" + "=" * 50)

    # Generate report
    report = generate_validation_report(results)

    # Print summary
    print(f"📊 VALIDATION SUMMARY")
    print(f"   Total Tests: {report['total_tests']}")
    print(f"   Passed: {report['passed']}")
    print(f"   Failed: {report['failed']}")
    print(f"   Success Rate: {report['success_rate']}")
    print(f"   Overall Status: {report['overall_status']}")

    # Save report
    with open("phase1_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed report saved to: phase1_validation_report.json")

    if report["overall_status"] == "PASSED":
        print("\n🎉 Phase 1 validation PASSED! Ready for Phase 2.")
        return 0
    else:
        print("\n⚠️  Phase 1 validation FAILED. Please fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    exit(main())
