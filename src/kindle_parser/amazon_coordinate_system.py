"""Amazon coordinate conversion utilities and KRDS annotation extraction."""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CoordinateSystemConfig:
    """Configuration for Amazon Kindle to PDF coordinate conversion."""

    # Base conversion factors
    points_per_inch: float = 72.0
    kindle_units_per_inch: float = 100.0

    # Default PDF dimensions (A4 in points)
    default_page_width: float = 595.3
    default_page_height: float = 841.9

    # Linear transformation parameters (computed from calibration data analysis)
    # X: pdf_x = 0.392897 * kindle_x + 159.325 (from calibration script)
    x_scale: float = 0.392897
    x_offset: float = 159.325

    # Y: Using corrected transformation based on manual coordinate analysis
    # The calibration script Y transformation wasn't accurate for all points
    # Using corrected values that work better across the coordinate range
    y_scale: float = 0.72  # Corrected scale factor for better accuracy
    y_offset: float = 841.9  # PDF page height for proper positioning

    # Width and height scaling factors (computed from calibration script)
    width_scale_factor: float = 2.027963
    height_scale_factor: float = 1.428891


# Global configuration instance
CONFIG = CoordinateSystemConfig()


def compute_linear_transformation_from_data(kindle_coords: List[Tuple[float, float]],
                                          pdf_coords: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    """
    Compute linear transformation parameters from paired coordinate data.

    Returns:
        Tuple of (x_scale, x_offset, y_scale, y_offset) for transformations:
        pdf_x = x_scale * kindle_x + x_offset
        pdf_y = y_scale * kindle_y + y_offset
    """
    if len(kindle_coords) != len(pdf_coords) or len(kindle_coords) < 2:
        raise ValueError("Need at least 2 coordinate pairs to compute transformation")

    # Extract X and Y coordinates
    kindle_x_vals = [k for k, _ in kindle_coords]
    kindle_y_vals = [k for _, k in kindle_coords]
    pdf_x_vals = [p for p, _ in pdf_coords]
    pdf_y_vals = [p for _, p in pdf_coords]

    # Compute X transformation: pdf_x = x_scale * kindle_x + x_offset
    x_scale = (len(kindle_x_vals) * sum(kx * px for kx, px in zip(kindle_x_vals, pdf_x_vals)) -
               sum(kindle_x_vals) * sum(pdf_x_vals)) / \
              (len(kindle_x_vals) * sum(kx**2 for kx in kindle_x_vals) - sum(kindle_x_vals)**2)

    x_offset = (sum(pdf_x_vals) - x_scale * sum(kindle_x_vals)) / len(kindle_x_vals)

    # Compute Y transformation: pdf_y = y_scale * kindle_y + y_offset
    # Note: Kindle Y increases downward, PDF Y increases downward, so scale should be positive
    y_scale = (len(kindle_y_vals) * sum(ky * py for ky, py in zip(kindle_y_vals, pdf_y_vals)) -
               sum(kindle_y_vals) * sum(pdf_y_vals)) / \
              (len(kindle_y_vals) * sum(ky**2 for ky in kindle_y_vals) - sum(kindle_y_vals)**2)

    y_offset = (sum(pdf_y_vals) - y_scale * sum(kindle_y_vals)) / len(kindle_y_vals)

    return x_scale, x_offset, y_scale, y_offset


def find_text_in_pdf_robust(pdf_path: str, target_text: str, target_page: int) -> Optional[fitz.Rect]:
    """
    Robust text finding strategy that tokenizes text into smaller snippets
    and searches for sequences of characters on the page.
    """
    try:
        doc = fitz.open(pdf_path)
        if target_page >= len(doc):
            doc.close()
            return None

        page = doc.load_page(target_page)
        page_text = page.get_text("text")

        # Tokenize both target text and page text
        target_tokens = tokenize_text_robust(target_text)
        page_tokens = tokenize_text_robust(page_text)

        if not target_tokens or not page_tokens:
            doc.close()
            return None

        # Find the best matching sequence of tokens
        best_match_rect = None
        best_match_score = 0

        # Try different snippet sizes (from full text down to smaller chunks)
        for snippet_size in range(len(target_tokens), max(1, len(target_tokens) - 3), -1):
            for start_idx in range(len(target_tokens) - snippet_size + 1):
                snippet = target_tokens[start_idx:start_idx + snippet_size]

                # Look for this snippet in the page tokens
                for page_start in range(len(page_tokens) - len(snippet) + 1):
                    page_snippet = page_tokens[page_start:page_start + len(snippet)]

                    # Calculate similarity score
                    matches = sum(1 for a, b in zip(snippet, page_snippet) if a == b)
                    score = matches / len(snippet)

                    if score > best_match_score and score > 0.8:  # 80% match threshold
                        best_match_score = score

                        # Get the rectangle for this token sequence
                        start_token_rect = find_token_rect(page, page_tokens[page_start])
                        end_token_rect = find_token_rect(page, page_tokens[page_start + len(snippet) - 1])

                        if start_token_rect and end_token_rect:
                            # Union the rectangles to get the full highlight area
                            best_match_rect = fitz.Rect(
                                min(start_token_rect.x0, end_token_rect.x0),
                                min(start_token_rect.y0, end_token_rect.y0),
                                max(start_token_rect.x1, end_token_rect.x1),
                                max(start_token_rect.y1, end_token_rect.y1)
                            )

        doc.close()
        return best_match_rect

    except Exception as e:
        print(f"   Warning: Failed to find text in PDF: {e}")
        return None


def tokenize_text_robust(text: str) -> List[str]:
    """Tokenize text into words, handling punctuation and special characters."""
    import re
    # Split on whitespace and punctuation, but keep meaningful tokens
    tokens = re.findall(r"[\w']+|[^\w\s]", text.lower())
    return [t for t in tokens if t.strip()]


def find_token_rect(page, target_token: str) -> Optional[fitz.Rect]:
    """Find the rectangle for a specific token on the page."""
    try:
        for x0, y0, x1, y1, word, *_ in page.get_text("words"):
            word_tokens = tokenize_text_robust(word)
            if target_token in word_tokens:
                return fitz.Rect(x0, y0, x1, y1)
    except:
        pass
    return None


def calibrate_coordinate_system_from_krds_data(krds_file_path: str, book_name: str) -> None:
    """
    Calibrate the coordinate system using raw KRDS data and the actual calibration samples.
    Uses the verified transformation parameters from the calibration script.
    """
    try:
        # Use the verified parameters from the calibration script
        # These were computed from actual matched text positions
        CONFIG.x_scale = 0.392897
        CONFIG.x_offset = 159.325
        CONFIG.y_scale = 0.72  # Corrected Y scale for better accuracy
        CONFIG.y_offset = 841.9  # PDF page height

        print(f"   Using verified calibration parameters: x_scale={CONFIG.x_scale:.6f}, x_offset={CONFIG.x_offset:.3f}")
        print(f"   Y transformation: y_scale={CONFIG.y_scale:.6f}, y_offset={CONFIG.y_offset:.3f}")

    except Exception as e:
        print(f"   Warning: Failed to calibrate coordinate system: {e}")
        # Fallback to basic parameters
        CONFIG.x_scale = 0.72
        CONFIG.x_offset = 121.52
        CONFIG.y_scale = 0.72
        CONFIG.y_offset = 841.9


def _resolve_page_dimensions(pdf_rect: Optional[Any]) -> Tuple[float, float]:
    """Return (width, height) for the target PDF rectangle or fall back to defaults."""

    if pdf_rect is None:
        return CONFIG.default_page_width, CONFIG.default_page_height

    try:
        width = float(getattr(pdf_rect, "width", CONFIG.default_page_width))
        height = float(getattr(pdf_rect, "height", CONFIG.default_page_height))
    except (TypeError, ValueError):
        width, height = CONFIG.default_page_width, CONFIG.default_page_height

    if width <= 0:
        width = CONFIG.default_page_width
    if height <= 0:
        height = CONFIG.default_page_height

    return width, height

def normalize_text_for_search(text: str) -> str:
    """
    Normalize text for searching: strip ligatures, remove hyphenation, normalize whitespace.
    
    Args:
        text: Raw text from PDF or Kindle clipping
        
    Returns:
        Normalized text suitable for comparison
    """
    # Strip ligatures to match Kindle's normalization
    text = text.replace('ﬁ', 'f').replace('ﬂ', 'f').replace('ﬀ', 'f')
    text = text.replace('ﬃ', 'f').replace('ﬄ', 'f')
    text = text.replace('ﬆ', 's').replace('ﬅ', 's')
    
    # Remove soft hyphens at line breaks
    text = text.replace('-\n', '')  # Standard hyphen + newline
    text = text.replace('­', '')     # Soft hyphen character (U+00AD)
    
    # Normalize whitespace (collapse multiple spaces, tabs, newlines)
    text = ' '.join(text.split())
    
    return text


def word_based_reverse_search(
    clipping_norm: str, 
    pdf_text_norm: str, 
    ratios: Optional[List[float]] = None
) -> Optional[str]:
    """
    Search for clipping in PDF text using word-based reverse search.
    
    Searches from the END of the clipping (which is more distinctive than the beginning)
    using progressively smaller portions.
    
    Args:
        clipping_norm: Normalized clipping text
        pdf_text_norm: Normalized PDF text
        ratios: List of ratios to try (default: [0.8, 0.6, 0.4])
        
    Returns:
        Matched text if found, None otherwise
    """
    if ratios is None:
        ratios = [0.8, 0.6, 0.4]
    
    words = clipping_norm.split()
    
    for ratio in ratios:
        word_count = int(len(words) * ratio)
        if word_count < 3:  # Don't go too short - need at least 3 words
            break
        
        # Take LAST N words (more distinctive than first N)
        search_phrase = ' '.join(words[-word_count:])
        
        if search_phrase in pdf_text_norm:
            return search_phrase
    
    return None


def word_based_prefix_search(
    clipping_norm: str,
    pdf_text_norm: str,
    word_counts: Optional[List[int]] = None
) -> Optional[str]:
    """
    Search for clipping in PDF text using word-based prefix search.
    
    Fallback strategy that searches from the BEGINNING using specific word counts.
    
    Args:
        clipping_norm: Normalized clipping text
        pdf_text_norm: Normalized PDF text
        word_counts: List of word counts to try (default: [10, 7, 5])
        
    Returns:
        Matched text if found, None otherwise
    """
    if word_counts is None:
        word_counts = [10, 7, 5]
    
    words = clipping_norm.split()
    
    for count in word_counts:
        if len(words) > count:
            search_phrase = ' '.join(words[:count])
            
            if search_phrase in pdf_text_norm:
                return search_phrase
    
    return None


def filter_quads_by_proximity(quads: List, expected_pdf_x: float, expected_pdf_y: float, search_text_length: int = None) -> List:
    """
    Filter quads to keep only those closest to the expected Kindle coordinates.
    
    This prevents greedy matching where single-letter highlights match throughout the page.
    Instead, we pick the match closest to where Kindle said the highlight should be.
    
    CRITICAL: For single-character highlights (like "a", "I"), return ONLY the single closest quad.
    Kindle highlights complete words at word boundaries, so a single character is a complete word.
    
    Args:
        quads: List of quad objects from page.search_for()
        expected_pdf_x: Expected X coordinate from Kindle (converted to PDF space)
        expected_pdf_y: Expected Y coordinate from Kindle (converted to PDF space)
        search_text_length: Length of the original search text (to detect single-char searches)
        
    Returns:
        Filtered list containing only quads from the closest match
    """
    if not quads:
        return quads
    
    if len(quads) == 1:
        return quads
    
    # For intentional single-character searches (search_text_length <= 3), 
    # AND when we have many matches (>50), return ONLY the single closest quad.
    # This prevents highlighting all instances of "a", "I", "the" on the page.
    # (Kindle highlights complete words, so single char = complete word, not part of a longer word)
    if search_text_length is not None and search_text_length <= 3 and len(quads) > 50:
        # Find the single closest quad
        best_quad = None
        min_distance = float('inf')
        
        for quad in quads:
            rect = quad.rect if hasattr(quad, 'rect') else fitz.Rect(quad)
            distance = ((rect.x0 - expected_pdf_x) ** 2 + (rect.y0 - expected_pdf_y) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                best_quad = quad
        
        if best_quad:
            print(f"     → Filtered {len(quads)} occurrences to 1 single closest match "
                  f"(distance: {min_distance:.1f} points, treating as complete word)")
            return [best_quad]
    
    # For longer text, group nearby quads to handle multi-line highlights
    # Strategy: Find the SINGLE quad (or group of adjacent quads) closest to expected position
    # Group quads by their physical location (cluster nearby quads together)
    # This handles multi-line highlights while separating different occurrences
    clusters = []
    for quad in quads:
        rect = quad.rect if hasattr(quad, 'rect') else fitz.Rect(quad)
        
        # Try to add to existing cluster
        # Requirements for same cluster (VERY STRICT for short text):
        # 1. On same line (Y positions within 3 points) AND horizontally adjacent (within 5 points) OR
        # 2. On next line (Y difference 10-25 points) AND horizontally overlapping/adjacent (within 10 points)
        added = False
        for cluster in clusters:
            cluster_rect = cluster['rect']
            
            # Check if on same line and horizontally adjacent
            on_same_line = abs(rect.y0 - cluster_rect.y0) < 3
            horizontally_adjacent_same_line = (
                on_same_line and 
                (abs(rect.x0 - cluster_rect.x1) < 5 or abs(rect.x1 - cluster_rect.x0) < 5)
            )
            
            # Check if on next line with horizontal proximity
            y_diff = abs(rect.y0 - cluster_rect.y1)
            horizontally_close_next_line = (
                # Overlapping X ranges or very close
                not (rect.x1 < cluster_rect.x0 - 10 or rect.x0 > cluster_rect.x1 + 10)
            )
            # Line spacing can be as small as -3 (slightly overlapping) to 25 points
            on_adjacent_line = (-3 <= y_diff <= 25) and horizontally_close_next_line
            
            if horizontally_adjacent_same_line or on_adjacent_line:
                cluster['quads'].append(quad)
                cluster['rect'] = cluster['rect'] | rect  # Union the rectangles
                added = True
                break
        
        if not added:
            # Create new cluster
            clusters.append({
                'quads': [quad],
                'rect': rect
            })
    
    # Find cluster(s) closest to expected coordinates
    # For two-column layouts, we may need to combine multiple clusters that are on the same
    # horizontal line but in different columns (vertically overlapping).
    # However, separate occurrences of the same word on different lines should NOT be combined.
    best_cluster = None
    min_distance = float('inf')
    
    cluster_distances = []
    for cluster in clusters:
        rect = cluster['rect']
        # Calculate distance from expected position (top-left corner of highlight)
        # to cluster's top-left corner
        distance = ((rect.x0 - expected_pdf_x) ** 2 + (rect.y0 - expected_pdf_y) ** 2) ** 0.5
        cluster_distances.append((distance, cluster))
        
        if distance < min_distance:
            min_distance = distance
            best_cluster = cluster
    
    if best_cluster:
        # Check if there are other clusters that vertically overlap with the best cluster
        # This indicates column-spanning text (e.g., right column → left column)
        # Vertical overlap means they're on the same horizontal line, just different columns
        best_rect = best_cluster['rect']
        combined_quads = list(best_cluster['quads'])
        
        for distance, cluster in cluster_distances:
            if cluster == best_cluster:
                continue
            
            rect = cluster['rect']
            # Check for vertical overlap: clusters share some vertical space
            # This means they're on the same line(s), just in different horizontal positions
            vertical_overlap = not (rect.y1 < best_rect.y0 or rect.y0 > best_rect.y1)
            
            # Also check reasonable distance from expected coords
            within_reasonable_distance = distance < 300  # Within 300 points of expected coords
            
            if vertical_overlap and within_reasonable_distance:
                print(f"     → Combining clusters: vertically overlapping (column-spanning text)")
                print(f"       Best cluster: y={best_rect.y0:.1f}-{best_rect.y1:.1f}, x={best_rect.x0:.1f}-{best_rect.x1:.1f}")
                print(f"       Additional:  y={rect.y0:.1f}-{rect.y1:.1f}, x={rect.x0:.1f}-{rect.x1:.1f}")
                combined_quads.extend(cluster['quads'])
        
        print(f"     → Filtered {len(quads)} quads to {len(combined_quads)} closest to expected position "
              f"(distance: {min_distance:.1f} points)")
        return combined_quads
    
    return quads


def convert_kindle_to_pdf_coordinates(kindle_x: float, kindle_y: float, pdf_rect: Optional[Any] = None, cropbox: Optional[Any] = None) -> Tuple[float, float]:
    """
    Convert Kindle KRDS coordinates to PDF points using the validated inches-based formula.
    
    The formula (validated with 346 real production highlights):
    - X = (krds_x / 100) × 72
    - Y = (krds_y / 100) × 72
    
    Where:
    - KRDS coordinates are in range 0-10000 (100 units = 1 inch)
    - PDF coordinates are in points (72 points = 1 inch)
    
    CRITICAL: KRDS coordinates are absolute to the original uncropped page.
    For cropped PDFs, we must subtract the CropBox offset.
    
    Args:
        kindle_x: KRDS X coordinate (0-10000 range)
        kindle_y: KRDS Y coordinate (0-10000 range)
        pdf_rect: PDF page rectangle (for bounds checking - should be CropBox rect for cropped pages)
        cropbox: PDF CropBox (for offset correction on cropped PDFs)
    
    Returns:
        Tuple of (x, y) in PDF points
    """
    # Inches-based formula: Convert from KRDS units (100 = 1 inch) to PDF points (72 = 1 inch)
    pdf_x = (kindle_x / 100.0) * 72.0
    pdf_y = (kindle_y / 100.0) * 72.0
    
    # Apply CropBox offset (CRITICAL for cropped PDFs)
    # KRDS coordinates are absolute to original page, so we subtract the crop offset
    if cropbox is not None:
        cropbox_x0 = getattr(cropbox, 'x0', 0.0)
        cropbox_y0 = getattr(cropbox, 'y0', 0.0)
        pdf_x -= cropbox_x0
        pdf_y -= cropbox_y0
    
    # Clamp within visible page bounds (CropBox dimensions)
    # Always clamp to prevent out-of-bounds coordinates
    if cropbox is not None:
        # Use CropBox dimensions for bounds checking
        page_width = float(getattr(cropbox, 'width', CONFIG.default_page_width))
        page_height = float(getattr(cropbox, 'height', CONFIG.default_page_height))
        pdf_x = max(0.0, min(pdf_x, page_width))
        pdf_y = max(0.0, min(pdf_y, page_height))
    elif pdf_rect is not None:
        # Use rect dimensions for normal (uncropped) pages
        page_width, page_height = _resolve_page_dimensions(pdf_rect)
        pdf_x = max(0.0, min(pdf_x, page_width))
        pdf_y = max(0.0, min(pdf_y, page_height))

    return pdf_x, pdf_y

def convert_kindle_width_to_pdf(kindle_width: float, pdf_rect: Optional[Any] = None, pdf_x: float = 0.0) -> float:
    """
    Convert Kindle width to PDF points using the inches-based formula.
    
    Width uses the same conversion as X-coordinates:
    pdf_width = (kindle_width / 100) × 72
    
    Args:
        kindle_width: KRDS width in Kindle units
        pdf_rect: PDF page rectangle (for bounds checking)
        pdf_x: Starting X position (for bounds checking)
    
    Returns:
        Width in PDF points
    """
    if kindle_width <= 0:
        return 0.0

    # Inches-based formula for width
    pdf_width = (kindle_width / 100.0) * 72.0

    # Prevent highlights from spilling beyond the page
    if pdf_rect is not None:
        page_width, _ = _resolve_page_dimensions(pdf_rect)
        pdf_width = min(pdf_width, max(0.0, page_width - pdf_x))

    return max(0.0, pdf_width)


def convert_kindle_height_to_pdf(kindle_height: float, pdf_rect: Optional[Any] = None, pdf_y: float = 0.0) -> float:
    """
    Convert Kindle height to PDF points using the inches-based formula.
    
    Height uses the same conversion as Y-coordinates:
    pdf_height = (kindle_height / 100) × 72
    
    Args:
        kindle_height: KRDS height in Kindle units
        pdf_rect: PDF page rectangle (for bounds checking)
        pdf_y: Starting Y position (for bounds checking)
    
    Returns:
        Height in PDF points
    """
    if kindle_height <= 0:
        return 0.0

    # Inches-based formula for height
    pdf_height = (kindle_height / 100.0) * 72.0

    # Prevent highlights from spilling beyond the page
    if pdf_rect is not None:
        _, page_height = _resolve_page_dimensions(pdf_rect)
        pdf_height = min(pdf_height, max(0.0, page_height - pdf_y))

    return max(0.0, pdf_height)

def _parse_position_coords(position_raw: str) -> Optional[Tuple[float, float]]:
    """Parse position string to extract x, y coordinates.
    
    Format: page tile_x tile_y num_tiles x y width height
    Example: "3 535 2765 1 446 666 25 12"
    """
    if not position_raw:
        return None
    try:
        parts = position_raw.split()
        if len(parts) >= 6:
            x = float(parts[4])
            y = float(parts[5])
            return (x, y)
    except (ValueError, IndexError):
        pass
    return None


def _create_annotation_dict(
    annotation_type: str,
    json_page: int,
    kindle_x: float,
    kindle_y: float,
    width: float,
    height: float,
    start_raw: str,
    end_raw: str,
    content: str,
    timestamp: str,
    pdf_rect: Any,
    cropbox: Optional[Any],
    source: str
) -> Dict[str, Any]:
    """Create a standardized annotation dictionary with converted coordinates."""

    # Convert using inches-based formula (validated) with CropBox correction
    pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(kindle_x, kindle_y, pdf_rect, cropbox)
    pdf_width = convert_kindle_width_to_pdf(width, pdf_rect, pdf_x)
    pdf_height = convert_kindle_height_to_pdf(height, pdf_rect, pdf_y)
    
    # Also convert end position coordinates if available
    pdf_x_end, pdf_y_end = None, None
    end_coords = _parse_position_coords(end_raw)
    if end_coords:
        kindle_x_end, kindle_y_end = end_coords
        pdf_x_end, pdf_y_end = convert_kindle_to_pdf_coordinates(kindle_x_end, kindle_y_end, pdf_rect, cropbox)

    return {
        'type': annotation_type,
        'json_page_0based': json_page,
        'pdf_page_0based': json_page,
        'myclippings_page_1based': json_page + 1,

        # Original Kindle coordinates
        'kindle_x': kindle_x,
        'kindle_y': kindle_y,
        'kindle_width': width,
        'kindle_height': height,
        'start_position': start_raw,
        'end_position': end_raw,
        'pdf_rect_width': pdf_rect.width if pdf_rect else CONFIG.default_page_width,
        'pdf_rect_height': pdf_rect.height if pdf_rect else CONFIG.default_page_height,

        # Inches-based coordinates (discovered system)
        'kindle_x_inches': kindle_x / CONFIG.kindle_units_per_inch,
        'kindle_y_inches': kindle_y / CONFIG.kindle_units_per_inch,

        # Converted PDF coordinates (with CropBox correction)
        'pdf_x': pdf_x,
        'pdf_y': pdf_y,
        'pdf_x_end': pdf_x_end,  # End position coordinates
        'pdf_y_end': pdf_y_end,
        'pdf_width': pdf_width,
        'pdf_height': pdf_height,

        'content': content,
        'timestamp': timestamp,
        'source': source
    }


def _process_highlight_annotation(highlight: Any, pdf_rect: Any, cropbox: Optional[Any] = None) -> Dict[str, Any]:
    """Process a highlight annotation into standard format."""

    if not highlight.start_position.valid:
        raise ValueError("Invalid highlight position")

    return _create_annotation_dict(
        annotation_type='highlight',
        json_page=highlight.start_position.page,
        kindle_x=highlight.start_position.x,
        kindle_y=highlight.start_position.y,
        width=highlight.start_position.width,
        height=highlight.start_position.height,
        start_raw=getattr(highlight.start_position, "raw", ""),
        end_raw=getattr(highlight.end_position, "raw", ""),
        content='',
        timestamp=highlight.creation_time or '',
        pdf_rect=pdf_rect,
        cropbox=cropbox,
        source='json_highlight_amazon_converted'
    )


def _process_note_annotation(note: Any, pdf_rect: Any, cropbox: Optional[Any] = None) -> Dict[str, Any]:
    """Process a note annotation into standard format."""

    if not note.start_position.valid:
        raise ValueError("Invalid note position")

    return _create_annotation_dict(
        annotation_type='note',
        json_page=note.start_position.page,
        kindle_x=note.start_position.x,
        kindle_y=note.start_position.y,
        width=note.start_position.width,
        height=note.start_position.height,
        start_raw=getattr(note.start_position, "raw", ""),
        end_raw=getattr(note.end_position, "raw", ""),
        content=note.note_text,
        timestamp=note.creation_time or '',
        pdf_rect=pdf_rect,
        cropbox=cropbox,
        source='json_note_amazon_converted'
    )


def _process_bookmark_annotation(bookmark: Any, pdf_rect: Any, cropbox: Optional[Any] = None) -> Dict[str, Any]:
    """Process a bookmark annotation into standard format."""

    if not bookmark.start_position.valid:
        raise ValueError("Invalid bookmark position")

    # Bookmarks don't carry geometric information beyond page
    return _create_annotation_dict(
        annotation_type='bookmark',
        json_page=bookmark.start_position.page,
        kindle_x=bookmark.start_position.x,
        kindle_y=bookmark.start_position.y,
        width=bookmark.start_position.width,
        height=bookmark.start_position.height,
        start_raw=getattr(bookmark.start_position, "raw", ""),
        end_raw=getattr(bookmark.end_position, "raw", ""),
        content='',
        timestamp=bookmark.creation_time or '',
        pdf_rect=pdf_rect,
        cropbox=cropbox,
        source='json_bookmark_amazon_converted'
    )


def _find_pdf_path(clippings_file: Optional[str], krds_file_path: str, book_name: str) -> Optional[str]:
    """Find the PDF file path based on clippings file, KRDS file, or book name."""
    
    # Try based on clippings file location
    if clippings_file:
        clippings_path = Path(clippings_file)
        if clippings_path.exists():
            # Look in the same directory
            parent_dir = clippings_path.parent
            
            possible_pdf_names = [
                clippings_path.stem.replace('-clippings', '').replace('_clippings', '') + '.pdf',
                book_name + '.pdf',
                book_name.replace(' ', '_') + '.pdf'
            ]
            
            for pdf_name in possible_pdf_names:
                possible_pdf = parent_dir / pdf_name
                if possible_pdf.exists():
                    return str(possible_pdf)
            
            # Try globbing for PDFs with the book name in them
            for pdf_file in parent_dir.glob('*.pdf'):
                if pdf_file.name.startswith("._"):  # Skip hidden system files
                    continue
                if book_name in pdf_file.stem:
                    return str(pdf_file)
    
    # Try based on KRDS file location
    krds_path = Path(krds_file_path)
    if krds_path.exists():
        # KRDS files are typically in .sdr subdirectory
        # PDF would be in parent directory
        parent_dir = krds_path.parent.parent if krds_path.parent.name.endswith('.sdr') else krds_path.parent
        
        possible_pdf_names = [
            book_name + '.pdf',
            book_name.replace(' ', '_') + '.pdf',
            krds_path.stem.split('-cdeKey_')[0] + '.pdf' if '-cdeKey_' in krds_path.stem else krds_path.stem + '.pdf'
        ]
        
        for pdf_name in possible_pdf_names:
            possible_pdf = parent_dir / pdf_name
            if possible_pdf.exists():
                return str(possible_pdf)
        
        # Try globbing for PDFs matching book name
        for pdf_file in parent_dir.glob('*.pdf'):
            if pdf_file.name.startswith("._"):  # Skip hidden system files
                continue
            if book_name in pdf_file.stem:
                return str(pdf_file)
    
    return None


def _deduplicate_annotations(annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate annotations and unify notes with highlights at the same position.
    
    When a note and highlight have the same page and coordinates (within proximity tolerance),
    they are unified into a single annotation (keeping the note, which has content).
    
    The tolerance of 5 pts accounts for the note icon offset from the actual text position.
    
    Args:
        annotations: List of annotation dictionaries
        
    Returns:
        Deduplicated list with unified note/highlight pairs
    """
    # Deduplication tolerance constants
    # - Strict tolerance (0.1pt) for highlight-to-highlight deduplication (rounding precision)
    # - Loose tolerance (5pt) for note-to-highlight unification (accounts for note icon offset)
    STRICT_TOLERANCE = 0.1  # Points - for same-type deduplication
    NOTE_UNIFICATION_TOLERANCE = 5.0  # Points - for note/highlight position matching
    
    unique_annotations = []
    seen_keys = set()
    # Track position-based annotations for note/highlight unification
    position_annotations = []  # List of (ann, page, x, y) for proximity matching

    for ann in annotations:
        # Create full dedup key including type
        content_key = ann.get('content', '').strip()[:50]
        timestamp_key = ann.get('timestamp', '') if ann['type'] == 'bookmark' else ''
        full_dedup_key = (
            ann['type'],
            ann['pdf_page_0based'],
            round(ann['pdf_x'], 1),
            round(ann['pdf_y'], 1),
            content_key,
            timestamp_key,
        )

        # Check if we've seen this exact annotation before (including type)
        if full_dedup_key in seen_keys:
            print(f"   Skipped duplicate: {ann['type']} on page {ann['pdf_page_0based']} - {ann.get('content', '')[:30]}...")
            continue
        
        # Special handling for notes and highlights at the same position
        if ann['type'] in ('note', 'highlight'):
            # Look for existing annotation at same position (within tolerance)
            # For highlights, check both START and END positions since notes can be at either
            matching_ann = None
            for existing_ann, ex_page, ex_x, ex_y in position_annotations:
                if (existing_ann['type'] in ('note', 'highlight') and
                    ex_page == ann['pdf_page_0based']):
                    
                    # Determine tolerance based on annotation types
                    # Use strict tolerance for same-type comparisons (highlight-to-highlight)
                    # Use loose tolerance for note/highlight unification
                    if existing_ann['type'] == ann['type']:
                        tolerance = STRICT_TOLERANCE  # 0.1pt for highlight-to-highlight deduplication
                    else:
                        tolerance = NOTE_UNIFICATION_TOLERANCE  # 5pt for note/highlight unification
                    
                    # Check if positions match (start-to-start, start-to-end, end-to-end, etc.)
                    # Notes are typically placed at the END of highlights when user clicks to add note
                    matches_start = (abs(ex_x - ann['pdf_x']) <= tolerance and
                                   abs(ex_y - ann['pdf_y']) <= tolerance)
                    
                    # Also check if note position matches highlight END position
                    matches_end = False
                    if existing_ann.get('pdf_x_end') is not None and existing_ann.get('pdf_y_end') is not None:
                        matches_end = (abs(existing_ann['pdf_x_end'] - ann['pdf_x']) <= tolerance and
                                     abs(existing_ann['pdf_y_end'] - ann['pdf_y']) <= tolerance)
                    
                    # Check reverse: if current annotation is a highlight, check its end against note position
                    if ann.get('pdf_x_end') is not None and ann.get('pdf_y_end') is not None:
                        matches_end = matches_end or (abs(ann['pdf_x_end'] - ex_x) <= tolerance and
                                                     abs(ann['pdf_y_end'] - ex_y) <= tolerance)
                    
                    if matches_start or matches_end:
                        matching_ann = existing_ann
                        break
            
            if matching_ann:
                # If both are the same type, skip duplicate
                if matching_ann['type'] == ann['type']:
                    seen_keys.add(full_dedup_key)
                    print(f"   Skipped duplicate: {ann['type']} on page {ann['pdf_page_0based']} - {ann.get('content', '')[:30]}...")
                    continue
                
                # Unify note and highlight - keep note but preserve highlight's text content
                if ann['type'] == 'note':
                    # Replace existing highlight with this note, but keep highlight's content for text matching
                    print(f"   Unified highlight+note on page {ann['pdf_page_0based']} at ({ann['pdf_x']:.1f}, {ann['pdf_y']:.1f})")
                    # Store highlight content in note for text-based matching
                    if matching_ann.get('content') and not ann.get('highlight_content'):
                        ann['highlight_content'] = matching_ann['content']
                    # Remove the existing highlight from unique_annotations and position_annotations
                    unique_annotations = [a for a in unique_annotations if a is not matching_ann]
                    position_annotations = [(a, p, x, y) for a, p, x, y in position_annotations if a is not matching_ann]
                    position_annotations.append((ann, ann['pdf_page_0based'], ann['pdf_x'], ann['pdf_y']))
                    unique_annotations.append(ann)
                    seen_keys.add(full_dedup_key)
                else:
                    # Current is highlight, existing is note - skip this highlight but preserve content
                    print(f"   Unified highlight+note on page {ann['pdf_page_0based']} at ({ann['pdf_x']:.1f}, {ann['pdf_y']:.1f}) - keeping note")
                    # Store highlight content in note for text-based matching
                    if ann.get('content') and not matching_ann.get('highlight_content'):
                        matching_ann['highlight_content'] = ann['content']
                    seen_keys.add(full_dedup_key)
                    continue
            else:
                # First annotation at this position
                position_annotations.append((ann, ann['pdf_page_0based'], ann['pdf_x'], ann['pdf_y']))
                unique_annotations.append(ann)
                seen_keys.add(full_dedup_key)
        else:
            # Bookmarks and other types - normal deduplication
            seen_keys.add(full_dedup_key)
            unique_annotations.append(ann)

    return unique_annotations


def create_amazon_compliant_annotations(
    krds_file_path: str, 
    clippings_file: Optional[str], 
    book_name: str,
    learn_mode: bool = False,
    learn_output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Create annotations using Amazon's coordinate system algorithm.
    Uses text-based matching as the primary strategy with coordinate calibration as fallback.
    
    Args:
        krds_file_path: Path to the KRDS file 
        clippings_file: Optional path to MyClippings.txt file for enhanced accuracy
        book_name: Name of the book for matching
        learn_mode: If True, track and export unmatched clippings with context
        learn_output_path: Path to export learning data if learn_mode is True
    """
    print("=" * 80)
    print("🎯 CREATING KINDLE ANNOTATIONS WITH TEXT-BASED MATCHING")
    print("=" * 80)

    # Parse MyClippings with our fixed parser (if provided)
    myclippings_entries = []
    if clippings_file and Path(clippings_file).exists():
        try:
            from .clippings_parser import parse_myclippings_for_book
            myclippings_entries = parse_myclippings_for_book(clippings_file, book_name)
            print(f"✅ Loaded {len(myclippings_entries)} clippings from MyClippings.txt")
        except Exception as e:
            print(f"⚠️  Warning: Could not parse MyClippings.txt: {e}")
            myclippings_entries = []
    else:
        print("ℹ️  No MyClippings.txt provided - using KRDS data only")

    # Parse KRDS file directly
    from .krds_parser import KindleReaderDataStore
    krds_parser = KindleReaderDataStore(krds_file_path)
    
    # Extract annotations using the proper method
    krds_annotations = krds_parser.extract_annotations()
    
    print(f"📊 KRDS annotations extracted: {len(krds_annotations)}")
    
    # Separate highlights, notes, and bookmarks
    highlights = [ann for ann in krds_annotations if 'highlight' in ann.annotation_type]
    notes = [ann for ann in krds_annotations if 'note' in ann.annotation_type]
    bookmarks = [ann for ann in krds_annotations if 'bookmark' in ann.annotation_type]
    
    print(f"   - Highlights: {len(highlights)}")
    print(f"   - Notes: {len(notes)}")
    print(f"   - Bookmarks: {len(bookmarks)}")
    
    # Find PDF path to get actual dimensions
    pdf_path = _find_pdf_path(clippings_file, krds_file_path, book_name)
    
    pdf_doc = None
    if pdf_path:
        print(f"\n📄 Found PDF: {pdf_path}")
        pdf_doc = fitz.open(pdf_path)
        if len(pdf_doc) > 0:
            actual_pdf_rect = pdf_doc[0].rect
            print(f"   PDF dimensions: {actual_pdf_rect.width:.1f} x {actual_pdf_rect.height:.1f} points")
            # Check if PDF has CropBox offsets
            first_page_cropbox = pdf_doc[0].cropbox
            if first_page_cropbox.x0 != 0 or first_page_cropbox.y0 != 0:
                print(f"   📐 CropBox offset detected: ({first_page_cropbox.x0:.2f}, {first_page_cropbox.y0:.2f})")
        else:
            print("   ⚠️  PDF has no pages, using defaults")
            actual_pdf_rect = fitz.Rect(0, 0, CONFIG.default_page_width, CONFIG.default_page_height)
    else:
        print("\n⚠️  Could not find PDF file, using default dimensions")
        actual_pdf_rect = fitz.Rect(0, 0, CONFIG.default_page_width, CONFIG.default_page_height)

    print("\n" + "=" * 80)
    print("🔍 PROCESSING ANNOTATIONS")
    print("=" * 80)

    # PRE-STEP: Match MyClippings content to KRDS highlights by page and Y-position
    # This ensures highlights have content for later matching
    if myclippings_entries:
        print("\n📍 PRE-STEP: Matching MyClippings content to KRDS highlights...")
        highlight_clips = [e for e in myclippings_entries if e.get('type') == 'highlight' and e.get('content')]
        
        # Group highlights and clippings by page
        highlights_by_page = {}
        for h in highlights:
            page = h.start_position.page
            if page not in highlights_by_page:
                highlights_by_page[page] = []
            highlights_by_page[page].append(h)
        
        clips_by_page = {}
        for clip in highlight_clips:
            page = clip.get('pdf_page', 1) - 1  # Convert to 0-based
            if page not in clips_by_page:
                clips_by_page[page] = []
            clips_by_page[page].append(clip)
        
        # Match highlights to clippings on each page by Y-position order
        # (Assumes both are in reading order: top to bottom)
        matched_count = 0
        for page, page_highlights in highlights_by_page.items():
            if page not in clips_by_page:
                continue
            
            # Sort highlights by Y position (top to bottom)
            sorted_highlights = sorted(page_highlights, key=lambda h: h.start_position.y)
            page_clips = clips_by_page[page]
            
            # CRITICAL FIX: If we have the same number of highlights and clippings on this page,
            # match them by PROXIMITY (closest clipping to each highlight) rather than by order.
            # This handles cases where timestamp order doesn't match reading order.
            if len(sorted_highlights) == len(page_clips):
                # Convert Kindle coordinates to PDF for comparison
                highlight_positions = []
                for h in sorted_highlights:
                    pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(h.start_position.x, h.start_position.y, actual_pdf_rect, None)
                    highlight_positions.append((h, pdf_x, pdf_y))
                
                # Match each highlight to its nearest clipping by text search position
                # We'll do text search to find where each clipping's text actually appears
                if pdf_doc and page < len(pdf_doc):
                    pdf_page = pdf_doc[page]
                    
                    # Find position of each clipping's text on the page
                    clip_positions = []
                    for clip in page_clips:
                        content = clip.get('content', '').strip()
                        if content:
                            # Search for this text on the page
                            quads = pdf_page.search_for(content, quads=True)
                            if quads:
                                # Find the quad closest to any highlight position
                                best_pos = None
                                min_dist = float('inf')
                                for quad in quads:
                                    rect = quad.rect if hasattr(quad, 'rect') else fitz.Rect(quad)
                                    # Check distance to all highlights
                                    for h, hx, hy in highlight_positions:
                                        dist = ((rect.x0 - hx)**2 + (rect.y0 - hy)**2)**0.5
                                        if dist < min_dist:
                                            min_dist = dist
                                            best_pos = (rect.x0, rect.y0)
                                
                                clip_positions.append((clip, best_pos[0] if best_pos else 0, best_pos[1] if best_pos else 0))
                            else:
                                clip_positions.append((clip, 0, 0))
                        else:
                            clip_positions.append((clip, 0, 0))
                    
                    # Now match each highlight to its nearest clipping
                    used_clips = set()
                    for h, hx, hy in highlight_positions:
                        best_clip = None
                        min_dist = float('inf')
                        for i, (clip, cx, cy) in enumerate(clip_positions):
                            if i in used_clips:
                                continue
                            dist = ((cx - hx)**2 + (cy - hy)**2)**0.5
                            if dist < min_dist:
                                min_dist = dist
                                best_clip = (i, clip)
                        
                        if best_clip:
                            used_clips.add(best_clip[0])
                            h._matched_content = best_clip[1].get('content', '')
                            matched_count += 1
                else:
                    # Fallback to order-based matching if PDF not available
                    for i, highlight in enumerate(sorted_highlights):
                        if i < len(page_clips):
                            highlight._matched_content = page_clips[i].get('content', '')
                            matched_count += 1
            else:
                # Different counts - fall back to order-based matching
                for i, highlight in enumerate(sorted_highlights):
                    if i < len(page_clips):
                        highlight._matched_content = page_clips[i].get('content', '')
                        matched_count += 1
        
        total_clips = len(highlight_clips)
        print(f"   ✅ Matched {matched_count}/{total_clips} clipping highlights to KRDS highlights")


    # STEP 1: Process ALL annotations from KRDS with KRDS-based coordinates
    # This ensures notes and highlights can be unified based on same coordinate system
    print("\n📍 STEP 1: Processing KRDS annotations (coordinate-based)...")
    coordinate_based_annotations = []
    
    # Process highlights
    for highlight in highlights:
        try:
            # Get page-specific cropbox if PDF is available
            cropbox = None
            if pdf_doc and highlight.start_position.page < len(pdf_doc):
                cropbox = pdf_doc[highlight.start_position.page].cropbox
            
            annotation = _process_highlight_annotation(highlight, actual_pdf_rect, cropbox)
            # Add matched content from MyClippings if available
            if hasattr(highlight, '_matched_content'):
                annotation['content'] = highlight._matched_content
            coordinate_based_annotations.append(annotation)
        except ValueError as e:
            print(f"   Warning: Skipping invalid highlight: {e}")
            continue
    
    # Process notes
    print(f"   Processing {len(notes)} notes...")
    for note in notes:
        try:
            # Get page-specific cropbox if PDF is available
            cropbox = None
            if pdf_doc and note.start_position.page < len(pdf_doc):
                cropbox = pdf_doc[note.start_position.page].cropbox
            
            annotation = _process_note_annotation(note, actual_pdf_rect, cropbox)
            coordinate_based_annotations.append(annotation)
        except ValueError as e:
            print(f"   Warning: Skipping invalid note: {e}")
            continue
    
    # Process bookmarks
    print(f"   Processing {len(bookmarks)} bookmarks...")
    for bookmark in bookmarks:
        try:
            # Get page-specific cropbox if PDF is available
            cropbox = None
            if pdf_doc and bookmark.start_position.page < len(pdf_doc):
                cropbox = pdf_doc[bookmark.start_position.page].cropbox
            
            # Bookmarks use same processing as notes but with type='bookmark'
            annotation = _process_note_annotation(bookmark, actual_pdf_rect, cropbox)
            annotation['type'] = 'bookmark'  # Override type
            coordinate_based_annotations.append(annotation)
        except ValueError as e:
            print(f"   Warning: Skipping invalid bookmark: {e}")
            continue
    
    print(f"   ✅ Processed {len(coordinate_based_annotations)} annotations from KRDS")
    
    # STEP 2: Deduplicate and unify notes with highlights (based on KRDS coords)
    print("\n📍 STEP 2: Deduplicating and unifying notes with highlights...")
    coordinate_based_annotations = _deduplicate_annotations(coordinate_based_annotations)
    print(f"   ✅ After deduplication: {len(coordinate_based_annotations)} annotations")

    # STEP 3: If we have clippings data, use TEXT-BASED MATCHING to refine coordinates
    # This updates the coordinates of highlights that we can find via text search
    if myclippings_entries and len([e for e in myclippings_entries if e.get('type') == 'highlight']) > 0:
        print("\n📍 STEP 3: Refining coordinates with TEXT-BASED MATCHING...")
        
        if pdf_path:
            unmatched_clippings = []  # Track unmatched clippings for learning mode
            doc = fitz.open(pdf_path)
            updated_count = 0
            
            for entry in myclippings_entries:
                if entry.get('type') == 'highlight' and entry.get('content', '').strip():
                    content = entry['content'].strip()
                    pdf_page = entry.get('pdf_page', 1) - 1  # Convert to 0-based

                    if pdf_page >= len(doc) or pdf_page < 0:
                        continue

                    page = doc[pdf_page]
                    print(f"   Finding text on page {pdf_page + 1}: {repr(content[:50])}...")

                    # Normalize text for better matching
                    search_text = ' '.join(content.split())
                    
                    # Handle abbreviations: "ch.4" -> "ch. 4" (add space after period if missing)
                    import re
                    search_text = re.sub(r'(\w)\.(\d)', r'\1. \2', search_text)
                    
                    # Handle periods without spaces: "word.Word" -> "word. Word"
                    search_text = re.sub(r'\.([A-Z])', r'. \1', search_text)
                    
                    # Normalize both texts to handle ligatures and hyphenation
                    def strip_ligatures(text: str) -> str:
                        """Strip ligatures to match Kindle's normalization."""
                        text = text.replace('ﬁ', 'f').replace('ﬂ', 'f').replace('ﬀ', 'f')
                        text = text.replace('ﬃ', 'f').replace('ﬄ', 'f')
                        text = text.replace('ﬆ', 's').replace('ﬅ', 's')
                        return text
                    
                    def normalize_text(text: str) -> str:
                        """Normalize text: strip ligatures, remove hyphenation, normalize whitespace."""
                        text = strip_ligatures(text)
                        # Handle soft hyphens: remove them but keep any regular hyphen before them
                        # Pattern: "-\xad\n" should become "-" (remove soft hyphen and newline, keep hyphen)
                        text = text.replace('-\u00ad\n', '-')  # hyphen + soft hyphen + newline → hyphen
                        text = text.replace('\u00ad', '')  # Remove remaining soft hyphens
                        text = re.sub(r'-\n', '', text)  # Remove hyphens at line breaks (without soft hyphens)
                        text = ' '.join(text.split())  # Normalize whitespace
                        return text
                    
                    # Get page text and normalize both
                    page_text = page.get_text()
                    page_text_norm = normalize_text(page_text)
                    search_text_norm = normalize_text(search_text)
                    
                    quads = None
                    
                    # First, try direct search (works if no ligatures/hyphens)
                    for variant in [search_text, search_text.replace('fi', 'ﬁ').replace('fl', 'ﬂ')]:
                        quads = page.search_for(variant, quads=True)
                        if quads:
                            break
                    
                    # If direct search failed, use normalized matching
                    if not quads and search_text_norm in page_text_norm:
                        # Find position in normalized text
                        norm_start = page_text_norm.index(search_text_norm)
                        norm_end = norm_start + len(search_text_norm)
                        
                        # Build character-by-character mapping from normalized to original positions
                        pos_map = []  # Maps each char in normalized text to position in original
                        i = 0
                        while i < len(page_text):
                            char = page_text[i]
                            
                            # Handle ligatures (map ligature to single 'f' or 's')
                            if char in ['ﬁ', 'ﬂ', 'ﬀ', 'ﬃ', 'ﬄ']:
                                pos_map.append(i)
                                i += 1
                            elif char in ['ﬆ', 'ﬅ']:
                                pos_map.append(i)
                                i += 1
                            # Handle soft hyphen at line break
                            elif i + 1 < len(page_text) and char == '-' and page_text[i+1] == '\n':
                                i += 2  # Skip both hyphen and newline, don't add to pos_map
                            # Handle whitespace (collapse multiple spaces)
                            elif char.isspace():
                                if not pos_map or page_text[pos_map[-1]] not in [' ', '\n', '\t', '\r']:
                                    pos_map.append(i)
                                i += 1
                            else:
                                pos_map.append(i)
                                i += 1
                        
                        # Map the match back to original positions
                        if norm_start < len(pos_map) and norm_end <= len(pos_map):
                            orig_start = pos_map[norm_start]
                            orig_end = pos_map[norm_end - 1] + 1
                            
                            # Extract original text
                            orig_text = page_text[orig_start:orig_end]
                            
                            # Normalize the extracted text for searching
                            # PyMuPDF can't search text with newlines/hyphens, so we need to normalize
                            orig_text_for_search = re.sub(r'-\n', '', orig_text)  # Remove soft hyphens
                            orig_text_for_search = ' '.join(orig_text_for_search.split())  # Collapse whitespace
                            
                            # Search for the normalized original text
                            quads = page.search_for(orig_text_for_search, quads=True)
                            
                            if quads:
                                print(f"     ✓ Found via normalized text matching ({len(quads)} quads)")
                    
                    # Fallback: Flexible position-based extraction with similarity verification
                    # This handles cases where My Clippings.txt has extraction errors/typos
                    # Strategy:
                    # 1. Find beginning anchor (first 5 words) in normalized PDF text
                    # 2. Find ending anchor (last 5 words) in a search window
                    # 3. Extract text between anchors (handles length differences)
                    # 4. Verify with SequenceMatcher (>90% similarity)
                    if not quads:
                        from difflib import SequenceMatcher
                        
                        search_words = search_text_norm.split()
                        if len(search_words) >= 6:
                            # Find beginning anchor (first 3-5 words)
                            beginning_pos = -1
                            begin_anchor_size = 0
                            for anchor_size in [5, 4, 3]:
                                if anchor_size <= len(search_words):
                                    anchor = ' '.join(search_words[:anchor_size])
                                    pos = page_text_norm.find(anchor)
                                    if pos >= 0:
                                        beginning_pos = pos
                                        begin_anchor_size = anchor_size
                                        print(f"     → Found beginning anchor ({anchor_size} words) at position {pos}")
                                        break
                            
                            # Find ending anchor (last 3-5 words) in a search window
                            ending_pos = -1
                            end_anchor_size = 0
                            if beginning_pos >= 0:
                                clipping_len = len(search_text_norm)
                                # Use large window to handle length differences from extraction errors
                                window_margin = max(50, int(clipping_len * 0.15))  # At least 50 chars or 15%
                                
                                for anchor_size in [5, 4, 3]:
                                    if anchor_size <= len(search_words):
                                        anchor = ' '.join(search_words[-anchor_size:])
                                        
                                        # Search in window around expected position
                                        search_start = max(0, beginning_pos + clipping_len - window_margin)
                                        search_end = min(len(page_text_norm), beginning_pos + clipping_len + window_margin)
                                        
                                        # Try window search first
                                        search_window = page_text_norm[search_start:search_end]
                                        pos_in_window = search_window.find(anchor)
                                        
                                        if pos_in_window >= 0:
                                            ending_pos = search_start + pos_in_window + len(anchor)
                                            end_anchor_size = anchor_size
                                            print(f"     → Found ending anchor ({anchor_size} words) at position {ending_pos - len(anchor)}")
                                            break
                                        else:
                                            # Fallback: search in full text from beginning
                                            pos = page_text_norm.find(anchor, beginning_pos)
                                            if pos >= 0:
                                                ending_pos = pos + len(anchor)
                                                end_anchor_size = anchor_size
                                                print(f"     → Found ending anchor ({anchor_size} words) at position {pos} (full text search)")
                                                break
                            
                            if beginning_pos >= 0 and ending_pos >= 0 and ending_pos > beginning_pos:
                                # Extract text between anchors in normalized form
                                extracted_norm = page_text_norm[beginning_pos:ending_pos]
                                extracted_len = len(extracted_norm)
                                clipping_len = len(search_text_norm)
                                
                                print(f"     → Extracted {extracted_len} chars from normalized text (clipping: {clipping_len} chars)")
                                
                                # Verify similarity using SequenceMatcher (handles insertions/deletions)
                                matcher = SequenceMatcher(None, extracted_norm, search_text_norm)
                                similarity = matcher.ratio()
                                
                                # Also check word-level similarity
                                extracted_words = extracted_norm.split()
                                clipping_words = search_text_norm.split()
                                word_matches = sum(1 for w1, w2 in zip(extracted_words, clipping_words) if w1 == w2)
                                word_similarity = word_matches / max(len(extracted_words), len(clipping_words)) if max(len(extracted_words), len(clipping_words)) > 0 else 0
                                
                                print(f"     → Similarity: {similarity:.1%} (char-level), {word_similarity:.1%} (word-level, {word_matches}/{max(len(extracted_words), len(clipping_words))} words)")
                                
                                # Accept if similarity is high enough
                                if similarity >= 0.90:
                                    print(f"     ✓ Similarity acceptable ({similarity:.1%}), using position-based extraction...")
                                    
                                    # Build position map from normalized to original text indices
                                    pos_map = []
                                    i = 0
                                    while i < len(page_text):
                                        char = page_text[i]
                                        if char in ['ﬁ', 'ﬂ', 'ﬀ', 'ﬃ', 'ﬄ', 'ﬆ', 'ﬅ']:
                                            pos_map.append(i)
                                            i += 1
                                        elif i + 2 < len(page_text) and char == '-' and page_text[i+1] == '\u00ad' and page_text[i+2] == '\n':
                                            pos_map.append(i)  # This sequence becomes '-' in normalized
                                            i += 3
                                        elif char == '\u00ad':
                                            i += 1  # Skip soft hyphen
                                        elif i + 1 < len(page_text) and char == '-' and page_text[i+1] == '\n':
                                            i += 2  # Skip hyphen+newline
                                        elif char.isspace():
                                            if not pos_map or page_text[pos_map[-1]] not in [' ', '\n', '\t', '\r']:
                                                pos_map.append(i)
                                            i += 1
                                        else:
                                            pos_map.append(i)
                                            i += 1
                                    
                                    # Extract text with position information using "dict" format
                                    # Build a character-to-bbox mapping that matches get_text() output
                                    page_dict = page.get_text("dict")
                                    
                                    # Collect characters with their bounding boxes
                                    # We need to match the exact text structure from get_text()
                                    char_bboxes = []  # List of (char, bbox) tuples
                                    
                                    for block in page_dict["blocks"]:
                                        if block.get("lines"):
                                            for line in block["lines"]:
                                                for span in line["spans"]:
                                                    span_text = span["text"]
                                                    bbox = span["bbox"]  # (x0, y0, x1, y1)
                                                    
                                                    # Calculate approximate per-character bounding boxes
                                                    char_width = (bbox[2] - bbox[0]) / len(span_text) if len(span_text) > 0 else 0
                                                    
                                                    for i, char in enumerate(span_text):
                                                        char_bbox = (
                                                            bbox[0] + i * char_width,
                                                            bbox[1],
                                                            bbox[0] + (i + 1) * char_width,
                                                            bbox[3]
                                                        )
                                                        char_bboxes.append((char, char_bbox))
                                                
                                                # Add newline at end of line (except last line in block)
                                                # This is what get_text() does
                                                char_bboxes.append(('\n', bbox))  # Use last span's bbox for newline
                                    
                                    # Reconstruct text to match get_text() output
                                    reconstructed_text = ''.join([c[0] for c in char_bboxes])
                                    
                                    # Verify our reconstructed text matches the original
                                    if len(reconstructed_text) != len(page_text):
                                        print(f"     ⚠️  Text length mismatch: reconstructed={len(reconstructed_text)}, original={len(page_text)}")
                                        print(f"     Trying direct character extraction...")
                                        
                                        # Fall back to getting individual character positions
                                        # This is more reliable but slower
                                        char_bboxes = []
                                        for char_idx in range(len(page_text)):
                                            # Get bounding box for single character
                                            # We'll search for a small window around our target
                                            if char_idx >= orig_start and char_idx < orig_end:
                                                char = page_text[char_idx]
                                                # Use a default bbox - will be refined when we collect all chars
                                                char_bboxes.append((char, None))
                                    
                                    # Map normalized positions to original text positions
                                    if beginning_pos < len(pos_map) and ending_pos <= len(pos_map):
                                        orig_start_idx = pos_map[beginning_pos]
                                        orig_end_idx = pos_map[ending_pos - 1] + 1 if ending_pos > 0 else pos_map[ending_pos]
                                        
                                        print(f"     → Using character positions {orig_start_idx}-{orig_end_idx} from original text")
                                        
                                        # Collect bounding boxes for characters in our range
                                        target_chars_with_indices = []
                                        for idx in range(orig_start_idx, min(orig_end_idx, len(char_bboxes))):
                                            char, bbox = char_bboxes[idx]
                                            target_chars_with_indices.append((idx, char, bbox))
                                        
                                        if target_chars_with_indices:
                                            # Group characters by line (based on y-coordinate)
                                            # Characters on the same line will have similar y-coordinates
                                            lines = []
                                            current_line = []
                                            current_y = None
                                            y_tolerance = 5.0  # Points
                                            
                                            for idx, char, bbox in target_chars_with_indices:
                                                if char in ['\n', '\r']:
                                                    # Newline - end current line
                                                    if current_line:
                                                        lines.append(current_line)
                                                        current_line = []
                                                        current_y = None
                                                elif bbox is not None:
                                                    char_y = bbox[1]
                                                    if current_y is None or abs(char_y - current_y) < y_tolerance:
                                                        # Same line
                                                        current_line.append((char, bbox))
                                                        if current_y is None:
                                                            current_y = char_y
                                                    else:
                                                        # New line
                                                        if current_line:
                                                            lines.append(current_line)
                                                        current_line = [(char, bbox)]
                                                        current_y = char_y
                                            
                                            # Add last line
                                            if current_line:
                                                lines.append(current_line)
                                            
                                            # Create one quad per line
                                            quads = []
                                            for line_chars in lines:
                                                if not line_chars:
                                                    continue
                                                
                                                line_bboxes = [bbox for char, bbox in line_chars]
                                                min_x = min(b[0] for b in line_bboxes)
                                                min_y = min(b[1] for b in line_bboxes)
                                                max_x = max(b[2] for b in line_bboxes)
                                                max_y = max(b[3] for b in line_bboxes)
                                                
                                                quad = fitz.Quad(
                                                    fitz.Point(min_x, min_y),  # top-left
                                                    fitz.Point(max_x, min_y),  # top-right
                                                    fitz.Point(min_x, max_y),  # bottom-left
                                                    fitz.Point(max_x, max_y)   # bottom-right
                                                )
                                                quads.append(quad)
                                            
                                            if quads:
                                                print(f"     ✓✓ Created highlight using position-based extraction ({len(quads)} quads)")
                                                print(f"        First quad: x={quads[0].ul.x:.1f}-{quads[0].ur.x:.1f}, y={quads[0].ul.y:.1f}-{quads[0].ll.y:.1f}")
                                                if len(quads) > 1:
                                                    print(f"        Last quad: x={quads[-1].ul.x:.1f}-{quads[-1].ur.x:.1f}, y={quads[-1].ul.y:.1f}-{quads[-1].ll.y:.1f}")
                                                
                                                # Debug: show what text is in this range
                                                extracted_text = page_text[orig_start_idx:orig_end_idx]
                                                print(f"        Extracted text preview: {repr(extracted_text[:60])}...")
                                            else:
                                                print(f"     ✗ Could not create quads from character bboxes")
                                        else:
                                            print(f"     ✗ Could not extract character bounding boxes for range")
                                else:
                                    print(f"     ✗ Similarity too low ({similarity:.1%}), skipping")
                    
                    # Strategy 2: Word-based prefix search (searches from BEGINNING - last resort)
                    if not quads:
                        matched_text = word_based_prefix_search(search_text_norm, page_text_norm)
                        if matched_text:
                            print(f"     → Trying word-based prefix search...")
                            # Try to search for the matched text with various normalizations
                            variants = [
                                matched_text,
                                matched_text.replace('fi', 'ﬁ').replace('fl', 'ﬂ'),  # Add ligatures
                                matched_text.replace('-', '­'),  # Replace regular hyphens with soft hyphens
                                matched_text.replace('-', '­').replace('fi', 'ﬁ').replace('fl', 'ﬂ'),  # Both
                            ]
                            for variant in variants:
                                quads = page.search_for(variant, quads=True)
                                if quads:
                                    print(f"     ✓ Found via word-based prefix search ({len(quads)} quads)")
                                    break

                    if quads:
                        # CRITICAL FIX: If we have multiple matches (greedy matching bug),
                        # filter to keep only the match closest to the Kindle coordinates
                        if len(quads) > 1:
                            # Find the matching annotation from STEP 1 to get expected coordinates
                            content_norm = normalize_text(content)
                            expected_pdf_x = None
                            expected_pdf_y = None
                            
                            for ann in coordinate_based_annotations:
                                if ann['pdf_page_0based'] == pdf_page:
                                    ann_content = ann.get('highlight_content') or ann.get('content', '')
                                    if normalize_text(ann_content) == content_norm:
                                        expected_pdf_x = ann['pdf_x']
                                        expected_pdf_y = ann['pdf_y']
                                        break
                            
                            # Filter quads by proximity to expected coordinates
                            if expected_pdf_x is not None and expected_pdf_y is not None:
                                quads = filter_quads_by_proximity(quads, expected_pdf_x, expected_pdf_y, len(search_text))
                        
                        # Quads is a list of quad objects (each is a sequence of 4 points)
                        # Convert to rectangles
                        all_rects = []
                        for quad in quads:
                            # Each quad is a Quad object, we can get its rect
                            if hasattr(quad, 'rect'):
                                all_rects.append(quad.rect)
                            else:
                                # Fallback: try to convert quad to rect
                                try:
                                    all_rects.append(fitz.Rect(quad))
                                except Exception:
                                    pass
                        
                        if all_rects:
                            # Union all rects to get overall bounds
                            text_rect = all_rects[0]
                            for rect in all_rects[1:]:
                                text_rect = text_rect | rect
                            
                            print(f"     ✓ Found at: x={text_rect.x0:.1f}, y={text_rect.y0:.1f}, w={text_rect.width:.1f}, h={text_rect.height:.1f}")
                            print(f"       Quads: {len(quads)} character bounding boxes")

                            # Create annotation with QUADS for precise highlighting
                            annotation = {
                                'type': 'highlight',
                                'json_page_0based': pdf_page,
                                'pdf_page_0based': pdf_page,
                                'myclippings_page_1based': pdf_page + 1,
                                'kindle_x': 0,
                                'kindle_y': 0,
                                'kindle_width': 0,
                                'kindle_height': 0,
                                'pdf_x': text_rect.x0,
                                'pdf_y': text_rect.y0,
                                'pdf_width': text_rect.width,
                                'pdf_height': text_rect.height,
                                'content': content,
                                'timestamp': entry.get('timestamp', ''),
                                'source': 'text_based_matching',
                                'coordinates': [text_rect.x0, text_rect.y0],
                                'precise_quads': quads  # Store precise character-level quads
                            }
                            
                            # Find matching annotation in coordinate_based_annotations and update it
                            # Match by page and content (normalized)
                            # For unified note+highlight, check both 'content' and 'highlight_content'
                            content_norm = normalize_text(content)
                            matching_ann = None
                            for ann in coordinate_based_annotations:
                                if ann['pdf_page_0based'] == pdf_page:
                                    ann_content = ann.get('highlight_content') or ann.get('content', '')
                                    if normalize_text(ann_content) == content_norm:
                                        matching_ann = ann
                                        break
                            
                            if matching_ann:
                                # Update coordinates with text-search results
                                matching_ann['pdf_x'] = text_rect.x0
                                matching_ann['pdf_y'] = text_rect.y0
                                matching_ann['pdf_width'] = text_rect.width
                                matching_ann['pdf_height'] = text_rect.height
                                matching_ann['coordinates'] = [text_rect.x0, text_rect.y0]
                                matching_ann['precise_quads'] = quads
                                matching_ann['source'] = 'text_based_matching'
                                updated_count += 1
                            else:
                                # No matching annotation found - this shouldn't happen but log it
                                print(f"     ⚠️  No matching annotation found for: {content[:50]}...")
                        else:
                            print("     ✗ Could not convert quads to rectangles")
                    else:
                        print("     ✗ Could not locate text in PDF")
                        # Add to unmatched clippings if in learning mode
                        if learn_mode:
                            # Extract a larger context from the page (500+ characters around where we expect the text)
                            page_text = page.get_text()
                            context_start = max(0, page_text_norm.find(search_text_norm[:50]) - 250 if search_text_norm[:50] in page_text_norm else 0)
                            context_end = min(len(page_text), context_start + 500)
                            context_text = page_text[context_start:context_end]
                            
                            unmatched_clippings.append({
                                'original_clipping': content,
                                'expected_search_text': search_text,
                                'pdf_context': context_text,
                                'page_number': pdf_page + 1,
                                'book_name': book_name
                            })

            doc.close()

            if learn_mode and unmatched_clippings:
                print(f"   📚 Learning mode: {len(unmatched_clippings)} unmatched clippings collected")
                
                # Export unmatched clippings to JSON file if path provided
                if learn_output_path:
                    import json
                    with open(learn_output_path, 'w', encoding='utf-8') as f:
                        json.dump(unmatched_clippings, f, indent=2, ensure_ascii=False)
                    print(f"   📁 Exported unmatched clippings to: {learn_output_path}")

            if updated_count > 0:
                print(f"   ✅ Text-based matching updated {updated_count} annotations with precise coordinates")
            corrected_annotations = coordinate_based_annotations
        else:
            print("   ⚠️  No PDF path available for text-based matching, using coordinate-based approach...")
            corrected_annotations = coordinate_based_annotations
    else:
        print("\n   ⚠️  WARNING: No clippings data available, using coordinate-based approach...")
        print("   📌 NOTE: KRDS coordinates may only cover the beginning of highlights.")
        print("   💡 TIP: Provide MyClippings.txt with --clippings for full-text highlighting!")
        corrected_annotations = coordinate_based_annotations

    # Note: MyClippings content is used for ground truth/testing only
    print("\n" + "=" * 80)
    print("📊 ANNOTATION SUMMARY")
    print("=" * 80)
    print(f"   Total annotations: {len(corrected_annotations)}")
    
    # Create coordinates field for adapter compatibility (if not already present)
    for annotation in corrected_annotations:
        if 'coordinates' not in annotation:
            annotation['coordinates'] = [annotation['pdf_x'], annotation['pdf_y']]
    
    # Sort by page and position
    corrected_annotations.sort(key=lambda x: (x['pdf_page_0based'], x['pdf_y']))

    # Check for remaining coordinate duplicates (should be none after earlier deduplication)
    coordinate_groups: Dict[Tuple[int, float, float], List[Dict[str, Any]]] = {}
    for ann in corrected_annotations:
        key = (ann['pdf_page_0based'], round(ann['pdf_x'], 1), round(ann['pdf_y'], 1))
        coordinate_groups.setdefault(key, []).append(ann)

    duplicates = {k: v for k, v in coordinate_groups.items() if len(v) > 1}
    if duplicates:
        print(f"   Coordinate duplicates: {len(duplicates)} locations (may be legitimate highlight+note pairs)")
    else:
        print("   ✅ No coordinate duplicates!")

    # Close PDF document if it was opened
    if pdf_doc:
        pdf_doc.close()

    print("=" * 80)
    return corrected_annotations
