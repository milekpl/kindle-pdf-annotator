#!/bin/bash
# Release script for kindle-pdf-annotator
# Usage: ./release.sh [patch|minor|major] [testpypi|pypi]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VERSION_BUMP="patch"
TARGET="testpypi"

# Parse arguments
if [ "$1" != "" ]; then
    VERSION_BUMP="$1"
fi

if [ "$2" != "" ]; then
    TARGET="$2"
fi

echo -e "${GREEN}=== Kindle PDF Annotator Release Script ===${NC}"
echo -e "Version bump: ${YELLOW}${VERSION_BUMP}${NC}"
echo -e "Target: ${YELLOW}${TARGET}${NC}"
echo ""

# Get current version from __init__.py
CURRENT_VERSION=$(grep -oP '__version__ = "\K[^"]+' src/kindle_pdf_annotator/__init__.py)
echo -e "Current version: ${YELLOW}${CURRENT_VERSION}${NC}"

# Calculate new version
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

case $VERSION_BUMP in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo -e "${RED}Error: Invalid version bump type. Use: patch, minor, or major${NC}"
        exit 1
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
echo -e "New version: ${GREEN}${NEW_VERSION}${NC}"
echo ""

# Confirm
read -p "Continue with release? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Release cancelled${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Updating version numbers...${NC}"
# Update version in __init__.py
sed -i "s/__version__ = \"${CURRENT_VERSION}\"/__version__ = \"${NEW_VERSION}\"/" src/kindle_pdf_annotator/__init__.py
echo "  ✓ Updated src/kindle_pdf_annotator/__init__.py"

# Update version in pyproject.toml
sed -i "s/^version = \"${CURRENT_VERSION}\"/version = \"${NEW_VERSION}\"/" pyproject.toml
echo "  ✓ Updated pyproject.toml"

echo -e "${GREEN}Step 2: Running tests...${NC}"
if command -v pytest &> /dev/null; then
    python -m pytest tests/ -v || {
        echo -e "${RED}Tests failed! Reverting changes...${NC}"
        git checkout src/kindle_pdf_annotator/__init__.py pyproject.toml
        exit 1
    }
    echo "  ✓ All tests passed"
else
    echo -e "${YELLOW}  ! pytest not found, skipping tests${NC}"
fi

echo -e "${GREEN}Step 3: Cleaning old build artifacts...${NC}"
rm -rf build/ dist/ *.egg-info src/*.egg-info
echo "  ✓ Cleaned build artifacts"

echo -e "${GREEN}Step 4: Building package...${NC}"
python -m build || {
    echo -e "${RED}Build failed! Reverting changes...${NC}"
    git checkout src/kindle_pdf_annotator/__init__.py pyproject.toml
    exit 1
}
echo "  ✓ Package built successfully"

echo -e "${GREEN}Step 5: Validating package...${NC}"
python -m twine check dist/* || {
    echo -e "${RED}Validation failed!${NC}"
    exit 1
}
echo "  ✓ Package validation passed"

echo -e "${GREEN}Step 6: Uploading to ${TARGET}...${NC}"
if [ "$TARGET" == "testpypi" ]; then
    python -m twine upload --repository testpypi dist/*
    PACKAGE_URL="https://test.pypi.org/project/kindle-pdf-annotator/${NEW_VERSION}/"
else
    python -m twine upload dist/*
    PACKAGE_URL="https://pypi.org/project/kindle-pdf-annotator/${NEW_VERSION}/"
fi
echo "  ✓ Package uploaded successfully"

echo -e "${GREEN}Step 7: Committing changes...${NC}"
git add src/kindle_pdf_annotator/__init__.py pyproject.toml
git commit -m "Release v${NEW_VERSION}"
echo "  ✓ Changes committed"

echo -e "${GREEN}Step 8: Creating git tag...${NC}"
git tag "v${NEW_VERSION}"
echo "  ✓ Tag v${NEW_VERSION} created"

echo ""
echo -e "${GREEN}=== Release Complete! ===${NC}"
echo -e "Version: ${GREEN}${NEW_VERSION}${NC}"
echo -e "Package URL: ${GREEN}${PACKAGE_URL}${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Push commits: git push origin main"
echo "  2. Push tags: git push origin v${NEW_VERSION}"
if [ "$TARGET" == "testpypi" ]; then
    echo "  3. Test the package with: ./test_package.sh ${NEW_VERSION}"
    echo "  4. If tests pass, release to PyPI: ./release.sh patch pypi"
fi
echo ""
