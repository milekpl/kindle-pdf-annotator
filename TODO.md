# TODO - Coordinate System Implementation

## ✅ COMPLETED - Priority 1: CropBox Handling and Coordinate System

### Implementation Summary (October 7, 2025)
All core coordinate system fixes have been successfully implemented and tested:

1. **Coordinate Conversion Formula**
   - ✅ Replaced calibrated transformation with validated inches-based formula
   - ✅ Formula: `PDF_points = (KRDS_units / 100) × 72`
   - ✅ Applied to X, Y, width, and height conversions
   - ✅ Removed cryptic "H1" terminology, using "inches-based formula"

2. **CropBox Support**
   - ✅ Added CropBox parameter to all conversion functions
   - ✅ Automatic offset subtraction for cropped PDFs
   - ✅ Page-specific CropBox retrieval during processing
   - ✅ Bounds clamping to visible page dimensions
   - ✅ CropBox offset detection and logging

3. **Testing**
   - ✅ Created comprehensive unit test suite (`test_cropbox_coordinate_conversion.py`)
   - ✅ 7 test cases covering: normal PDFs, cropped PDFs, bounds clamping, zero coords
   - ✅ All 41 core tests passing
   - ✅ Validated on realistic coordinate values

4. **Cleanup**
   - ✅ Archived outdated research markdown files to `docs/archive/`
   - ✅ Moved research scripts to `scripts/archive/`
   - ✅ Updated README.md with coordinate system section
   - ✅ Created COORDINATE_SYSTEM.md technical documentation

### Files Modified
- `src/kindle_parser/amazon_coordinate_system.py` - Core implementation
- `tests/test_cropbox_coordinate_conversion.py` - New unit tests (7 tests)
- `README.md` - Added coordinate system documentation
- `COORDINATE_SYSTEM.md` - New technical reference
- `TODO.md` - This file

### Test Results
```
✅ 7/7 CropBox coordinate conversion tests passing
✅ 41/42 total core tests passing (1 skipped)
✅ All deduplication tests passing
✅ All KRDS parser tests passing
```

---

## ✅ COMPLETED - Priority 2: Note/Highlight Unification

### Implementation Summary (October 7, 2025)
Successfully implemented unification of notes and highlights that share the same position:

1. **Unification Logic**
   - ✅ Notes and highlights at same position (within 0.15 pt tolerance) are unified
   - ✅ Note is kept (has content), highlight is removed
   - ✅ Position tolerance: ±0.15 points for both X and Y coordinates
   - ✅ Proximity matching instead of exact position matching
   - ✅ Bookmarks remain separate, not unified with notes/highlights

2. **Implementation Details**
   - ✅ Modified `_deduplicate_annotations()` in `amazon_coordinate_system.py`
   - ✅ Replaced dict-based position tracking with list-based proximity search
   - ✅ Added debug logging for unified annotations
   - ✅ Preserves existing deduplication logic for other cases

3. **Testing**
   - ✅ Created comprehensive unit test suite (`test_note_highlight_unification.py`)
   - ✅ 9 test cases covering:
     - Same position unification (note preferred)
     - Near coordinates (within tolerance) unified
     - Different pages/positions kept separate
     - Multiple notes at same position
     - Content preservation
     - Mixed annotation scenarios
   - ✅ All 9 unification tests passing
   - ✅ Updated existing deduplication test expectations
   - ✅ All 64 core tests passing (1 skipped)

### Files Modified
- `src/kindle_parser/amazon_coordinate_system.py` - Unification logic in `_deduplicate_annotations()`
- `tests/test_note_highlight_unification.py` - New unit tests (9 tests)
- `tests/test_deduplication.py` - Updated test expectations for new behavior
- `TODO.md` - This file

### Test Results
```
✅ 9/9 Note/highlight unification tests passing
✅ 7/7 CropBox coordinate conversion tests passing
✅ 64/65 total tests passing (1 skipped)
✅ All deduplication tests passing
✅ All KRDS parser tests passing
```

### Key Features
- **Smart Proximity Matching**: Uses 0.15 pt tolerance to handle slight coordinate variations
- **Content Preservation**: Always keeps note (which has user content) when unified
- **Backward Compatible**: Existing exact-duplicate detection still works
- **Debug Output**: Logs unification events for transparency

---

## ⏳ Priority 3: Cleanup and Documentation

### Code Cleanup
- ✅ **test_text_matching_strategies.py**: Removed hypothetical implementations, now uses production functions only
  - Removed duplicate `normalize_text()` implementations
  - Removed hypothetical `word_based_reverse_search()` implementation
  - Removed hypothetical `current_fixed_length_search()` implementation
  - Removed hypothetical `hybrid_search()` implementation
  - Now imports and tests production functions from `amazon_coordinate_system.py`
  - All 29 tests passing with production code

- ✅ **Fixed import errors in 5 test files**: Corrected obsolete `fixed_clippings_parser` imports
  - `test_highlight_width_coverage.py` - fixed import ✅
  - `test_peirce_text_coverage.py` - fixed import ✅
  - `test_krds_page_numbers.py` - fixed import ✅
  - `test_krds_offset_verification.py` - fixed import ✅
  - `test_two_column_pdf.py` - fixed import ✅
  - All 4 previously broken tests now passing

- ✅ **Renamed and updated test_all_three_pdfs.py → test_all_example_pdfs.py**
  - Now tests all 4 example PDFs (not just 3)
  - Added Shea Page 136 (CropBox example) to test suite
  - All 4 PDFs tested successfully:
    - Peirce - The Fixation of Belief (8 highlights)
    - Theatre Hunger Paper (7 highlights)
    - 659ec7697e419 (4 highlights)
    - Shea Page 136 - CropBox Example (1 highlight)

- ✅ **Cleaned up scripts/ directory - removed 38 one-off analysis scripts**
  - Kept 5 diagnostic tools useful for future Kindle versions:
    - `debug_krds.py` - KRDS file inspection
    - `diagnose_imports.py` - Import debugging
    - `test_pdt_files.py` - PDT file content verification
    - `find_content_in_pdf.py` - Text search debugging
    - `dump_pdf_tokens.py` - Text extraction and ligature debugging
  - Created `scripts/README.md` - Documentation for diagnostic tools
  - Removed obsolete scripts:
    - 20+ analysis scripts (analyze_*.py)
    - 12 test scripts (test_*.py from research phase)
    - 6 debug scripts specific to old hypotheses
    - Learning/calibration scripts (learn_*.py, calibrate_*.py)
    - Visualization scripts (visualize_*.py)
    - Shell scripts (*.sh)

### Files to Remove (Outdated Research Notes)
These files contain research notes that have been superseded by the validated solution:
- `CI_CD_TEST_STATUS.md` - outdated
- `COORDINATE_RESEARCH_JOURNEY.md` - superseded by findings
- `CROPBOX_FIX_DISCOVERY.md` - obsolete (CropBox handling now understood)
- `H1_TEST_RESULTS.md` - old results, superseded
- `HYBRID_SEARCH_IMPLEMENTATION_COMPLETE.md` - not relevant
- `OLD_FORMAT_COORDINATE_ANALYSIS.md` - obsolete
- `SNAKE_PATTERN_IMPLEMENTATION.md` - already implemented
- `Y_AXIS_FIX_DISCOVERED.md` - integrated into solution

### Outdated code:
- `pdt_parser.py` - there is never any content in pdt files (please double check)
- all testing scripts in the main folder should be converted to unit tests if still relevant, and discarded otherwise

### Files to Keep
- `README.md` - main documentation
- `LICENSE` - project license
- `TODO.md` - this file
- `requirements.txt` - dependencies
- `setup.py` - package setup
- `VALIDATION_SUMMARY.md` - validation results
- ✅ `COORDINATE_SYSTEM.md` - NEW technical documentation

### Documentation Updates
1. ✅ **COORDINATE_SYSTEM.md**: Created - Documents inches-based formula and CropBox handling
2. ✅ **README.md**: Updated with coordinate system section
3. ✅ **Archive old research**: Moved outdated MD files to `docs/archive/` folder

## Next Steps

### Testing (Priority 1)
1. ✅ Test on all cropped PDFs in dataset (especially Shea PDF with 40.1 pt offset) using UNIT TESTS
2. ✅ Verify highlights appear at correct positions using UNIT TESTS
3. ⏳ Run full test suite on all 83 annotated PDFs (only for internal purposes, the annotated PDFs are not part of the official repo)
4. ⏳ Compare output with production system (blue highlights)

### Notes Without Content (Priority 2)
1. ✅ Implemented overlap detection between notes and highlights (unification with 0.15pt tolerance)
2. ⏳ Make sure notes have text as specified in KRDS data (and consistent with what clipping file say)
3. ⏳ Test with real notes from KRDS data

### Cleanup (Priority 3)
1. ✅ Archive outdated research markdown files
2. ✅ Update README.md with new coordinate system info
3. ✅ Remove obsolete test/analysis scripts if not needed
4. ✅ Rename "H1" to "inches-based formula" (done - removed cryptic hypothesis numbering)

## Validation Results Summary

### Dataset Quality
- **346 real highlights** extracted from production-annotated PDFs
- **78.6% multi-line** (272 highlights with snake patterns)
- **Single-highlight-per-page** strict matching (unambiguous ground truth)

### H1 Formula Performance (Validated Winner)
```
Combined median error: 10.94 pts (0.15 inches)
X-axis median: 19.73 pts (0.27 inches)
Y-axis median: 2.12 pts (0.03 inches)
```

### Hypothesis Comparison
1. **H1 (inches both)**: 10.94 pts ⭐ WINNER
2. H5 (piecewise): 124.94 pts
3. H8 (hybrid piecewise): 124.94 pts
4. H6 (hybrid): 136.31 pts
5. **H7 (expert report)**: 286.61 pts ❌ 26.2x WORSE

### Key Findings
- ✅ H1 simple inches formula is best
- ✅ Y-axis extremely accurate (2 pts median)
- ✅ X-axis acceptable (20 pts median on real multi-line data)
- ❌ Expert report hypothesis completely wrong
- ⚠️ CropBox offset MUST be handled (not optional)

## Next Session Goals
1. Fix CropBox handling in production code
2. Test on all cropped PDFs in dataset
3. Verify notes-without-content handling
4. Clean up repository documentation
5. Create final validation report
