#!/bin/bash

# MLOps Platform Pre-Commit Hook Installer
# This script installs a Git pre-commit hook that runs MLOps-specific validations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_FILE="$REPO_ROOT/.git/hooks/pre-commit"

echo "🔧 Installing MLOps Platform Pre-Commit Hook"
echo "============================================"

# Check if we're in a git repository
if [ ! -d "$REPO_ROOT/.git" ]; then
    echo "❌ Error: Not in a Git repository root"
    echo "   Please run this script from the mlops-platform directory"
    exit 1
fi

# Create the pre-commit hook
cat > "$HOOK_FILE" << 'EOF'
#!/bin/bash

# MLOps Platform Pre-Commit Hook
# Runs comprehensive validation before allowing commits

echo "🚀 Running MLOps Platform Pre-Commit Validation..."

# Change to the repository root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Run the MLOps validation script
python3 scripts/mlops-pre-commit-validation.py

# Check the exit code
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Pre-commit validation failed!"
    echo "   Please fix the issues above before committing."
    echo "   To bypass this check (not recommended), use: git commit --no-verify"
    exit 1
fi

echo ""
echo "✅ All validations passed! Proceeding with commit..."
EOF

# Make the hook executable
chmod +x "$HOOK_FILE"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "📋 What this hook does:"
echo "   • Runs Black code formatting checks"
echo "   • Validates import sorting with isort"
echo "   • Performs Flake8 linting"
echo "   • Runs MyPy type checking"
echo "   • Executes Bandit security scans"
echo ""
echo "🎯 Usage:"
echo "   • Normal commits will automatically run validation"
echo "   • To bypass validation: git commit --no-verify"
echo "   • To run validation manually: python3 scripts/mlops-pre-commit-validation.py"
echo ""
echo "🔧 To uninstall this hook:"
echo "   rm $HOOK_FILE"