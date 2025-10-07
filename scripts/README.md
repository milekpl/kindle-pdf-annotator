# Diagnostic Scripts

This directory contains diagnostic tools for troubleshooting issues with Kindle coordinate systems, text extraction, and PDF processing.

## When to Use These Scripts

These scripts are useful if you encounter:
- **A newer Kindle device** with a different coordinate system
- **Different text extraction behavior** (ligature handling, hyphenation)
- **Changes in KRDS file format** or structure
- **Import or environment issues**

## Available Scripts

### `diagnose_imports.py`
**Purpose**: Debug Python import issues in the repository.

**Use case**: When you encounter `ModuleNotFoundError` or other import errors.

**Usage**:
```bash
python scripts/diagnose_imports.py
```

**What it checks**:
- Python version
- sys.path configuration
- Module imports
- Available attributes in modules

---

### `debug_krds.py`
**Purpose**: Parse and inspect KRDS files directly to verify coordinate data.

**Use case**: When investigating coordinate issues or annotation placement problems.

**Usage**:
```bash
python scripts/debug_krds.py
```

**What it shows**:
- Total annotations in KRDS file
- Breakdown by type (highlights, notes, bookmarks)
- Coordinate values for bookmarks
- Position validity

---

### `test_pdt_files.py`
**Purpose**: Scan dataset to check if PDT files contain any annotations.

**Use case**: Verify whether PDT files need to be processed (historically they don't contain annotations).

**Usage**:
```bash
python scripts/test_pdt_files.py
```

**What it checks**:
- Scans all PDT files in a dataset
- Reports whether any contain annotation data
- Helps confirm that PDT files can be safely ignored

---

### `find_content_in_pdf.py`
**Purpose**: Search for specific text content within PDF files.

**Use case**: 
- Debugging text extraction issues
- Verifying text matching algorithms
- Testing ligature normalization

**Usage**:
```bash
python scripts/find_content_in_pdf.py
```

**What it does**:
- Searches for text in PDF pages
- Handles text normalization
- Useful for debugging highlight matching issues

---

### `dump_pdf_tokens.py`
**Purpose**: Extract and display raw text tokens from a PDF page.

**Use case**:
- Investigating ligature handling differences between Kindle and PDF
- Debugging text extraction for new PDF formats
- Analyzing character encoding issues

**Usage**:
```bash
python scripts/dump_pdf_tokens.py
```

**What it shows**:
- Raw text extraction from PDF
- Character-by-character breakdown
- Helps identify ligature and encoding issues

---

## Archive Directory

The `archive/` subdirectory contains historical research scripts that were used during the development of the validated coordinate system. These are kept for reference but are not needed for normal operations.

---

## Future Kindle Versions

If Amazon releases a new Kindle with different coordinate behavior:

1. **Start with `debug_krds.py`** - Check the raw KRDS coordinate values
2. **Use `find_content_in_pdf.py`** - Verify text matching still works
3. **Check `dump_pdf_tokens.py`** - Ensure text extraction handles ligatures correctly
4. **Review unit tests** - Run the full test suite to identify specific failures
5. **Refer to `COORDINATE_SYSTEM.md`** - Document current validated formula

The current validated formula is:
```
PDF_points = (KRDS_units / 100) × 72
```

This is based on KRDS using 100 units per inch, and PDF using 72 points per inch.
