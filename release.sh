#!/bin/bash
set -e

echo -e "\033[1;34m[INFO]\033[0m Preparing release..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "\033[1;31m[ERROR]\033[0m Not in a git repository"
    exit 1
fi

# Check if we have uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "\033[1;33m[WARNING]\033[0m You have uncommitted changes. Consider committing them first."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get current version
current_version=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
echo -e "\033[1;34m[INFO]\033[0m Current version: $current_version"

# Ask for new version
read -p "Enter new version (or press Enter to keep $current_version): " new_version
if [ -z "$new_version" ]; then
    new_version=$current_version
fi

# Update version in pyproject.toml
echo -e "\033[1;34m[INFO]\033[0m Updating version to $new_version..."
sed -i.bak "s/version = \"$current_version\"/version = \"$new_version\"/" pyproject.toml
rm pyproject.toml.bak

# Update version in __init__.py
echo -e "\033[1;34m[INFO]\033[0m Updating __init__.py..."
sed -i.bak "s/__version__ = \"$current_version\"/__version__ = \"$new_version\"/" src/commit_gpt/__init__.py
rm src/commit_gpt/__init__.py.bak

# Build the package
echo -e "\033[1;34m[INFO]\033[0m Building package..."
python -m build

# Test the build
echo -e "\033[1;34m[INFO]\033[0m Testing build..."
python -m twine check dist/*

echo -e "\033[1;32m[SUCCESS]\033[0m Build completed successfully!"
echo ""
echo "Next steps:"
echo "1. Test the package: pip install dist/commit_gpt-$new_version-py3-none-any.whl"
echo "2. Upload to PyPI: python -m twine upload dist/*"
echo "3. Create git tag: git tag v$new_version && git push origin v$new_version"
echo ""
echo "To upload to PyPI, run:"
echo "  python -m twine upload dist/*"
