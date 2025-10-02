# Kindle PDF Annotator - Project Context

## Project Overview

The Kindle PDF Annotator is a Python application that extracts Kindle annotations from PDS (Kindle Reader Data Store) files and embeds them back into the original PDF with pixel-perfect positioning. The project uses a precise Amazon coordinate system to convert Kindle coordinates to PDF coordinates with sub-point accuracy.

### Key Features
- Complete Annotation Support: Extracts and preserves notes, highlights, and bookmarks from Kindle
- Precise Amazon Coordinate System: Converts Kindle coordinates to PDF coordinates with 0.1-0.5 point precision
- Multiple Input Sources: Processes both PDS files (`.pds`) and `MyClippings.txt`
- Accurate Positioning: Uses precise coordinate system with 0.1-0.5 point precision
- Correct Highlight Sizing: Uses actual Kindle annotation dimensions instead of fixed rectangles
- PDF Navigation Bookmarks: Creates real PDF bookmarks visible in all PDF viewers
- GUI and CLI: Both graphical interface and command-line tool available
- Comprehensive Testing: 27 unit tests with high coverage

## Project Structure

```
kindle-pdf-annotator/
├── main.py                        # GUI application entry point
├── cli.py                         # Command-line interface
├── src/
│   ├── kindle_parser/             # Kindle file parsing modules
│   │   ├── amazon_coordinate_system.py    # Core coordinate conversion (Amazon system)
│   │   ├── fixed_clippings_parser.py      # MyClippings.txt parser (working)
│   │   ├── clippings_parser.py            # Legacy clippings parser (for tests)
│   │   ├── krds_parser.py                 # KRDS file parser (notes, highlights, bookmarks)
│   │   ├── pds_parser.py                  # PDS file parser
│   │   └── pdt_parser.py                  # PDT file parser
│   ├── pdf_processor/             # PDF annotation creation
│   │   ├── amazon_to_pdf_adapter.py       # Convert to PDF annotator format
│   │   ├── annotation_mapper.py           # Legacy coordinate mapping
│   │   ├── column_aware_highlighting.py   # Multi-column layout support
│   │   └── pdf_annotator.py               # PDF annotation creation
│   ├── gui/                       # GUI components
│   │   └── main_window.py                 # Main application window
│   └── utils/                     # Utility modules
│       ├── file_utils.py                  # File handling utilities
│       └── location_encoder.py            # Location encoding utilities
├── tests/                         # Unit tests (comprehensive coverage)
├── scripts/                       # Development and debugging tools
├── examples/sample_data/          # Sample Kindle files for testing
└── LICENSE                        # GPL v3 license
```

## Building and Running

### Prerequisites
- Python 3.8+
- Dependencies listed in requirements.txt

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`

### Running the Application

#### GUI Mode
```bash
python main.py
```

#### CLI Mode
```bash
python cli.py --kindle-folder "path/to/book.sdr" --pdf-file "book.pdf" --output "annotated.pdf"
```

#### CLI Options
- `--kindle-folder`: Path to Kindle documents folder (.sdr folder)
- `--pdf-file`: Path to PDF file
- `--output`: Output PDF path
- `--clippings`: Path to MyClippings.txt file (optional)
- `--export-json`: Export annotations to JSON file
- `--verbose`: Verbose output

## Technical Details

### Coordinate System
- Uses Amazon's inches×100 encoding with linear mapping
- Positioning Accuracy: 0.1-0.5 point precision (sub-millimeter level)
- Highlight Sizing: Extracts actual width/height from Kindle position data
- Y-Axis Correction: 7-point adjustment for perfect text alignment

### Core Components

#### Amazon Coordinate System
Located in `src/kindle_parser/amazon_coordinate_system.py`, this module contains the core coordinate conversion utilities that map Kindle coordinates to PDF coordinates using a verified inches × 100 encoding system.

#### PDF Processing
The `src/pdf_processor/` directory contains modules for:
- Converting Amazon annotations to PDF annotator format
- Creating PDF annotations with precise positioning
- Column-aware highlighting for multi-column layouts

#### Kindle Parser
The `src/kindle_parser/` directory handles:
- PDS and PDT file parsing
- KRDS file parsing (notes, highlights, bookmarks)
- MyClippings.txt parsing
- Amazon coordinate system implementation

## Testing

Run all tests:
```bash
python -m pytest tests/ -v
```

Test specific functionality:
```bash
python tests/test_page_9_highlights.py
python tests/test_krds_parser.py
```

## Dependencies

- PyMuPDF (fitz) for PDF processing
- python-dateutil for date parsing
- chardet for character encoding detection
- pillow for image handling
- pytest for testing framework

## License

The project is licensed under GPL v3. This project incorporates and extends GPL-licensed code and research from Kindle annotation parsing algorithms by John Howell.

## Development Conventions

- Python 3.8+ compatibility required
- Modules are organized in the src/ directory with clear separation of concerns
- Testing is done with pytest, with comprehensive coverage of critical functionality
- Coordinate conversion algorithms are precisely implemented with sub-point accuracy
- CLI and GUI interfaces provide the same core functionality with different user experiences