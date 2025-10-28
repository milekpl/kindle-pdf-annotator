# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-26

### Added
- Initial PyPI release
- Complete annotation support for notes, highlights, and bookmarks from Kindle
- Intelligent note/highlight unification based on position matching
- Text-based matching with comprehensive ligature handling
- Language-independent ligature support (f-ligatures, st-ligatures, ae-ligatures, oe-ligatures)
- Fuzzy matching fallback using Levenshtein distance (85% threshold)
- Precise Amazon coordinate system for sub-point accuracy annotation placement
- Multiple input sources: PDS files (.pds) and MyClippings.txt support
- Accurate positioning using Amazon's inches×100 encoding
- Correct highlight sizing using actual Kindle annotation dimensions
- PDF navigation bookmarks visible in all PDF viewers
- Both GUI and CLI interfaces
- Comprehensive testing: 138 unit tests covering all major functionality
- Support for multi-line and multi-column highlights
- Complex "snake" highlight pattern support
- CropBox-aware coordinate conversion

### Technical Details
- Validated coordinate conversion formula: `PDF_points = (KRDS_units / 100) × 72`
- Median positioning error: 10.94 pts (0.15 inches) validated on 346 real highlights
- Supports Python 3.8+
- Uses PyMuPDF for PDF processing
- Cross-platform: Windows, macOS, Linux

### Package Structure
- Proper PyPI packaging with pyproject.toml (PEP 621)
- Console scripts: `kindle-pdf-annotator` (CLI) and `kindle-pdf-annotator-gui` (GUI)
- Comprehensive documentation and examples
- Full test suite included

[1.0.0]: https://github.com/milekpl/kindle-pdf-annotator/releases/tag/v1.0.0
