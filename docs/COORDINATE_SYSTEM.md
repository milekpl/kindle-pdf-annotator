# Kindle KRDS to PDF Coordinate System

**Status**: ✅ **VALIDATED** (October 2025)  
**Formula**: H1 - Inches-based conversion  
**Validation**: 346 real production highlights with multi-line patterns

---

## The Validated Formula

The coordinate conversion from Kindle KRDS units to PDF points follows this simple, elegant formula:

```python
# H1 Formula (Validated)
def krds_to_pdf(krds_x, krds_y, cropbox_x0=0, cropbox_y0=0):
    """
    Convert KRDS coordinates to PDF points.
    
    KRDS Range: 0-10000 (100 units = 1 inch)
    PDF Points: 72 points = 1 inch
    """
    # Convert from KRDS units to PDF points
    pdf_x = (krds_x / 100.0) * 72.0
    pdf_y = (krds_y / 100.0) * 72.0
    
    # Apply CropBox offset (CRITICAL for cropped PDFs)
    pdf_x -= cropbox_x0
    pdf_y -= cropbox_y0
    
    return pdf_x, pdf_y
```

### Key Properties

1. **Same formula for both X and Y axes** - Simple and consistent
2. **KRDS coordinates are in hundredths of an inch** (100 units = 1 inch)
3. **PDF points are 1/72 of an inch** (72 points = 1 inch)
4. **Conversion factor**: divide by 100, multiply by 72 = multiply by 0.72

### Performance Metrics

Validated on **346 real production highlights** (78.6% multi-line):

- **Combined median error**: 10.94 pts (0.15 inches)
- **X-axis median error**: 19.73 pts (0.27 inches)
- **Y-axis median error**: 2.12 pts (0.03 inches)

The Y-axis is extremely accurate (2 pts ≈ 1mm). The X-axis error is acceptable for multi-line highlights with text wrapping.

---

## Critical: CropBox Offset

### The Problem

**KRDS coordinates are absolute to the original uncropped page.**

When a PDF is cropped (e.g., margins removed), the visible page has different coordinates than the original. If you don't account for this, all highlights will appear shifted or outside the visible bounds.

### Example

```
Original PDF: 612 x 792 pts
Cropped PDF: CropBox = [40.1, 0, 612, 792]
             (40.1 pts removed from left margin)

KRDS coordinate: X=4330 → PDF X=311.8 pts
Without CropBox fix: X=311.8 (outside visible bounds!)
With CropBox fix: X=311.8 - 40.1 = 271.7 (correct position)
```

### Implementation

```python
# Get the page's CropBox
page = pdf_doc[page_number]
cropbox = page.cropbox

# Convert with CropBox correction
pdf_x = (krds_x / 100.0) * 72.0 - cropbox.x0
pdf_y = (krds_y / 100.0) * 72.0 - cropbox.y0
```

### Detection

Check if a PDF has CropBox offsets:

```python
import fitz

doc = fitz.open("document.pdf")
page = doc[0]

if page.cropbox.x0 != 0 or page.cropbox.y0 != 0:
    print(f"CropBox offset: ({page.cropbox.x0}, {page.cropbox.y0})")
```

---

## Width and Height Conversion

Width and height use the **same formula** as X and Y coordinates:

```python
def convert_width_height(krds_width, krds_height):
    """Convert KRDS width/height to PDF points."""
    pdf_width = (krds_width / 100.0) * 72.0
    pdf_height = (krds_height / 100.0) * 72.0
    return pdf_width, pdf_height
```

---

## Multi-line Highlights (Snake Pattern)

**78.6%** of real highlights span multiple lines and wrap around.

### Coordinate Behavior

For multi-line highlights:
- `start_x` > `end_x` (wraps to next line)
- `start_y` < `end_y` (goes downward)

```
Line 1: [start_x, start_y] ─────────────────┐
                                             │
Line 2: ┌──────────────────────────────────┤
        │                                   │
Line 3: ├───────────────────────────────┐  │
        │                                │  │
Line 4: └────── [end_x, end_y]          │  │
                                         └──┘
```

### Rendering

**DO NOT** create a single rectangle from start to end:
```python
# ❌ WRONG - fails for multi-line
rect = fitz.Rect(start_x, start_y, end_x, end_y)
```

**DO** use the actual quad coordinates:
```python
# ✅ CORRECT - uses actual text quads
quads = page.search_for(text, quads=True)
for quad in quads:
    highlight.add_quad(quad)
```

---

## Validation History

### Previous Hypotheses (Rejected)

| Hypothesis | Error | Status |
|------------|-------|--------|
| H2: Direct scaling | 124+ pts | ❌ Rejected |
| H3: Percentage | 124+ pts | ❌ Rejected |
| H5: Piecewise | 124.94 pts | ❌ Rejected |
| H6: Hybrid | 136.31 pts | ❌ Rejected |
| **H7: Expert report** | **286.61 pts** | ❌ **26.2x WORSE** |

### Why H7 (Expert Report) Failed

The expert report claimed:
- Y-axis uses inverted screen coordinates (Y=0 at top)
- Requires complex translation matrix

**Empirical testing proved this completely wrong:**
- Y-axis error: 326 pts (vs 2 pts for H1)
- Combined error: 26.2x worse than H1
- The Y-axis is NOT inverted - it follows standard PDF coordinates

---

## Implementation Checklist

When implementing KRDS coordinate conversion:

- [x] Use H1 formula: `(krds / 100) × 72`
- [x] Same formula for X, Y, width, height
- [x] Get page-specific CropBox for each annotation
- [x] Subtract CropBox offset from converted coordinates
- [x] Check bounds to prevent out-of-page coordinates
- [x] Use quads (not rectangles) for multi-line highlights
- [ ] Handle notes without content (check overlap with highlights)

---

## Testing on Cropped PDFs

To verify CropBox handling:

1. Find a PDF with CropBox offset > 10 pts
2. Convert KRDS annotations
3. Verify highlights appear at correct positions (not shifted)
4. Compare with production system output (blue highlights)

Example test files:
- `Shea - 2024 - Concepts at the interface_cropped.pdf` (40.1 pt offset)

---

## References

- **Validation Summary**: `VALIDATION_SUMMARY.md`
- **Implementation**: `src/kindle_parser/amazon_coordinate_system.py`
- **Production Data**: 83 annotated PDFs, 346 validated highlights
- **Date Validated**: October 6-7, 2025

---

## Notes on Coordinate Systems

### KRDS Coordinate System
- Range: 0-10000 on both axes
- Origin: Top-left (0, 0)
- Units: 100 = 1 inch
- Direction: X increases right, Y increases downward
- **Absolute to original uncropped page**

### PDF Coordinate System
- Units: Points (72 = 1 inch)
- Origin: Bottom-left (0, 0) for MediaBox
- Direction: X increases right, Y increases upward
- CropBox: Defines visible region within MediaBox
- **Coordinates relative to CropBox origin**

### The Conversion
Since both systems measure in fractions of inches (KRDS: 1/100", PDF: 1/72"), the conversion is straightforward:

```
pdf_points = (krds_units / 100 inches) × (72 points/inch)
           = krds_units × 0.72
```

The Y-axis direction matches (both increase downward in the PDF rendering context for highlights), so no inversion is needed.
