#!/bin/bash

# Install Pre-Commit Hook Script
# This script sets up the pre-commit hook to run comprehensive validation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_DIR="$REPO_ROOT/.git"
HOOKS_DIR="$GIT_DIR/hooks"
PRE_COMMIT_HOOK="$HOOKS_DIR/pre-commit"

echo "🔧 Installing Pre-Commit Hook for Enterprise MLOps Healthcare AI"
echo "================================================================"

# Check if we're in a git repository
if [ ! -d "$GIT_DIR" ]; then
    echo "❌ Error: Not in a git repository root"
    echo "   Please run this script from the repository root"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Check if pre-commit hook already exists
if [ -f "$PRE_COMMIT_HOOK" ]; then
    echo "⚠️  Pre-commit hook already exists"
    echo "   Backing up existing hook to pre-commit.backup"
    mv "$PRE_COMMIT_HOOK" "$PRE_COMMIT_HOOK.backup"
fi

# Create the pre-commit hook
cat > "$PRE_COMMIT_HOOK" << 'EOF'
#!/bin/bash

# Enterprise MLOps Healthcare AI Pre-Commit Hook
# Runs comprehensive validation before allowing commits

set -e

echo "🚀 Running Pre-Commit Validation..."
echo "==================================="

# Get the repository root
REPO_ROOT="$(git rev-parse --show-toplevel)"
VALIDATION_SCRIPT="$REPO_ROOT/scripts/pre-commit-validation.py"

# Check if validation script exists
if [ ! -f "$VALIDATION_SCRIPT" ]; then
    echo "❌ Error: Pre-commit validation script not found at $VALIDATION_SCRIPT"
    echo "   Please ensure the validation script is installed"
    exit 1
fi

# Run the validation script
echo "Running comprehensive validation..."
if python3 "$VALIDATION_SCRIPT" --skip-e2e; then
    echo ""
    echo "✅ All validations passed - commit allowed"
    exit 0
else
    echo ""
    echo "❌ Validation failed - commit blocked"
    echo ""
    echo "To fix issues and try again:"
    echo "  1. Fix the reported issues"
    echo "  2. Stage your changes: git add ."
    echo "  3. Try committing again: git commit"
    echo ""
    echo "To run validation manually:"
    echo "  python3 scripts/pre-commit-validation.py"
    echo ""
    echo "To skip validation (NOT RECOMMENDED):"
    echo "  git commit --no-verify"
    exit 1
fi
EOF

# Make the hook executable
chmod +x "$PRE_COMMIT_HOOK"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "📋 What happens now:"
echo "   • Every 'git commit' will run comprehensive validation"
echo "   • Commits will be blocked if validation fails"
echo "   • Use 'git commit --no-verify' to skip (not recommended)"
echo ""
echo "🧪 To test the hook:"
echo "   git add ."
echo "   git commit -m 'test commit'"
echo ""
echo "🔧 To run validation manually:"
echo "   python3 scripts/pre-commit-validation.py"
echo ""
echo "⚙️  Hook installed at: $PRE_COMMIT_HOOK"