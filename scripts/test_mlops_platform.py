#!/usr/bin/env python3
"""Comprehensive MLOps Platform Integration Test"""

import json
import time
from typing import Dict, List, Tuple

import requests


def test_service_health(service_name: str, port: int) -> bool:
    """Test if a service is healthy"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print(f"✓ {service_name} is healthy")
                return True
        print(f"✗ {service_name} returned unhealthy status")
        return False
    except Exception as e:
        print(f"✗ {service_name} health check failed: {e}")
        return False


def test_service_api(service_name: str, port: int, endpoint: str) -> bool:
    """Test service API endpoint"""
    try:
        response = requests.get(f"http://localhost:{port}{endpoint}", timeout=5)
        if response.status_code == 200:
            print(f"✓ {service_name} API {endpoint} working")
            return True
        else:
            print(f"✗ {service_name} API {endpoint} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ {service_name} API {endpoint} failed: {e}")
        return False


def test_service_docs(service_name: str, port: int) -> bool:
    """Test if service documentation is accessible"""
    try:
        response = requests.get(f"http://localhost:{port}/docs", timeout=5)
        if response.status_code == 200:
            print(f"✓ {service_name} documentation accessible")
            return True
        else:
            print(f"✗ {service_name} docs returned {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ {service_name} docs failed: {e}")
        return False


def test_core_services() -> List[bool]:
    """Test all core MLOps services"""
    print("=== Testing Core MLOps Services ===")

    services = [
        ("MLflow", 5050, "/"),
        ("MinIO Console", 9001, "/"),
        ("PostgreSQL", 5432, None),  # No HTTP endpoint
        ("Redis", 6379, None),  # No HTTP endpoint
    ]

    results = []

    # Test MLflow
    try:
        response = requests.get("http://localhost:5050/health", timeout=5)
        if response.status_code == 200:
            print("✓ MLflow is accessible")
            results.append(True)
        else:
            print("✗ MLflow not accessible")
            results.append(False)
    except:
        print("✗ MLflow connection failed")
        results.append(False)

    # Test MinIO
    try:
        response = requests.get("http://localhost:9001", timeout=5)
        if response.status_code == 200:
            print("✓ MinIO Console is accessible")
            results.append(True)
        else:
            print("✗ MinIO Console not accessible")
            results.append(False)
    except:
        print("✗ MinIO Console connection failed")
        results.append(False)

    # Test Redis
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, db=0)
        r.ping()
        print("✓ Redis is accessible")
        results.append(True)
    except:
        print("✗ Redis connection failed")
        results.append(False)

    # Test PostgreSQL
    try:
        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="mlflow",
            user="mlflow",
            password="mlflow123",
        )
        conn.close()
        print("✓ PostgreSQL is accessible")
        results.append(True)
    except:
        print("✗ PostgreSQL connection failed")
        results.append(False)

    return results


def test_platform_services() -> List[bool]:
    """Test all MLOps platform services"""
    print("\n=== Testing Platform Services ===")

    services = [
        ("Model Registry", 8001, "/models"),
        ("Pipeline Orchestrator", 8002, "/pipelines"),
        ("Feature Store", 8003, "/features"),
        ("Experiment Tracking", 8004, "/experiments"),
    ]

    results = []

    for service_name, port, api_endpoint in services:
        # Test health
        health_ok = test_service_health(service_name, port)

        # Test API
        api_ok = test_service_api(service_name, port, api_endpoint)

        # Test docs
        docs_ok = test_service_docs(service_name, port)

        results.append(health_ok and api_ok and docs_ok)

    return results


def test_monitoring_integration() -> List[bool]:
    """Test monitoring integration"""
    print("\n=== Testing Monitoring Integration ===")

    results = []

    # Test Prometheus
    try:
        response = requests.get("http://localhost:9090/api/v1/targets", timeout=5)
        if response.status_code == 200:
            data = response.json()
            active_targets = len(
                [t for t in data["data"]["activeTargets"] if t["health"] == "up"]
            )
            print(f"✓ Prometheus monitoring {active_targets} targets")
            results.append(True)
        else:
            print("✗ Prometheus not responding")
            results.append(False)
    except:
        print("✗ Prometheus connection failed")
        results.append(False)

    # Test Grafana
    try:
        response = requests.get("http://localhost:3001/api/health", timeout=5)
        if response.status_code == 200:
            print("✓ Grafana is accessible")
            results.append(True)
        else:
            print("✗ Grafana not accessible")
            results.append(False)
    except:
        print("✗ Grafana connection failed")
        results.append(False)

    # Test Alertmanager
    try:
        response = requests.get("http://localhost:9093/api/v2/status", timeout=5)
        if response.status_code == 200:
            print("✓ Alertmanager is accessible")
            results.append(True)
        else:
            print("✗ Alertmanager not accessible")
            results.append(False)
    except:
        print("✗ Alertmanager connection failed")
        results.append(False)

    return results


def test_service_metrics() -> List[bool]:
    """Test if services expose metrics"""
    print("\n=== Testing Service Metrics ===")

    services = [
        ("Model Registry", 8001),
        ("Pipeline Orchestrator", 8002),
        ("Feature Store", 8003),
        ("Experiment Tracking", 8004),
    ]

    results = []

    for service_name, port in services:
        try:
            response = requests.get(f"http://localhost:{port}/metrics", timeout=5)
            if response.status_code == 200 and response.text:
                print(f"✓ {service_name} exposing metrics")
                results.append(True)
            else:
                print(f"✗ {service_name} metrics not available")
                results.append(False)
        except:
            print(f"✗ {service_name} metrics endpoint failed")
            results.append(False)

    return results


def print_service_summary():
    """Print summary of all running services"""
    print("\n=== MLOps Platform Service Summary ===")

    services = [
        (
            "Core Services",
            [
                ("MLflow (Model Tracking)", "http://localhost:5050"),
                ("MinIO (Object Storage)", "http://localhost:9001"),
                ("PostgreSQL (Database)", "localhost:5432"),
                ("Redis (Cache)", "localhost:6379"),
            ],
        ),
        (
            "Platform Services",
            [
                ("Model Registry", "http://localhost:8001/docs"),
                ("Pipeline Orchestrator", "http://localhost:8002/docs"),
                ("Feature Store", "http://localhost:8003/docs"),
                ("Experiment Tracking", "http://localhost:8004/docs"),
            ],
        ),
        (
            "Monitoring Stack",
            [
                ("Prometheus", "http://localhost:9090"),
                ("Grafana", "http://localhost:3001"),
                ("Alertmanager", "http://localhost:9093"),
            ],
        ),
    ]

    for category, service_list in services:
        print(f"\n{category}:")
        for name, url in service_list:
            print(f"  - {name}: {url}")


def main():
    """Run all platform tests"""
    print("🚀 MLOps Platform Integration Test Suite")
    print("=" * 50)

    # Install required packages if needed
    try:
        import psycopg2
        import redis
    except ImportError:
        print("Installing required packages...")
        import subprocess
        import sys

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "redis", "psycopg2-binary"]
        )
        import psycopg2
        import redis

    # Run all tests
    test_results = []

    core_results = test_core_services()
    test_results.extend(core_results)

    platform_results = test_platform_services()
    test_results.extend(platform_results)

    monitoring_results = test_monitoring_integration()
    test_results.extend(monitoring_results)

    metrics_results = test_service_metrics()
    test_results.extend(metrics_results)

    # Summary
    passed = sum(test_results)
    total = len(test_results)

    print(f"\n{'=' * 50}")
    print(f"🎯 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All MLOps platform services are working correctly!")
        print_service_summary()
        return True
    else:
        print("⚠️  Some services need attention")
        failed = total - passed
        print(f"❌ {failed} tests failed")
        return False


if __name__ == "__main__":
    exit(0 if main() else 1)
