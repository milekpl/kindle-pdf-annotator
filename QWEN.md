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

## Learning Mode for Text Matching Analysis

The application now includes a learning mode that helps identify and analyze text matching issues in the annotation process. This mode is designed to:

1. **Capture unmatched clippings**: When text matching fails during annotation processing, the system exports the unmatched clipping along with contextual text from the PDF.

2. **Export contextual data**: For each failed match, the system exports:
   - The original clipping text that failed to match
   - The contextual text from the PDF (500+ characters around the expected match position)
   - Metadata about the book and page where matching failed

3. **Generate analysis JSON**: The exported data is saved to a JSON file that can be used for further analysis.

### How Learning Mode Works

The learning mode operates as follows:

1. When processing a book with MyClippings.txt and a PDF, the system attempts text-based matching as usual
2. For each clipping that fails to match with the current matching algorithm, the system:
   - Saves the clipping text and relevant PDF context
   - Records the failure with details about what was attempted
   - Collects this data for analysis
3. After processing, a JSON file is exported containing all unmatched clippings with context

### Running Learning Mode

To use the learning mode, run the CLI with the `--learn` option:

```bash
python cli.py --learn --learn-output "learning_data.json" --kindle-folder "path/to/book.sdr" --pdf-file "book.pdf" --clippings "MyClippings.txt"
```

### Analysis Scripts

The project includes several scripts for analyzing the learning data:

1. **diff_analysis.py**: Compares unmatched clippings with their PDF context to identify patterns in text differences
2. **frequency_transformations.py**: Analyzes differences to identify common transformations needed for better matching
3. **process_learning_directory.py**: Processes multiple books in a directory to gather comprehensive learning data

### Expected Output

The frequency analysis script produces a sorted list of transformations that could improve text matching, such as:
- Whitespace normalization patterns
- Special character handling
- Ligature replacements
- Hyphenation handling
- Text normalization rules

### Using the Scripts

To use the learning mode in practice:

1. **Collect data**: Use `process_learning_directory.py` to process multiple PDFs and KRDS files:
   ```bash
   python scripts/process_learning_directory.py /path/to/learn/directory
   ```
   Note: Files starting with "._" (hidden system files) will be ignored.

2. **Analyze differences**: Use `diff_analysis.py` to analyze the unmatched clippings:
   ```bash
   python scripts/diff_analysis.py learning_output/combined_learning_data.json
   ```

3. **Identify transformations**: Use `frequency_transformations.py` to get suggestions for improving text matching:
   ```bash
   python scripts/frequency_transformations.py learning_output/combined_learning_data.json
   ```

4. **Run the full workflow**: Use the `run_learning_mode.sh` script to execute the complete learning workflow:
   ```bash
   bash scripts/run_learning_mode.sh
   ```
   This script assumes your learning files are in `./learn/documents` and will create output in `./learning_output`.
   Note: PDF files starting with "._" (hidden system files) will be ignored.

## License

The project is licensed under GPL v3. This project incorporates and extends GPL-licensed code and research from Kindle annotation parsing algorithms by John Howell.

## Development Conventions

- Python 3.8+ compatibility required
- Modules are organized in the src/ directory with clear separation of concerns
- Testing is done with pytest, with comprehensive coverage of critical functionality
- Coordinate conversion algorithms are precisely implemented with sub-point accuracy
- CLI and GUI interfaces provide the same core functionality with different user experiences