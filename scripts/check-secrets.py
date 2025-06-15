#!/usr/bin/env python3
"""
Check staged files for potential secrets and sensitive information
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns to detect potential secrets
SECRET_PATTERNS = [
    # API Keys and tokens
    (r'api[_-]?key[_-]?[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', "API Key"),
    (r'access[_-]?token[_-]?[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', "Access Token"),
    (r'secret[_-]?key[_-]?[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', "Secret Key"),
    (r'auth[_-]?token[_-]?[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', "Auth Token"),
    # Database credentials
    (r'password[_-]?[:=]\s*["\']?[^\s\'"]{8,}["\']?', "Password"),
    (r'db[_-]?pass[_-]?[:=]\s*["\']?[^\s\'"]{8,}["\']?', "Database Password"),
    (r'mysql[_-]?pass[_-]?[:=]\s*["\']?[^\s\'"]{8,}["\']?', "MySQL Password"),
    (r'postgres[_-]?pass[_-]?[:=]\s*["\']?[^\s\'"]{8,}["\']?', "PostgreSQL Password"),
    # Cloud credentials
    (
        r'aws[_-]?secret[_-]?access[_-]?key[_-]?[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?',
        "AWS Secret Key",
    ),
    (
        r'aws[_-]?access[_-]?key[_-]?id[_-]?[:=]\s*["\']?[A-Z0-9]{20}["\']?',
        "AWS Access Key",
    ),
    # Private keys
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----", "Private Key"),
    (r"-----BEGIN\s+OPENSSH\s+PRIVATE KEY-----", "SSH Private Key"),
    # JWTs
    (r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "JWT Token"),
    # Generic high-entropy strings (potential secrets)
    (r'["\'][A-Za-z0-9+/]{32,}={0,2}["\']', "High Entropy String"),
]

# Files to exclude from secret scanning
EXCLUDED_FILES = [
    "*.md",
    "*.txt",
    "*.rst",
    "*.log",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    ".gitignore",
    ".gitattributes",
    "*.json",
    "*.yaml",
    "*.yml",  # Config files often have example values
]

# Safe patterns that should be ignored
SAFE_PATTERNS = [
    r"example[_-]?key",
    r"test[_-]?key",
    r"fake[_-]?key",
    r"sample[_-]?key",
    r"your[_-]?key",
    r"<[^>]+>",  # Template placeholders
    r"\$\{[^}]+\}",  # Environment variable placeholders
    r"xxxxxxxx",
    r"password123",
    r"changeme",
    r"replace[_-]?me",
]


def get_staged_files() -> List[str]:
    """Get list of staged files"""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except subprocess.CalledProcessError:
        return []


def should_scan_file(file_path: str) -> bool:
    """Check if file should be scanned for secrets"""
    path = Path(file_path)

    # Skip binary files
    try:
        with open(path, "r", encoding="utf-8") as f:
            f.read(1024)  # Try to read first 1KB as text
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        return False

    # Skip excluded file patterns
    for pattern in EXCLUDED_FILES:
        if path.match(pattern):
            return False

    return True


def is_safe_match(match_text: str) -> bool:
    """Check if a match is a safe/example value"""
    match_lower = match_text.lower()

    for pattern in SAFE_PATTERNS:
        if re.search(pattern, match_lower, re.IGNORECASE):
            return True

    return False


def scan_file_for_secrets(file_path: str) -> List[Tuple[int, str, str]]:
    """Scan a file for potential secrets"""
    issues: List[Tuple[int, str, str]] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, FileNotFoundError):
        return issues

    for line_num, line in enumerate(lines, 1):
        for pattern, secret_type in SECRET_PATTERNS:
            matches = re.finditer(pattern, line, re.IGNORECASE)

            for match in matches:
                match_text = match.group(0)

                # Skip if it's a safe/example value
                if is_safe_match(match_text):
                    continue

                # Skip comments in code
                if line.strip().startswith("#") or line.strip().startswith("//"):
                    continue

                issues.append(
                    (
                        line_num,
                        secret_type,
                        match_text[:50] + "..." if len(match_text) > 50 else match_text,
                    )
                )

    return issues


def main():
    """Main function to check for secrets in staged files"""
    print("🔍 Checking staged files for secrets...")

    staged_files = get_staged_files()

    if not staged_files:
        print("✅ No staged files to check")
        return 0

    total_issues = 0

    for file_path in staged_files:
        if not should_scan_file(file_path):
            continue

        issues = scan_file_for_secrets(file_path)

        if issues:
            print(f"\n❌ Potential secrets found in {file_path}:")
            for line_num, secret_type, match_text in issues:
                print(f"   Line {line_num}: {secret_type} - {match_text}")
            total_issues += len(issues)

    if total_issues > 0:
        print(f"\n🚨 Found {total_issues} potential secret(s) in staged files!")
        print("\n🔧 To fix:")
        print("   1. Remove or replace secrets with environment variables")
        print("   2. Use configuration files with placeholders")
        print("   3. Add sensitive files to .gitignore")
        print("   4. If false positive, add to SAFE_PATTERNS in check-secrets.py")
        print("\n⚠️  Commit blocked to protect sensitive information")
        return 1
    else:
        print("✅ No secrets detected in staged files")
        return 0


if __name__ == "__main__":
    sys.exit(main())
