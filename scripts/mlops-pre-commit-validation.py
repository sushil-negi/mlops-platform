#!/usr/bin/env python3
"""
MLOps Platform Pre-Commit Validation Script
Runs code quality checks specific to the MLOps platform
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class ValidationResult:
    name: str
    passed: bool
    duration: float
    output: str
    error: Optional[str] = None


class MLOpsPreCommitValidator:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent  # mlops-platform directory
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
            ("black", ["python3", "-m", "black", "--version"]),
            ("isort", ["python3", "-m", "isort", "--version"]),
            ("flake8", ["python3", "-m", "flake8", "--version"]),
            ("mypy", ["python3", "-m", "mypy", "--version"]),
            ("bandit", ["python3", "-m", "bandit", "--version"]),
        ]

        missing_tools = []
        for tool_name, cmd in required_tools:
            success, stdout, stderr = self.run_command(cmd)
            if not success:
                missing_tools.append(tool_name)

        duration = time.time() - start_time

        if missing_tools:
            return ValidationResult(
                name="Environment Validation",
                passed=False,
                duration=duration,
                output="",
                error=f"Missing required tools: {', '.join(missing_tools)}",
            )

        return ValidationResult(
            name="Environment Validation",
            passed=True,
            duration=duration,
            output="All required tools available",
        )

    def check_git_status(self) -> ValidationResult:
        """Check git repository status"""
        start_time = time.time()

        success, stdout, stderr = self.run_command(["git", "status", "--porcelain"])
        duration = time.time() - start_time

        if not success:
            return ValidationResult(
                name="Git Status Check",
                passed=False,
                duration=duration,
                output="",
                error="Failed to check git status",
            )

        file_count = len(stdout.strip().split() if stdout.strip() else [])
        return ValidationResult(
            name="Git Status Check",
            passed=True,
            duration=duration,
            output=f"Git status: {file_count} changed files",
        )

    def run_black_formatting(self) -> ValidationResult:
        """Run Black code formatting check"""
        start_time = time.time()

        cmd = [
            "python3",
            "-m",
            "black",
            "--check",
            "--diff",
            "services/",
            "infrastructure/",
            "scripts/",
        ]
        success, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time

        if not success:
            return ValidationResult(
                name="Black Code Formatting",
                passed=False,
                duration=duration,
                output=f"Formatting issues found:\n{stdout}",
                error="Code formatting issues detected",
            )

        return ValidationResult(
            name="Black Code Formatting",
            passed=True,
            duration=duration,
            output="All files properly formatted",
        )

    def run_import_sorting(self) -> ValidationResult:
        """Run isort import sorting check"""
        start_time = time.time()

        cmd = [
            "python3",
            "-m",
            "isort",
            "--check-only",
            "--diff",
            "services/",
            "infrastructure/",
            "scripts/",
            "--profile=black",
            "--line-length=88",
        ]
        success, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time

        if not success:
            return ValidationResult(
                name="Import Sorting (isort)",
                passed=False,
                duration=duration,
                output=f"Import sorting issues found:\n{stdout}",
                error=stderr if stderr else "Import sorting issues detected",
            )

        return ValidationResult(
            name="Import Sorting (isort)",
            passed=True,
            duration=duration,
            output="All imports properly sorted",
        )

    def run_flake8_linting(self) -> ValidationResult:
        """Run Flake8 linting"""
        start_time = time.time()

        cmd = [
            "python3",
            "-m",
            "flake8",
            "services/",
            "infrastructure/",
            "scripts/",
            "--max-line-length=88",
            "--extend-ignore=E203,W503",
        ]
        success, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time

        if not success:
            lines = stdout.strip().split("\n") if stdout.strip() else []
            return ValidationResult(
                name="Flake8 Linting",
                passed=False,
                duration=duration,
                output=f"Linting issues:\n{stdout[:1000]}"
                + ("... (truncated)" if len(stdout) > 1000 else ""),
                error=f"Found {len(lines)} linting issues",
            )

        return ValidationResult(
            name="Flake8 Linting",
            passed=True,
            duration=duration,
            output="No linting issues found",
        )

    def run_mypy_type_checking(self) -> ValidationResult:
        """Run MyPy type checking"""
        start_time = time.time()

        cmd = [
            "python3",
            "-m",
            "mypy",
            "services/",
            "scripts/",
            "--ignore-missing-imports",
            "--no-strict-optional",
            "--explicit-package-bases",
        ]
        success, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time

        if not success:
            return ValidationResult(
                name="MyPy Type Checking",
                passed=False,
                duration=duration,
                output=f"Type checking issues:\n{stdout}",
                error="Type checking failed",
            )

        return ValidationResult(
            name="MyPy Type Checking",
            passed=True,
            duration=duration,
            output="Type checking passed",
        )

    def run_bandit_security_scan(self) -> ValidationResult:
        """Run Bandit security scan"""
        start_time = time.time()

        cmd = [
            "python3",
            "-m",
            "bandit",
            "-r",
            "services/",
            "infrastructure/",
            "scripts/",
            "-f",
            "json",
            "--exclude",
            "**/tests/**",
        ]
        success, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time

        if not success and "No issues identified" not in stderr:
            try:
                # Try to parse JSON output to get meaningful error info
                if stdout.strip():
                    report = json.loads(stdout)
                    high_issues = [
                        issue
                        for issue in report.get("results", [])
                        if issue.get("issue_confidence") == "HIGH"
                        and issue.get("issue_severity") == "HIGH"
                    ]

                    return ValidationResult(
                        name="Bandit Security Scan",
                        passed=len(high_issues) == 0,
                        duration=duration,
                        output=f"Security scan completed. High-severity issues: "
                        f"{len(high_issues)}",
                        error=(
                            f"Found {len(high_issues)} high-severity security issues"
                            if high_issues
                            else None
                        ),
                    )
            except json.JSONDecodeError:
                pass

            return ValidationResult(
                name="Bandit Security Scan",
                passed=False,
                duration=duration,
                output="",
                error=f"Bandit security scan failed: {stderr}",
            )

        return ValidationResult(
            name="Bandit Security Scan",
            passed=True,
            duration=duration,
            output="No security issues identified",
        )

    def run_comprehensive_validation(self) -> bool:
        """Run all validation checks"""
        print("🚀 Starting MLOps Platform Pre-Commit Validation")
        print("=" * 60)

        # Run all validations
        validations = [
            ("📋 Validating Environment...", self.validate_environment),
            ("🔍 Checking Git Status...", self.check_git_status),
            ("🎨 Running Black Formatting...", self.run_black_formatting),
            ("📦 Running Import Sorting...", self.run_import_sorting),
            ("🔧 Running Flake8 Linting...", self.run_flake8_linting),
            ("🔍 Running MyPy Type Checking...", self.run_mypy_type_checking),
            ("🔒 Running Security Scan...", self.run_bandit_security_scan),
        ]

        for description, validation_func in validations:
            print(description)
            result = validation_func()
            self.results.append(result)

            if result.passed:
                print(f"✅ PASS {result.name} ({result.duration:.2f}s)")
            else:
                print(f"❌ FAIL {result.name} ({result.duration:.2f}s)")
                if result.error:
                    print(f"   Error: {result.error}")
                if result.output and len(result.output) > 0:
                    output_lines = result.output.split("\n")[:10]
                    print("   Output (first 10 lines):")
                    for line in output_lines:
                        print(f"   {line}")
                    output_line_count = len(result.output.split("\n"))
                    if output_line_count > 10:
                        print(f"   ... ({output_line_count - 10} more lines)")

        # Summary
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        total_duration = sum(r.duration for r in self.results)

        print("=" * 60)
        print("🎯 VALIDATION SUMMARY")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {total - passed}")
        print(f"   Duration: {total_duration:.2f}s")

        if passed == total:
            print("\n🎉 ALL VALIDATIONS PASSED")
            print("✅ Ready to commit")
            return True
        else:
            failed_tests = [r.name for r in self.results if not r.passed]
            print(f"\n⚠️  {total - passed} VALIDATION(S) FAILED")
            print("❌ Please fix issues before committing")
            print(f"   Failed tests: {', '.join(failed_tests)}")
            return False


def main():
    """Main validation function"""
    validator = MLOpsPreCommitValidator()
    success = validator.run_comprehensive_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
