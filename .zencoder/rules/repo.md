---
description: Repository Information Overview
alwaysApply: true
---

# Kindle PDF Annotator Information

## Summary
A Python application that extracts Kindle annotations from PDS files and embeds them back into the original PDF with pixel-perfect positioning. It supports notes, highlights, and bookmarks with precise coordinate conversion from Kindle's coordinate system to PDF coordinates.

## Structure
- **src/kindle_parser/**: Kindle file parsing modules for different file formats
- **src/pdf_processor/**: PDF annotation creation and coordinate conversion
- **src/gui/**: GUI components for the application
- **src/utils/**: Utility modules for file handling and location encoding
- **tests/**: Comprehensive unit tests with high coverage
- **scripts/**: Development and debugging tools
- **examples/sample_data/**: Sample Kindle files for testing

## Language & Runtime
**Language**: Python
**Version**: 3.8+
**Build System**: setuptools
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- PyMuPDF (fitz) >= 1.23.0 - PDF processing
- python-dateutil >= 2.8.2 - Date handling
- chardet >= 5.2.0 - Character encoding detection
- pillow >= 10.0.0 - Image processing

**Development Dependencies**:
- pytest >= 7.4.0 - Testing framework

## Build & Installation
```bash
# Clone the repository
git clone <repository-url>

# Install dependencies
pip install -r requirements.txt

# Install as a package (optional)
pip install -e .
```

## Main Entry Points
**GUI Mode**:
```bash
python main.py
```

**CLI Mode**:
```bash
python cli.py --kindle-folder "path/to/book.sdr" --pdf-file "book.pdf" --output "annotated.pdf"
```

## Testing
**Framework**: pytest
**Test Location**: tests/ directory
**Naming Convention**: test_*.py
**Run Command**:
```bash
python -m pytest tests/ -v

# Test specific functionality
python tests/test_page_9_highlights.py
python tests/test_krds_parser.py
```

## Key Features
- Complete annotation support (notes, highlights, bookmarks)
- Precise Amazon coordinate system conversion
- Multiple input sources (PDS files, MyClippings.txt)
- Accurate positioning with 0.1-0.5 point precision
- Correct highlight sizing using actual Kindle dimensions
- PDF navigation bookmarks
- Both GUI and CLI interfaces