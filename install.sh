#!/bin/bash

# Commit-GPT Installation Script

set -e

echo -e "\033[1;34m[INFO]\033[0m Installing Commit-GPT..."

# Check if Python 3.11+ is available
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "\033[1;31m[ERROR]\033[0m Python 3.11 or higher is required. Found: $python_version"
    exit 1
fi

echo -e "\033[1;32m[OK]\033[0m Python version: $python_version"

# Install the package
echo -e "\033[1;34m[INFO]\033[0m Installing commit-gpt..."
pip install -e .

# Create cache directory
echo -e "\033[1;34m[INFO]\033[0m Creating cache directory..."
mkdir -p ~/.commit-gpt

# Check for API keys
echo -e "\033[1;34m[INFO]\033[0m Checking for API keys..."
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "\033[1;33m[WARNING]\033[0m No API keys found. You'll need to set one:"
    echo ""
    echo "Option 1 - Environment variables:"
    echo "   export OPENAI_API_KEY='your-openai-api-key'"
    echo "   # or"
    echo "   export ANTHROPIC_API_KEY='your-anthropic-api-key'"
    echo ""
    echo "Option 2 - .env file (recommended):"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your API key"
    echo ""
    echo "Without an API key, commit-gpt will use offline heuristics only."
else
    echo -e "\033[1;32m[OK]\033[0m API key found"
fi

# Test installation
echo -e "\033[1;34m[INFO]\033[0m Testing installation..."
if command -v commit-gpt &> /dev/null; then
    echo -e "\033[1;32m[OK]\033[0m commit-gpt command is available"
else
    echo -e "\033[1;31m[ERROR]\033[0m commit-gpt command not found. Try:"
    echo "   python -m commit_gpt.cli"
fi

echo ""
echo -e "\033[1;32m[SUCCESS]\033[0m Installation complete!"
echo ""
echo "Usage:"
echo "  commit-gpt                    # Generate commit message"
echo "  commit-gpt --write           # Write commit directly"
echo "  commit-gpt --style casual    # Use casual style"
echo "  commit-gpt --explain         # Show explanation"
echo "  commit-gpt --risk-check      # Check for risks"
echo "  commit-gpt --suggest-groups  # Split large diffs into multiple commits"
echo ""
echo "For more options: commit-gpt --help"
