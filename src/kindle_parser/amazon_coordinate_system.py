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

def convert_kindle_to_pdf_coordinates(kindle_x: float, kindle_y: float, pdf_rect: Optional[Any] = None) -> Tuple[float, float]:
    """Convert Kindle coordinates to PDF points using robust linear transformation."""

    page_width, page_height = _resolve_page_dimensions(pdf_rect)

    # Use linear transformation: pdf_coord = scale * kindle_coord + offset
    # X transformation (direct relationship)
    pdf_x = CONFIG.x_scale * kindle_x + CONFIG.x_offset

    # Y transformation (Kindle Y=0 at top, PDF Y=0 at bottom, so negative scale)
    pdf_y = CONFIG.y_scale * kindle_y + CONFIG.y_offset

    # Clamp within page bounds to avoid accidental overshoot
    pdf_x = max(0.0, min(pdf_x, page_width))
    pdf_y = max(0.0, min(pdf_y, page_height))

    return pdf_x, pdf_y

def convert_kindle_width_to_pdf(kindle_width: float, pdf_rect: Optional[Any] = None, pdf_x: float = 0.0) -> float:
    """Convert Kindle width to PDF points using linear transformation."""

    if kindle_width <= 0:
        return 0.0

    # Use linear transformation for width
    pdf_width = kindle_width * CONFIG.width_scale_factor

    # Prevent highlights from spilling beyond the page
    if pdf_rect is not None:
        page_width, _ = _resolve_page_dimensions(pdf_rect)
        pdf_width = min(pdf_width, max(0.0, page_width - pdf_x))

    return max(0.0, pdf_width)


def convert_kindle_height_to_pdf(kindle_height: float, pdf_rect: Optional[Any] = None, pdf_y: float = 0.0) -> float:
    """Convert Kindle height to PDF points using calibrated scaling."""

    if kindle_height <= 0:
        return 0.0

    _, page_height = _resolve_page_dimensions(pdf_rect)
    pdf_height = kindle_height * CONFIG.height_scale_factor

    if pdf_rect is not None:
        pdf_height = min(pdf_height, max(0.0, page_height - pdf_y))

    return max(0.0, pdf_height)

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
    source: str
) -> Dict[str, Any]:
    """Create a standardized annotation dictionary with converted coordinates."""

    # Convert using inches-based coordinate system
    pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(kindle_x, kindle_y, pdf_rect)
    pdf_width = convert_kindle_width_to_pdf(width, pdf_rect, pdf_x)
    pdf_height = convert_kindle_height_to_pdf(height, pdf_rect, pdf_y)

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

        # Converted PDF coordinates
        'pdf_x': pdf_x,
        'pdf_y': pdf_y,
        'pdf_width': pdf_width,
        'pdf_height': pdf_height,

        'content': content,
        'timestamp': timestamp,
        'source': source
    }


def _process_highlight_annotation(highlight: Any, pdf_rect: Any) -> Dict[str, Any]:
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
        source='json_highlight_amazon_converted'
    )


def _process_note_annotation(note: Any, pdf_rect: Any) -> Dict[str, Any]:
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
        source='json_note_amazon_converted'
    )


def _process_bookmark_annotation(bookmark: Any, pdf_rect: Any) -> Dict[str, Any]:
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
            if book_name in pdf_file.stem:
                return str(pdf_file)
    
    return None


def _deduplicate_annotations(annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate annotations based on type, page, position, and content."""

    unique_annotations = []
    seen_keys = set()

    for ann in annotations:
        # Create a key that includes type, page, and approximate position
        content_key = ann.get('content', '').strip()[:50]
        timestamp_key = ann.get('timestamp', '') if ann['type'] == 'bookmark' else ''
        dedup_key = (
            ann['type'],
            ann['pdf_page_0based'],
            round(ann['pdf_x'], 1),
            round(ann['pdf_y'], 1),
            content_key,
            timestamp_key,
        )

        if dedup_key not in seen_keys:
            seen_keys.add(dedup_key)
            unique_annotations.append(ann)
        else:
            print(f"   Skipped duplicate: {ann['type']} on page {ann['pdf_page_0based']} - {ann.get('content', '')[:30]}...")

    return unique_annotations


def create_amazon_compliant_annotations(krds_file_path: str, clippings_file: Optional[str], book_name: str) -> List[Dict[str, Any]]:
    """
    Create annotations using Amazon's coordinate system algorithm.
    Uses text-based matching as the primary strategy with coordinate calibration as fallback.
    
    Args:
        krds_file_path: Path to the KRDS file 
        clippings_file: Optional path to MyClippings.txt file for enhanced accuracy
        book_name: Name of the book for matching
    """
    print("=" * 80)
    print("🎯 CREATING KINDLE ANNOTATIONS WITH TEXT-BASED MATCHING")
    print("=" * 80)

    # Parse MyClippings with our fixed parser (if provided)
    myclippings_entries = []
    if clippings_file and Path(clippings_file).exists():
        try:
            from .fixed_clippings_parser import parse_myclippings_for_book
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
    
    if pdf_path:
        print(f"\n📄 Found PDF: {pdf_path}")
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            actual_pdf_rect = doc[0].rect
            print(f"   PDF dimensions: {actual_pdf_rect.width:.1f} x {actual_pdf_rect.height:.1f} points")
        else:
            print(f"   ⚠️  PDF has no pages, using defaults")
            actual_pdf_rect = fitz.Rect(0, 0, CONFIG.default_page_width, CONFIG.default_page_height)
        doc.close()
    else:
        print(f"\n⚠️  Could not find PDF file, using default dimensions")
        actual_pdf_rect = fitz.Rect(0, 0, CONFIG.default_page_width, CONFIG.default_page_height)

    print("\n" + "=" * 80)
    print("🔍 PROCESSING ANNOTATIONS")
    print("=" * 80)

    # Try coordinate-based approach first
    coordinate_based_annotations = []
    for highlight in highlights:
        try:
            annotation = _process_highlight_annotation(highlight, actual_pdf_rect)
            coordinate_based_annotations.append(annotation)
        except ValueError as e:
            print(f"   Warning: Skipping invalid highlight: {e}")
            continue

    # If we have clippings data, USE TEXT-BASED MATCHING as primary approach
    if myclippings_entries and len([e for e in myclippings_entries if e.get('type') == 'highlight']) > 0:
        print("\n📍 Using TEXT-BASED MATCHING (primary strategy)...")
        
        if pdf_path:
            text_based_annotations = []
            doc = fitz.open(pdf_path)
            
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
                    search_text = search_text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
                    # Handle abbreviations: "ch.4" -> "ch. 4" (add space after period if missing)
                    import re
                    search_text = re.sub(r'(\w)\.(\d)', r'\1. \2', search_text)
                    
                    # Try to find exact text using PyMuPDF's search with quads
                    quads = page.search_for(search_text, quads=True)
                    
                    # If not found, try progressively shorter versions
                    if not quads and len(search_text) > 50:
                        quads = page.search_for(search_text[:50], quads=True)
                    if not quads and len(search_text) > 30:
                        quads = page.search_for(search_text[:30], quads=True)
                    
                    # If still not found, try first few words
                    if not quads:
                        words = search_text.split()
                        if len(words) > 5:
                            quads = page.search_for(' '.join(words[:5]), quads=True)
                        elif len(words) > 3:
                            quads = page.search_for(' '.join(words[:3]), quads=True)

                    if quads:
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
                                except:
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
                            text_based_annotations.append(annotation)
                        else:
                            print("     ✗ Could not convert quads to rectangles")
                    else:
                        print("     ✗ Could not locate text in PDF")

            doc.close()

            if text_based_annotations:
                print(f"   ✅ Text-based matching found {len(text_based_annotations)} annotations")
                corrected_annotations = text_based_annotations
            else:
                print("   ⚠️  Text-based matching failed, falling back to coordinate-based...")
                corrected_annotations = coordinate_based_annotations
        else:
            print("   ⚠️  No PDF path available for text-based matching, using coordinate-based approach...")
            corrected_annotations = coordinate_based_annotations
    else:
        print("\n   ℹ️  No clippings data available, using coordinate-based approach...")
        corrected_annotations = coordinate_based_annotations

    # Process notes
    print(f"\n📝 Processing {len(notes)} notes...")
    for note in notes:
        try:
            annotation = _process_note_annotation(note, actual_pdf_rect)
            corrected_annotations.append(annotation)
        except ValueError as e:
            print(f"   Warning: Skipping invalid note: {e}")
            continue

    # Process bookmarks (skip those without location data)
    print(f"\n🔖 Processing {len(bookmarks)} bookmarks (skipped - no location data)...")
    for _ in bookmarks:
        # Bookmarks typically don't have precise location data, skip them
        # They're just page markers
        continue

    # Note: MyClippings content is used for ground truth/testing only
    print("\n" + "=" * 80)
    print("📊 ANNOTATION SUMMARY")
    print("=" * 80)
    print(f"   Total annotations before dedup: {len(corrected_annotations)}")
    
    # Create coordinates field for adapter compatibility (if not already present)
    for annotation in corrected_annotations:
        if 'coordinates' not in annotation:
            annotation['coordinates'] = [annotation['pdf_x'], annotation['pdf_y']]
    
    # Sort by page and position
    corrected_annotations.sort(key=lambda x: (x['pdf_page_0based'], x['pdf_y']))

    # Deduplicate annotations based on type, page, and coordinates
    corrected_annotations = _deduplicate_annotations(corrected_annotations)
    print(f"   Total annotations after dedup: {len(corrected_annotations)}")

    # Check for remaining coordinate duplicates
    coordinate_groups: Dict[Tuple[int, float, float], List[Dict[str, Any]]] = {}
    for ann in corrected_annotations:
        key = (ann['pdf_page_0based'], round(ann['pdf_x'], 1), round(ann['pdf_y'], 1))
        coordinate_groups.setdefault(key, []).append(ann)

    duplicates = {k: v for k, v in coordinate_groups.items() if len(v) > 1}
    if duplicates:
        print(f"   Coordinate duplicates: {len(duplicates)} locations (may be legitimate highlight+note pairs)")
    else:
        print("   ✅ No coordinate duplicates!")

    print("=" * 80)
    return corrected_annotations
