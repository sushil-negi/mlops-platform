#!/usr/bin/env python3
"""
Security validation script to check for hardcoded credentials.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Common default passwords and credentials to check for
FORBIDDEN_PATTERNS = [
    (r"mlflow123", "Hardcoded MLflow password"),
    (r"mlops123", "Hardcoded MLOps password"),
    (r"minioadmin", "Default MinIO username"),
    (r"minioadmin123", "Default MinIO password"),
    (r"admin123", "Common default admin password"),
    (r"password123", "Common weak password"),
    (r"postgres123", "Common PostgreSQL password"),
    (r"redis123", "Common Redis password"),
    (r"grafana123", "Common Grafana password"),
    (r"dev123", "Common development password"),
    (r"test123", "Common test password"),
    (r"demo123", "Common demo password"),
    # Base64 encoded versions of common passwords
    (r"bWxmbG93MTIz", "Base64 encoded mlflow123"),
    (r"bWluaW9hZG1pbg==", "Base64 encoded minioadmin"),
    (r"bWluaW9hZG1pbjEyMw==", "Base64 encoded minioadmin123"),
    # Patterns that might indicate hardcoded credentials
    (
        r'password\s*=\s*["\'](?!.*\$\{)(?!.*CHANGE_ME)'
        r'(?!.*PLACEHOLDER)[^"\']+["\']',
        "Potential hardcoded password",
    ),
    (
        r'secret\s*=\s*["\'](?!.*\$\{)(?!.*CHANGE_ME)' r'(?!.*PLACEHOLDER)[^"\']+["\']',
        "Potential hardcoded secret",
    ),
]

# File extensions to check
CHECK_EXTENSIONS = [".py", ".yaml", ".yml", ".sql", ".sh", ".env", ".json", ".md"]

# Directories to skip
SKIP_DIRS = [".git", "__pycache__", "node_modules", ".pytest_cache", "venv", ".env"]

# Files to skip
SKIP_FILES = [".env.example", "security-check.py"]


def check_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Check a single file for security issues."""
    issues = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            for pattern, description in FORBIDDEN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's a comment, example, or test-only credential
                    if any(
                        skip in line.upper()
                        for skip in [
                            "#",
                            "//",
                            "CHANGE_ME",
                            "PLACEHOLDER",
                            "EXAMPLE",
                            "TEST ONLY",
                            "CI ONLY",
                            "TESTING",
                        ]
                    ):
                        continue
                    # Skip test files and CI workflows for certain patterns
                    if any(
                        test_file in str(file_path).lower()
                        for test_file in ["test", "ci.yml", "github/workflows"]
                    ):
                        if any(
                            test_pattern in pattern
                            for test_pattern in ["test123", "minioadmin"]
                        ):
                            continue
                    issues.append((line_num, description, line.strip()))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return issues


def scan_directory(directory: Path) -> dict:
    """Scan directory for security issues."""
    all_issues = {}

    for root, dirs, files in os.walk(directory):
        # Skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            # Skip files
            if file in SKIP_FILES:
                continue

            file_path = Path(root) / file

            # Check only specific extensions
            if any(file_path.suffix == ext for ext in CHECK_EXTENSIONS):
                issues = check_file(file_path)
                if issues:
                    all_issues[str(file_path)] = issues

    return all_issues


def main():
    """Main security check function."""
    print("🔒 MLOps Platform Security Check")
    print("=" * 50)

    # Get the repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Scanning: {repo_root}")
    print()

    # Scan for issues
    issues = scan_directory(repo_root)

    if not issues:
        print("✅ No security issues found!")
        print()
        print("All hardcoded credentials have been removed.")
        return 0

    # Report issues
    print(f"❌ Found security issues in {len(issues)} files:")
    print()

    total_issues = 0
    for file_path, file_issues in issues.items():
        print(f"📄 {file_path}")
        for line_num, description, line_content in file_issues:
            print(f"   Line {line_num}: {description}")
            print(f"   > {line_content[:80]}...")
            total_issues += 1
        print()

    print(f"Total issues found: {total_issues}")
    print()
    print("⚠️  Please fix these security issues before production!")
    print()
    print("Recommendations:")
    print("1. Replace hardcoded passwords with environment variables")
    print("2. Use .env files for local development (never commit them)")
    print("3. Use external secret management for K8s")
    print("4. Follow the patterns in .env.example")

    return 1


if __name__ == "__main__":
    sys.exit(main())
