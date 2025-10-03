"""
Calibration engine for computing robust linear transformation from Amazon Kindle coordinates to PDF coordinates.
Uses multiple datasets to derive stable, general transformation parameters.
"""

import fitz
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re


def normalize_text_for_search(text: str) -> str:
    """Normalize text for search by handling common issues."""
    if not text:
        return ""
    # Remove extra whitespace
    normalized = ' '.join(text.split())
    # Handle common OCR/encoding issues
    normalized = normalized.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return normalized


def find_text_on_page_robust(page, target_text: str, max_attempts: int = 5) -> Optional[fitz.Rect]:
    """
    Robustly find text on a PDF page using multiple strategies.
    Returns the bounding rectangle if found, None otherwise.
    """
    if not target_text or not target_text.strip():
        return None
    
    # Strategy 1: Direct search with full text
    normalized_target = normalize_text_for_search(target_text)
    rects = page.search_for(normalized_target)
    if rects:
        return rects[0]
    
    # Strategy 2: Try first 100 characters
    if len(normalized_target) > 100:
        shortened = normalized_target[:100]
        rects = page.search_for(shortened)
        if rects:
            return rects[0]
    
    # Strategy 3: Try first 50 characters
    if len(normalized_target) > 50:
        shortened = normalized_target[:50]
        rects = page.search_for(shortened)
        if rects:
            return rects[0]
    
    # Strategy 4: Try words-based search (first 10 words)
    words = normalized_target.split()
    if len(words) > 10:
        shortened = ' '.join(words[:10])
        rects = page.search_for(shortened)
        if rects:
            return rects[0]
    
    # Strategy 5: Try first 5 words
    if len(words) > 5:
        shortened = ' '.join(words[:5])
        rects = page.search_for(shortened)
        if rects:
            return rects[0]
    
    # Strategy 6: Character-by-character matching using text blocks
    # This is more expensive but more robust for complex layouts
    try:
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])
        
        # Flatten all text from blocks
        page_text = []
        block_rects = []
        
        for block in blocks:
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text.strip():
                            bbox = span.get("bbox", [])
                            if len(bbox) == 4:
                                page_text.append(normalize_text_for_search(span_text))
                                block_rects.append(fitz.Rect(bbox))
        
        # Try to find a sequence that matches the beginning of target
        target_words = normalized_target.split()[:5]  # First 5 words
        target_str = ' '.join(target_words)
        
        page_full_text = ' '.join(page_text)
        if target_str.lower() in page_full_text.lower():
            # Find the span index where this starts
            cumulative = ""
            for i, text in enumerate(page_text):
                cumulative += " " + text
                if target_str.lower() in cumulative.lower():
                    # Return union of relevant rectangles
                    start_idx = max(0, i - 2)
                    end_idx = min(len(block_rects), i + 5)
                    if start_idx < len(block_rects):
                        union_rect = block_rects[start_idx]
                        for j in range(start_idx + 1, end_idx):
                            if j < len(block_rects):
                                union_rect = union_rect | block_rects[j]
                        return union_rect
    except Exception as e:
        pass
    
    return None


def collect_calibration_points_from_dataset(
    krds_file: str,
    clippings_file: str,
    pdf_file: str,
    book_name: str
) -> List[Dict[str, Any]]:
    """
    Collect calibration points from a single dataset by matching:
    - KRDS coordinates (Amazon Kindle coordinate system)
    - Clippings text (ground truth content)
    - PDF text locations (actual PDF coordinates)
    
    Returns list of calibration points with both Kindle and PDF coordinates.
    """
    from .krds_parser import KindleReaderDataStore
    from .fixed_clippings_parser import parse_myclippings_for_book
    
    print(f"\n📊 Collecting calibration data from: {book_name}")
    
    # Load KRDS annotations
    krds = KindleReaderDataStore(krds_file)
    krds_annotations = krds.extract_annotations()
    krds_highlights = [ann for ann in krds_annotations if 'highlight' in ann.annotation_type]
    
    # Load clippings
    clippings = parse_myclippings_for_book(clippings_file, book_name)
    clippings_highlights = [c for c in clippings if c['type'] == 'highlight' and c['content'].strip()]
    
    print(f"   KRDS highlights: {len(krds_highlights)}")
    print(f"   Clippings highlights: {len(clippings_highlights)}")
    
    # Open PDF
    doc = fitz.open(pdf_file)
    pdf_dimensions = {
        'width': doc[0].rect.width,
        'height': doc[0].rect.height
    }
    print(f"   PDF dimensions: {pdf_dimensions['width']:.1f} x {pdf_dimensions['height']:.1f}")
    
    calibration_points = []
    
    # Match clippings to KRDS and PDF locations
    for clip in clippings_highlights:
        content = clip['content'].strip()
        page_1based = clip['pdf_page']
        page_0based = page_1based - 1
        
        if page_0based >= len(doc) or page_0based < 0:
            continue
        
        page = doc[page_0based]
        
        # Find text in PDF
        pdf_rect = find_text_on_page_robust(page, content)
        
        if not pdf_rect:
            continue
        
        # Find matching KRDS annotation on the same page
        krds_match = None
        min_distance = float('inf')
        
        for krds_ann in krds_highlights:
            if krds_ann.start_position.page == page_0based:
                # Use position as a rough match - prefer annotations we haven't used
                if krds_ann not in [p['krds_ann'] for p in calibration_points]:
                    # Calculate distance metric (just to prefer closer ones)
                    distance = abs(krds_ann.start_position.y - 400)  # Rough middle of page
                    if distance < min_distance:
                        min_distance = distance
                        krds_match = krds_ann
        
        if krds_match:
            point = {
                'book': book_name,
                'page': page_0based,
                'kindle_x': krds_match.start_position.x,
                'kindle_y': krds_match.start_position.y,
                'kindle_w': krds_match.start_position.width,
                'kindle_h': krds_match.start_position.height,
                'pdf_x': pdf_rect.x0,
                'pdf_y': pdf_rect.y0,
                'pdf_w': pdf_rect.width,
                'pdf_h': pdf_rect.height,
                'pdf_page_width': pdf_dimensions['width'],
                'pdf_page_height': pdf_dimensions['height'],
                'content': content[:50],
                'krds_ann': krds_match  # Keep reference to avoid reuse
            }
            calibration_points.append(point)
            print(f"   ✓ Matched: Kindle({point['kindle_x']}, {point['kindle_y']}) -> PDF({point['pdf_x']:.1f}, {point['pdf_y']:.1f})")
    
    doc.close()
    
    print(f"   📍 Collected {len(calibration_points)} calibration points")
    return calibration_points


def compute_linear_transformation(calibration_points: List[Dict[str, Any]]) -> Tuple[float, float, float, float, float, float]:
    """
    Compute linear transformation parameters from calibration points using least squares.
    
    Transformations:
        pdf_x = x_scale * kindle_x + x_offset
        pdf_y = y_scale * kindle_y + y_offset
        pdf_width = width_scale * kindle_width
        pdf_height = height_scale * kindle_height
    
    Returns:
        Tuple of (x_scale, x_offset, y_scale, y_offset, width_scale, height_scale)
    """
    if len(calibration_points) < 2:
        raise ValueError(f"Need at least 2 calibration points, got {len(calibration_points)}")
    
    print(f"\n🔧 Computing linear transformation from {len(calibration_points)} points...")
    
    # Extract coordinate arrays
    kindle_xs = [p['kindle_x'] for p in calibration_points]
    kindle_ys = [p['kindle_y'] for p in calibration_points]
    kindle_ws = [p['kindle_w'] for p in calibration_points if p['kindle_w'] > 0]
    kindle_hs = [p['kindle_h'] for p in calibration_points if p['kindle_h'] > 0]
    
    pdf_xs = [p['pdf_x'] for p in calibration_points]
    pdf_ys = [p['pdf_y'] for p in calibration_points]
    pdf_ws = [p['pdf_w'] for p in calibration_points if p['kindle_w'] > 0]
    pdf_hs = [p['pdf_h'] for p in calibration_points if p['kindle_h'] > 0]
    
    n = len(kindle_xs)
    
    # Linear regression for X: pdf_x = x_scale * kindle_x + x_offset
    sum_kx = sum(kindle_xs)
    sum_px = sum(pdf_xs)
    sum_kx_px = sum(kx * px for kx, px in zip(kindle_xs, pdf_xs))
    sum_kx2 = sum(kx ** 2 for kx in kindle_xs)
    
    denominator = n * sum_kx2 - sum_kx ** 2
    if abs(denominator) < 1e-10:
        raise ValueError("Cannot compute X transformation: insufficient variation in X coordinates")
    
    x_scale = (n * sum_kx_px - sum_kx * sum_px) / denominator
    x_offset = (sum_px - x_scale * sum_kx) / n
    
    # Linear regression for Y: pdf_y = y_scale * kindle_y + y_offset
    sum_ky = sum(kindle_ys)
    sum_py = sum(pdf_ys)
    sum_ky_py = sum(ky * py for ky, py in zip(kindle_ys, pdf_ys))
    sum_ky2 = sum(ky ** 2 for ky in kindle_ys)
    
    denominator = n * sum_ky2 - sum_ky ** 2
    if abs(denominator) < 1e-10:
        raise ValueError("Cannot compute Y transformation: insufficient variation in Y coordinates")
    
    y_scale = (n * sum_ky_py - sum_ky * sum_py) / denominator
    y_offset = (sum_py - y_scale * sum_ky) / n
    
    # Compute width and height scaling (simple ratio average)
    if kindle_ws and pdf_ws:
        width_scale = sum(pw / kw for kw, pw in zip(kindle_ws, pdf_ws)) / len(kindle_ws)
    else:
        width_scale = 1.0
    
    if kindle_hs and pdf_hs:
        height_scale = sum(ph / kh for kh, ph in zip(kindle_hs, pdf_hs)) / len(kindle_hs)
    else:
        height_scale = 1.0
    
    print(f"   X transformation: pdf_x = {x_scale:.6f} * kindle_x + {x_offset:.3f}")
    print(f"   Y transformation: pdf_y = {y_scale:.6f} * kindle_y + {y_offset:.3f}")
    print(f"   Width scale: {width_scale:.6f}")
    print(f"   Height scale: {height_scale:.6f}")
    
    # Validate transformation accuracy
    print(f"\n✅ Validation:")
    errors_x = []
    errors_y = []
    
    for p in calibration_points[:5]:  # Show first 5
        pred_x = x_scale * p['kindle_x'] + x_offset
        pred_y = y_scale * p['kindle_y'] + y_offset
        error_x = abs(pred_x - p['pdf_x'])
        error_y = abs(pred_y - p['pdf_y'])
        errors_x.append(error_x)
        errors_y.append(error_y)
        print(f"   Point: error_x={error_x:.1f}pt, error_y={error_y:.1f}pt")
    
    # Calculate overall error statistics
    all_errors_x = [abs((x_scale * p['kindle_x'] + x_offset) - p['pdf_x']) for p in calibration_points]
    all_errors_y = [abs((y_scale * p['kindle_y'] + y_offset) - p['pdf_y']) for p in calibration_points]
    
    avg_error_x = sum(all_errors_x) / len(all_errors_x)
    avg_error_y = sum(all_errors_y) / len(all_errors_y)
    max_error_x = max(all_errors_x)
    max_error_y = max(all_errors_y)
    
    print(f"\n   Average error: X={avg_error_x:.2f}pt, Y={avg_error_y:.2f}pt")
    print(f"   Max error: X={max_error_x:.2f}pt, Y={max_error_y:.2f}pt")
    
    return x_scale, x_offset, y_scale, y_offset, width_scale, height_scale


def calibrate_from_datasets(datasets: List[Dict[str, str]]) -> Dict[str, float]:
    """
    Calibrate transformation parameters from multiple datasets.
    
    Args:
        datasets: List of dataset configurations with keys: 'name', 'krds', 'clippings', 'pdf'
    
    Returns:
        Dictionary with calibration parameters
    """
    print("=" * 80)
    print("🎯 MULTI-DATASET CALIBRATION")
    print("=" * 80)
    
    all_calibration_points = []
    
    # Collect points from all datasets
    for dataset in datasets:
        try:
            points = collect_calibration_points_from_dataset(
                dataset['krds'],
                dataset['clippings'],
                dataset['pdf'],
                dataset['name']
            )
            all_calibration_points.extend(points)
        except Exception as e:
            print(f"   ⚠️  Warning: Failed to process {dataset['name']}: {e}")
    
    if len(all_calibration_points) < 3:
        raise ValueError(f"Insufficient calibration data: only {len(all_calibration_points)} points collected")
    
    print(f"\n📊 Total calibration points: {len(all_calibration_points)}")
    
    # Compute transformation
    x_scale, x_offset, y_scale, y_offset, width_scale, height_scale = compute_linear_transformation(
        all_calibration_points
    )
    
    return {
        'x_scale': x_scale,
        'x_offset': x_offset,
        'y_scale': y_scale,
        'y_offset': y_offset,
        'width_scale': width_scale,
        'height_scale': height_scale,
        'num_points': len(all_calibration_points)
    }
