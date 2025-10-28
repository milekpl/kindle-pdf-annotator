#!/bin/bash
# Test script for kindle-pdf-annotator from TestPyPI
# Usage: ./test_package.sh [version]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get version
VERSION="$1"
if [ "$VERSION" == "" ]; then
    VERSION=$(grep -oP '__version__ = "\K[^"]+' src/kindle_pdf_annotator/__init__.py)
fi

echo -e "${GREEN}=== Testing kindle-pdf-annotator v${VERSION} from TestPyPI ===${NC}"
echo ""

# Create test directory
TEST_DIR="/tmp/kindle-pdf-annotator-test-$$"
echo -e "${GREEN}Step 1: Creating test environment...${NC}"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
echo "  ✓ Created test directory: $TEST_DIR"

# Create virtual environment
echo -e "${GREEN}Step 2: Creating virtual environment...${NC}"
python3 -m venv test_env
source test_env/bin/activate
echo "  ✓ Virtual environment created and activated"

# Install from TestPyPI
echo -e "${GREEN}Step 3: Installing package from TestPyPI...${NC}"
echo "  (This may take a moment...)"
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple \
    kindle-pdf-annotator==$VERSION || {
    echo -e "${RED}Installation failed!${NC}"
    deactivate
    rm -rf "$TEST_DIR"
    exit 1
}
echo "  ✓ Package installed successfully"

# Test imports
echo -e "${GREEN}Step 4: Testing imports...${NC}"
python -c "import kindle_pdf_annotator" && echo "  ✓ Can import kindle_pdf_annotator" || {
    echo -e "${RED}  ✗ Cannot import kindle_pdf_annotator${NC}"
    deactivate
    rm -rf "$TEST_DIR"
    exit 1
}

# Check version
echo -e "${GREEN}Step 5: Verifying version...${NC}"
INSTALLED_VERSION=$(python -c "from kindle_pdf_annotator import __version__; print(__version__)")
if [ "$INSTALLED_VERSION" == "$VERSION" ]; then
    echo "  ✓ Version matches: $INSTALLED_VERSION"
else
    echo -e "${RED}  ✗ Version mismatch! Expected: $VERSION, Got: $INSTALLED_VERSION${NC}"
    deactivate
    rm -rf "$TEST_DIR"
    exit 1
fi

# Test CLI command
echo -e "${GREEN}Step 6: Testing CLI command...${NC}"
if command -v kindle-pdf-annotator &> /dev/null; then
    kindle-pdf-annotator --help > /dev/null && echo "  ✓ CLI command works" || {
        echo -e "${RED}  ✗ CLI command failed${NC}"
        deactivate
        rm -rf "$TEST_DIR"
        exit 1
    }
else
    echo -e "${RED}  ✗ CLI command not found${NC}"
    deactivate
    rm -rf "$TEST_DIR"
    exit 1
fi

# Test GUI command
echo -e "${GREEN}Step 7: Testing GUI command...${NC}"
if command -v kindle-pdf-annotator-gui &> /dev/null; then
    echo "  ✓ GUI command found"
    echo "  ℹ Skipping GUI execution (requires display)"
else
    echo -e "${RED}  ✗ GUI command not found${NC}"
    deactivate
    rm -rf "$TEST_DIR"
    exit 1
fi

# Test basic functionality
echo -e "${GREEN}Step 8: Testing basic functionality...${NC}"
python << 'PYTHON_TEST'
from kindle_pdf_annotator.kindle_parser import pds_parser, clippings_parser
from kindle_pdf_annotator.pdf_processor import pdf_annotator
from kindle_pdf_annotator.utils import file_utils
print("  ✓ All core modules import successfully")
PYTHON_TEST

# Cleanup
echo -e "${GREEN}Step 9: Cleaning up...${NC}"
deactivate
cd /
rm -rf "$TEST_DIR"
echo "  ✓ Test environment removed"

echo ""
echo -e "${GREEN}=== All Tests Passed! ===${NC}"
echo -e "Package ${GREEN}kindle-pdf-annotator v${VERSION}${NC} is working correctly on TestPyPI"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Check TestPyPI page: https://test.pypi.org/project/kindle-pdf-annotator/${VERSION}/"
echo "  2. Verify screenshots display correctly"
echo "  3. If everything looks good, release to PyPI with: ./release.sh patch pypi"
echo ""
