#!/usr/bin/env python3
"""
Comprehensive Pre-Commit Validation Script
Mimics the full CI/CD pipeline for local testing before commits
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import tempfile


@dataclass
class ValidationResult:
    name: str
    passed: bool
    duration: float
    output: str
    error: Optional[str] = None


class PreCommitValidator:
    def __init__(self, root_dir: str = None):
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.healthcare_dir = self.root_dir / "healthcare-ai-app"
        self.mlops_dir = self.root_dir / "mlops-platform"
        self.results: List[ValidationResult] = []

    def run_command(
        self, cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.root_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def validate_environment(self) -> ValidationResult:
        """Validate required tools and dependencies"""
        start_time = time.time()

        required_tools = [
            ("python3", ["python3", "--version"]),
            ("docker", ["docker", "--version"]),
            ("docker-compose", ["docker", "compose", "version"]),
            ("pytest", ["python3", "-m", "pytest", "--version"]),
            ("black", ["python3", "-m", "black", "--version"]),
            ("isort", ["python3", "-m", "isort", "--version"]),
            ("flake8", ["python3", "-m", "flake8", "--version"]),
            ("mypy", ["python3", "-m", "mypy", "--version"]),
        ]

        missing_tools = []
        output_lines = []

        for tool_name, cmd in required_tools:
            success, stdout, stderr = self.run_command(cmd)
            if success:
                output_lines.append(f"✓ {tool_name}: {stdout.strip()}")
            else:
                missing_tools.append(tool_name)
                output_lines.append(f"✗ {tool_name}: Missing or failed")

        duration = time.time() - start_time
        passed = len(missing_tools) == 0

        return ValidationResult(
            name="Environment Validation",
            passed=passed,
            duration=duration,
            output="\n".join(output_lines),
            error=(
                f"Missing tools: {', '.join(missing_tools)}" if missing_tools else None
            ),
        )

    def validate_code_quality(self) -> List[ValidationResult]:
        """Run code quality checks (black, isort, flake8, mypy)"""
        results = []

        # Black formatting check
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [
                "python3",
                "-m",
                "black",
                "--check",
                "--diff",
                "healthcare-ai-app/src",
                "healthcare-ai-app/scripts",
                "healthcare-ai-app/tests",
                "mlops-platform/services",
                "mlops-platform/scripts",
            ]
        )
        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="Black Code Formatting",
                passed=success,
                duration=duration,
                output=stdout if success else f"Formatting issues found:\n{stdout}",
                error=stderr if stderr else None,
            )
        )

        # isort import sorting check
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [
                "python3",
                "-m",
                "isort",
                "--check-only",
                "--diff",
                "healthcare-ai-app/src",
                "healthcare-ai-app/scripts",
                "healthcare-ai-app/tests",
                "mlops-platform/services",
                "mlops-platform/scripts",
            ]
        )
        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="Import Sorting (isort)",
                passed=success,
                duration=duration,
                output=stdout if success else f"Import sorting issues found:\n{stdout}",
                error=stderr if stderr else None,
            )
        )

        # Flake8 linting
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [
                "python3",
                "-m",
                "flake8",
                "--max-line-length=88",
                "--extend-ignore=E203,W503",
                "healthcare-ai-app/src",
                "healthcare-ai-app/scripts",
                "healthcare-ai-app/tests",
                "mlops-platform/services",
                "mlops-platform/scripts",
            ]
        )
        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="Flake8 Linting",
                passed=success,
                duration=duration,
                output=(
                    "No linting issues found"
                    if success
                    else f"Linting issues:\n{stdout}"
                ),
                error=stderr if stderr else None,
            )
        )

        # MyPy type checking
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [
                "python3",
                "-m",
                "mypy",
                "--ignore-missing-imports",
                "--no-strict-optional",
                "healthcare-ai-app/src",
                "mlops-platform/services",
            ]
        )
        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="MyPy Type Checking",
                passed=success,
                duration=duration,
                output=(
                    "No type issues found"
                    if success
                    else f"Type checking issues:\n{stdout}"
                ),
                error=stderr if stderr else None,
            )
        )

        return results

    def validate_security(self) -> List[ValidationResult]:
        """Run security checks (bandit, safety)"""
        results = []

        # Bandit security linting
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            [
                "python3",
                "-m",
                "bandit",
                "-r",
                "-f",
                "json",
                "healthcare-ai-app/src",
                "healthcare-ai-app/scripts",
                "mlops-platform/services",
                "mlops-platform/scripts",
            ]
        )
        duration = time.time() - start_time

        if success:
            # Parse bandit JSON output
            try:
                bandit_data = json.loads(stdout)
                high_severity = len(
                    [
                        r
                        for r in bandit_data.get("results", [])
                        if r.get("issue_severity") == "HIGH"
                    ]
                )
                medium_severity = len(
                    [
                        r
                        for r in bandit_data.get("results", [])
                        if r.get("issue_severity") == "MEDIUM"
                    ]
                )

                if high_severity > 0:
                    success = False
                    output = f"Security issues found: {high_severity} HIGH, {medium_severity} MEDIUM severity"
                else:
                    output = f"Security scan passed: {medium_severity} MEDIUM severity issues (allowed)"
            except json.JSONDecodeError:
                output = "Bandit scan completed"
        else:
            output = f"Bandit security scan failed:\n{stdout}"

        results.append(
            ValidationResult(
                name="Bandit Security Scan",
                passed=success,
                duration=duration,
                output=output,
                error=stderr if stderr else None,
            )
        )

        # Safety dependency check
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            ["python3", "-m", "safety", "check", "--json"]
        )
        duration = time.time() - start_time

        if success:
            try:
                safety_data = json.loads(stdout)
                if isinstance(safety_data, list) and len(safety_data) > 0:
                    success = False
                    output = f"Vulnerable dependencies found: {len(safety_data)} issues"
                else:
                    output = "No vulnerable dependencies found"
            except json.JSONDecodeError:
                output = "Safety check completed"
        else:
            output = f"Safety dependency check failed:\n{stdout}"

        results.append(
            ValidationResult(
                name="Safety Dependency Check",
                passed=success,
                duration=duration,
                output=output,
                error=stderr if stderr else None,
            )
        )

        return results

    def validate_unit_tests(self) -> ValidationResult:
        """Run unit tests"""
        start_time = time.time()

        success, stdout, stderr = self.run_command(
            [
                "python3",
                "-m",
                "pytest",
                "tests/unit/",
                "-v",
                "--tb=short",
                "--cov=src",
                "--cov-report=term-missing",
            ],
            cwd=self.healthcare_dir,
        )

        duration = time.time() - start_time

        return ValidationResult(
            name="Unit Tests",
            passed=success,
            duration=duration,
            output=stdout,
            error=stderr if stderr else None,
        )

    def validate_integration_tests(self) -> ValidationResult:
        """Run integration tests"""
        start_time = time.time()

        success, stdout, stderr = self.run_command(
            ["python3", "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
            cwd=self.healthcare_dir,
        )

        duration = time.time() - start_time

        return ValidationResult(
            name="Integration Tests",
            passed=success,
            duration=duration,
            output=stdout,
            error=stderr if stderr else None,
        )

    def validate_healthcare_specific(self) -> List[ValidationResult]:
        """Run healthcare-specific validations"""
        results = []

        # HIPAA compliance check
        start_time = time.time()
        hipaa_script = self.healthcare_dir / "scripts" / "hipaa_compliance_check.py"
        if hipaa_script.exists():
            success, stdout, stderr = self.run_command(
                ["python3", str(hipaa_script)], cwd=self.healthcare_dir
            )
        else:
            success, stdout, stderr = False, "", "HIPAA compliance script not found"

        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="HIPAA Compliance Check",
                passed=success,
                duration=duration,
                output=stdout,
                error=stderr if stderr else None,
            )
        )

        # Crisis detection validation
        start_time = time.time()
        crisis_script = self.healthcare_dir / "tests" / "crisis_detection_validation.py"
        if crisis_script.exists():
            success, stdout, stderr = self.run_command(
                ["python3", str(crisis_script)], cwd=self.healthcare_dir
            )
        else:
            success, stdout, stderr = False, "", "Crisis detection script not found"

        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="Crisis Detection Validation",
                passed=success,
                duration=duration,
                output=stdout,
                error=stderr if stderr else None,
            )
        )

        # Training data validation
        start_time = time.time()
        data_script = self.healthcare_dir / "scripts" / "validate_training_data.py"
        if data_script.exists():
            success, stdout, stderr = self.run_command(
                ["python3", str(data_script)], cwd=self.healthcare_dir
            )
        else:
            success, stdout, stderr = (
                False,
                "",
                "Training data validation script not found",
            )

        duration = time.time() - start_time

        results.append(
            ValidationResult(
                name="Training Data Validation",
                passed=success,
                duration=duration,
                output=stdout,
                error=stderr if stderr else None,
            )
        )

        return results

    def validate_services_health(self) -> List[ValidationResult]:
        """Check if required services are running"""
        results = []

        # Check Docker services
        start_time = time.time()
        success, stdout, stderr = self.run_command(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"]
        )

        duration = time.time() - start_time

        if success:
            required_services = ["postgres", "redis", "minio", "mlflow"]
            running_services = stdout.lower()
            missing_services = [
                svc for svc in required_services if svc not in running_services
            ]

            if missing_services:
                success = False
                output = f"Missing services: {', '.join(missing_services)}\nRunning services:\n{stdout}"
            else:
                output = f"All required services running:\n{stdout}"
        else:
            output = f"Failed to check Docker services:\n{stderr}"

        results.append(
            ValidationResult(
                name="Docker Services Health",
                passed=success,
                duration=duration,
                output=output,
                error=stderr if stderr else None,
            )
        )

        return results

    def validate_e2e_tests(self) -> ValidationResult:
        """Run end-to-end tests (requires services)"""
        start_time = time.time()

        # First check if services are available
        health_check_success, _, _ = self.run_command(
            ["curl", "-f", "http://localhost:8889/health"]
        )

        if not health_check_success:
            return ValidationResult(
                name="E2E Tests",
                passed=False,
                duration=time.time() - start_time,
                output="",
                error="Healthcare AI service not available at localhost:8889",
            )

        success, stdout, stderr = self.run_command(
            ["python3", "-m", "pytest", "tests/e2e/", "-v", "--tb=short"],
            cwd=self.healthcare_dir,
        )

        duration = time.time() - start_time

        return ValidationResult(
            name="E2E Tests",
            passed=success,
            duration=duration,
            output=stdout,
            error=stderr if stderr else None,
        )

    def validate_git_status(self) -> ValidationResult:
        """Check git status for uncommitted changes and sensitive files"""
        start_time = time.time()

        # Check for uncommitted changes
        success, stdout, stderr = self.run_command(["git", "status", "--porcelain"])

        if not success:
            return ValidationResult(
                name="Git Status Check",
                passed=False,
                duration=time.time() - start_time,
                output="",
                error="Failed to check git status",
            )

        sensitive_patterns = ["password", "secret", "key", "token", "credential"]

        issues = []

        # Check staged files for sensitive content
        staged_success, staged_files, _ = self.run_command(
            ["git", "diff", "--cached", "--name-only"]
        )
        if staged_success and staged_files:
            for file_path in staged_files.strip().split("\n"):
                if file_path:
                    # Check file content for sensitive data
                    file_success, file_content, _ = self.run_command(
                        ["git", "show", f":{file_path}"]
                    )
                    if file_success:
                        file_lower = file_content.lower()
                        for pattern in sensitive_patterns:
                            if pattern in file_lower and "example" not in file_lower:
                                issues.append(
                                    f"Potential sensitive data in {file_path}: contains '{pattern}'"
                                )

        duration = time.time() - start_time

        return ValidationResult(
            name="Git Status Check",
            passed=len(issues) == 0,
            duration=duration,
            output=(
                f"Git status clean"
                if len(issues) == 0
                else f"Issues found:\n" + "\n".join(issues)
            ),
            error=None,
        )

    def run_comprehensive_validation(self, skip_e2e: bool = False) -> bool:
        """Run all validation checks"""
        print("🚀 Starting Comprehensive Pre-Commit Validation")
        print("=" * 60)

        # Environment validation
        print("\n📋 Validating Environment...")
        result = self.validate_environment()
        self.results.append(result)
        self._print_result(result)

        if not result.passed:
            print("❌ Environment validation failed. Cannot proceed.")
            return False

        # Git status check
        print("\n🔍 Checking Git Status...")
        result = self.validate_git_status()
        self.results.append(result)
        self._print_result(result)

        # Code quality checks
        print("\n🎨 Running Code Quality Checks...")
        quality_results = self.validate_code_quality()
        self.results.extend(quality_results)
        for result in quality_results:
            self._print_result(result)

        # Security checks
        print("\n🔒 Running Security Checks...")
        security_results = self.validate_security()
        self.results.extend(security_results)
        for result in security_results:
            self._print_result(result)

        # Unit tests
        print("\n🧪 Running Unit Tests...")
        result = self.validate_unit_tests()
        self.results.append(result)
        self._print_result(result)

        # Integration tests
        print("\n🔗 Running Integration Tests...")
        result = self.validate_integration_tests()
        self.results.append(result)
        self._print_result(result)

        # Healthcare-specific validations
        print("\n🏥 Running Healthcare-Specific Validations...")
        healthcare_results = self.validate_healthcare_specific()
        self.results.extend(healthcare_results)
        for result in healthcare_results:
            self._print_result(result)

        # Service health checks
        print("\n🔧 Checking Service Health...")
        service_results = self.validate_services_health()
        self.results.extend(service_results)
        for result in service_results:
            self._print_result(result)

        # E2E tests (optional)
        if not skip_e2e:
            print("\n🌐 Running End-to-End Tests...")
            result = self.validate_e2e_tests()
            self.results.append(result)
            self._print_result(result)

        # Final summary
        self._print_summary()

        return all(result.passed for result in self.results)

    def _print_result(self, result: ValidationResult):
        """Print a single validation result"""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} {result.name} ({result.duration:.2f}s)")

        if not result.passed and result.error:
            print(f"   Error: {result.error}")

        if not result.passed and result.output:
            # Truncate long output
            output_lines = result.output.split("\n")
            if len(output_lines) > 10:
                print(f"   Output (first 10 lines):")
                for line in output_lines[:10]:
                    print(f"   {line}")
                print(f"   ... ({len(output_lines) - 10} more lines)")
            else:
                print(f"   Output: {result.output}")

    def _print_summary(self):
        """Print final validation summary"""
        passed = sum(1 for result in self.results if result.passed)
        total = len(self.results)
        total_duration = sum(result.duration for result in self.results)

        print("\n" + "=" * 60)
        print(f"🎯 VALIDATION SUMMARY")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {total - passed}")
        print(f"   Duration: {total_duration:.2f}s")

        if passed == total:
            print("\n🎉 ALL VALIDATIONS PASSED!")
            print("✅ Ready to commit")
        else:
            print(f"\n⚠️  {total - passed} VALIDATION(S) FAILED")
            print("❌ Please fix issues before committing")

            # List failed tests
            failed_tests = [result.name for result in self.results if not result.passed]
            print(f"   Failed tests: {', '.join(failed_tests)}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Pre-commit validation script")
    parser.add_argument("--skip-e2e", action="store_true", help="Skip end-to-end tests")
    parser.add_argument("--root-dir", help="Root directory of the project")

    args = parser.parse_args()

    validator = PreCommitValidator(args.root_dir)
    success = validator.run_comprehensive_validation(skip_e2e=args.skip_e2e)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
