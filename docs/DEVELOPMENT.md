# Development Setup Guide

Quick guide for setting up a development environment for kindle-pdf-annotator.

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/milekpl/kindle-pdf-annotator.git
   cd kindle-pdf-annotator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   # Install package in editable mode with dev dependencies
   pip install -e ".[dev]"
   
   # Or install from requirements.txt
   pip install -r requirements.txt
   pip install pytest build twine
   ```

## Running the Application

### GUI Mode
```bash
# Using the installed console script
kindle-pdf-annotator-gui

# Or directly
python -m kindle_pdf_annotator.main
```

### CLI Mode
```bash
# Using the installed console script
kindle-pdf-annotator --help

# Or directly
python -m kindle_pdf_annotator.cli --help
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_integration_end_to_end.py -v

# Run with coverage
pytest tests/ --cov=kindle_pdf_annotator --cov-report=html
```

## Making Changes

1. **Make your changes** in `src/kindle_pdf_annotator/`
2. **Run tests** to ensure nothing breaks
3. **Update documentation** if needed
4. **Commit changes** with descriptive messages

## Before Submitting

1. Ensure all tests pass
2. Update CHANGELOG.md if adding features
3. Follow existing code style
4. Add tests for new functionality

## Package Structure After Setup

```
src/kindle_pdf_annotator/
├── __init__.py           # Package metadata and version
├── main.py              # GUI entry point
├── cli.py               # CLI entry point
├── gui/                 # GUI components
├── kindle_parser/       # Kindle file parsing
├── pdf_processor/       # PDF annotation creation
└── utils/               # Utility functions
```

## Useful Commands

```bash
# Format code (if using black)
black src/

# Type checking (if using mypy)
mypy src/

# Build package locally
python -m build

# Check package
twine check dist/*

# Clean build artifacts
rm -rf build/ dist/ *.egg-info src/*.egg-info
```
