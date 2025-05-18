#!/bin/bash
# setup_hooks.sh - Automatically configure git hooks for logging standards enforcement
#
# This script configures the local git repository to use our custom hooks directory
# (.githooks), ensuring that all logging standards are enforced on commit.
#
# Run this script once after cloning the repository to enable automatic validation.

# Ensure we're in the project root
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR" || { echo "Error: Could not navigate to project directory"; exit 1; }

# Set up the git hooks directory
echo "Setting up git hooks..."
git config core.hooksPath .githooks

# Ensure the pre-commit hook is executable
chmod +x .githooks/pre-commit

# Verify the setup
if [ "$(git config core.hooksPath)" = ".githooks" ]; then
    echo "✅ Git hooks successfully configured!"
    echo "Logging standards will now be automatically enforced on commit."
else
    echo "❌ Error: Failed to configure git hooks."
    echo "Please run: git config core.hooksPath .githooks"
    exit 1
fi

# Print readme
echo ""
echo "===== Football Match Tracking System ====="
echo "Logging standards will be automatically enforced when you commit code."
echo "Run the following command to test the logging enforcement:"
echo "  python3 tools/enforce_logging_standards.py"
echo ""
echo "For more information about the logging standards, see:"
echo "  LOGGING_SYSTEM_RULES.md"
echo "=========================================="
