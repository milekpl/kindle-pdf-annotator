"""
Amazon to PDF Annotator Adapter
Converts Amazon coordinate system annotations to the format expected by pdf_annotator.py
"""

from typing import List, Dict, Any, Optional
import fitz

from kindle_parser.amazon_coordinate_system import convert_kindle_to_pdf_coordinates, convert_kindle_width_to_pdf, convert_kindle_height_to_pdf


def convert_amazon_to_pdf_annotator_format(amazon_annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert Amazon coordinate system annotations to pdf_annotator expected format
    
    Args:
        amazon_annotations: List of annotations from amazon_coordinate_system.py
        
    Returns:
        List of annotations in pdf_annotator.py expected format
    """
    converted_annotations = []
    
    for ann in amazon_annotations:
        content = ann.get('content', '').strip()
        ann_type = ann.get('type', 'highlight')
        pdf_x = ann.get('pdf_x', 0)
        pdf_y = ann.get('pdf_y', 0)
        page_number = ann.get('pdf_page_0based', 0)
        
        # DEBUG: Check if this is the title
        if ann.get('kindle_width') == 46:
            print(f"🔍 DEBUG Processing title in adapter:")
            print(f"   content: '{content}'")
            print(f"   ann_type: {ann_type}")
            print(f"   Empty content check: not content = {not content}")
            print(f"   Skip condition: {not content and ann_type not in ['highlight', 'bookmark']}")
        
        # Skip empty annotations, but NOT for highlights or bookmarks (they don't need content)
        if not content and ann_type not in ['highlight', 'bookmark']:
            if ann.get('kindle_width') == 46:
                print(f"   >>> TITLE SKIPPED HERE!")
            continue
            
        # Create proper coordinates based on annotation type
        if ann_type == 'highlight':
            # Use the already-converted PDF coordinates from amazon_coordinate_system
            # DO NOT re-convert Kindle coordinates to avoid double-scaling!
            
            # Set up PDF rect for multi-line highlight processing
            pdf_rect_width = float(ann.get('pdf_rect_width', 595.3))
            pdf_rect_height = float(ann.get('pdf_rect_height', 841.9))
            pdf_rect = fitz.Rect(0, 0, pdf_rect_width, pdf_rect_height)
            
            # Get pre-converted PDF coordinates and dimensions
            pdf_width = ann.get('pdf_width', 0.0)
            pdf_height = ann.get('pdf_height', 0.0)
            
            # Fall back to manual conversion only if PDF dimensions not available
            if abs(pdf_width) < 0.01 or abs(pdf_height) < 0.01:
                kindle_width = float(ann.get('kindle_width', 0.0))
                kindle_height = float(ann.get('kindle_height', 0.0))
                
                pdf_width = convert_kindle_width_to_pdf(kindle_width, pdf_rect)
                pdf_height = convert_kindle_height_to_pdf(kindle_height)

            # Initial right/bottom edges based on start segment
            right_candidates: List[float] = []
            bottom_candidates: List[float] = []
            top_candidates = [pdf_y]

            # Track individual segment rectangles for downstream multi-line handling
            segment_rects: List[fitz.Rect] = []

            # Base rectangle using pre-converted coordinates
            start_rect = fitz.Rect(pdf_x, pdf_y, pdf_x + pdf_width, pdf_y + pdf_height)

            # DON'T add start_rect to segment_rects yet - wait to see if it's single-line or multi-line

            right_candidates.append(pdf_x + pdf_width)
            bottom_candidates.append(pdf_y + pdf_height)
            start_line_height = max(0.1, start_rect.height)
            end_line_height: Optional[float] = None

            # DEBUG: Check what values we're getting for first highlight
            if ann.get('type') == 'highlight' and ann.get('kindle_width') == 46:  # Title highlight
                print(f"🔍 DEBUG Title annotation in adapter:")
                print(f"   pdf_width from ann: {pdf_width} (type: {type(pdf_width)})")
                print(f"   pdf_height from ann: {pdf_height} (type: {type(pdf_height)})")
                print(f"   start_rect: {start_rect}")
                print(f"   segment_rects count: {len(segment_rects)}")
                for i, rect in enumerate(segment_rects):
                    print(f"   segment_rects[{i}]: {rect}")


            # Use start/end position strings for multi-word / multi-line spans
            # CRITICAL: Only use pre-converted coordinates for single-line highlights
            # Multi-line highlights need segment rectangles to be computed
            start_pos = ann.get('start_position')
            end_pos = ann.get('end_position')
            is_single_line = True  # Assume single line initially
            
            if start_pos and end_pos and start_pos != end_pos:
                start_parts = start_pos.split()
                end_parts = end_pos.split()

                if len(start_parts) >= 8 and len(end_parts) >= 8:
                    start_y_kindle = float(start_parts[5])
                    end_y_kindle = float(end_parts[5])
                    
                    # Check if this is actually a single-line highlight
                    # If Y coordinates are the same, it's single-line - don't process end
                    if abs(end_y_kindle - start_y_kindle) <= 10:  # Same line (within 10 Kindle units)
                        is_single_line = True
                        # DON'T continue here - we still need to create the annotation!
                    else:
                        # Multi-line highlight - process end position
                        is_single_line = False
                        
                        # Add start_rect for multi-line highlights
                        segment_rects.append(start_rect)
                            
                        end_x = float(end_parts[4])
                        end_y = float(end_parts[5])
                        end_width = float(end_parts[6])
                        end_height = float(end_parts[7])

                        # Need to convert from Kindle coordinates
                        end_left_pdf, end_top_pdf = convert_kindle_to_pdf_coordinates(end_x, end_y, pdf_rect)
                        top_candidates.append(end_top_pdf)

                        end_pdf_width = convert_kindle_width_to_pdf(end_width, pdf_rect)
                        end_pdf_height = convert_kindle_height_to_pdf(end_height)
                        
                        end_right_pdf = end_left_pdf + end_pdf_width
                        end_bottom_pdf = end_top_pdf + end_pdf_height
                        
                        right_candidates.append(end_right_pdf)
                        bottom_candidates.append(end_bottom_pdf)

                        end_rect = fitz.Rect(end_left_pdf, end_top_pdf, end_right_pdf, end_bottom_pdf)

                        # Always add end_rect for multi-line highlights
                        segment_rects.append(end_rect)

                        # For multi-line highlights, DON'T compute intermediate segments
                        # The PDF annotator will handle multi-line properly using start + end rects
                        # Computing intermediates causes issues with two-column layouts

            # DEBUG: Check multi-line highlight (#2 - "Few persons")
            if ann.get('type') == 'highlight' and 'Few persons' in ann.get('content', ''):
                print(f"\n🔍 DEBUG Multi-line annotation in adapter:")
                print(f"   content: '{ann.get('content', '')[:50]}...'")
                print(f"   pdf_width from ann: {pdf_width}")
                print(f"   pdf_height from ann: {pdf_height}")
                print(f"   start_rect: {start_rect}")
                print(f"   is_single_line: {is_single_line}")
                print(f"   segment_rects count: {len(segment_rects)}")
                for i, rect in enumerate(segment_rects):
                    print(f"   segment_rects[{i}]: {rect}")

            # Ensure segments are ordered from top to bottom for consistency
            segment_rects.sort(key=lambda r: r.y0)

            pdf_right = max(right_candidates) if right_candidates else pdf_x + 2
            pdf_bottom = max(bottom_candidates) if bottom_candidates else pdf_y + 14
            pdf_top = min(top_candidates) if top_candidates else pdf_y

            # Ensure minimum highlight size
            if pdf_right <= pdf_x:
                pdf_right = pdf_x + 5
            if pdf_bottom <= pdf_top:
                pdf_bottom = pdf_top + 12

            coordinates = [
                pdf_x,
                pdf_top,
                pdf_right,
                pdf_bottom
            ]
        elif ann_type == 'note':
            # For notes, create a small rectangle at the point
            coordinates = [
                pdf_x,           # x0 - left
                pdf_y,           # y0 - top
                pdf_x + 20,      # x1 - right (small note icon)
                pdf_y + 20       # y1 - bottom (small note icon)
            ]
        elif ann_type == 'bookmark':
            # For bookmarks, create a small rectangle at the point (similar to notes)
            coordinates = [
                pdf_x,           # x0 - left
                pdf_y,           # y0 - top
                pdf_x + 18,      # x1 - right (bookmark icon)
                pdf_y + 18       # y1 - bottom (bookmark icon)
            ]
        else:
            # Default rectangle
            coordinates = [pdf_x, pdf_y, pdf_x + 100, pdf_y + 20]
        
        # Convert to pdf_annotator format
        converted_ann = {
            # Required fields for pdf_annotator
            'page_number': page_number,
            'content': content,
            'type': ann_type,
            'coordinates': coordinates,
            
            # Additional metadata
            'source': ann.get('source', 'amazon_converted'),
            'timestamp': ann.get('timestamp', ''),
            'start_position': ann.get('start_position'),
            'end_position': ann.get('end_position'),
            
            # Pre-computed segment rectangles (for highlights only)
            # For single-line highlights, DON'T pass segment_rects - let PDF annotator use pre-converted coords
            # For multi-line highlights, pass segment_rects for proper multi-line handling
            'segment_rects': segment_rects if (ann_type == 'highlight' and not is_single_line) else None,
            
            # Pre-converted PDF dimensions (pass through from amazon_coordinate_system)
            'pdf_x': ann.get('pdf_x', 0),
            'pdf_y': ann.get('pdf_y', 0),
            'pdf_width': ann.get('pdf_width', 0.0),
            'pdf_height': ann.get('pdf_height', 0.0),
            
            # Improved coordinate system metadata (for debugging)
            'kindle_coordinates': {
                'kindle_x': ann.get('kindle_x', 0),
                'kindle_y': ann.get('kindle_y', 0),
                'kindle_x_inches': ann.get('kindle_x_inches', 0.0),
                'kindle_y_inches': ann.get('kindle_y_inches', 0.0),
                'pdf_x': pdf_x,
                'pdf_y': pdf_y
            }
        }
        
        converted_annotations.append(converted_ann)
    
    # DEBUG: Check if title annotation is in the final list
    print(f"\n✅ ADAPTER CONVERSION COMPLETE:")
    print(f"   Total annotations returned: {len(converted_annotations)}")
    
    title_found = False
    for ann in converted_annotations:
        if ann.get('pdf_width') == 184.2:
            title_found = True
            print(f"   ✅ Title annotation found in final list!")
            break
    if not title_found:
        print(f"   ❌ Title annotation NOT found in final list!")
    
    return converted_annotations


def test_amazon_to_pdf_conversion():
    """Test the conversion from Amazon to PDF annotator format"""
    
    # Create test Amazon annotation
    amazon_ann = {
        'type': 'note',
        'pdf_page_0based': 8,
        'kindle_x': 248.0,
        'kindle_y': 591.0,
        'kindle_width': 47.0,
        'kindle_height': 14.0,
        'pdf_x': 194.8,
        'pdf_y': 356.0,
        'content': 'Whom',
        'source': 'json_note_amazon_converted',
        'timestamp': '2025-09-02T08:03:25.232000'
    }
    
    converted = convert_amazon_to_pdf_annotator_format([amazon_ann])
    
    print("🔄 AMAZON TO PDF ANNOTATOR CONVERSION TEST")
    print(f"   Original Amazon format:")
    print(f"      Page: {amazon_ann['pdf_page_0based']}")
    print(f"      PDF coordinates: ({amazon_ann['pdf_x']}, {amazon_ann['pdf_y']})")
    print(f"      Content: '{amazon_ann['content']}'")
    print(f"      Type: {amazon_ann['type']}")
    
    print(f"   Converted PDF annotator format:")
    conv_ann = converted[0]
    print(f"      page_number: {conv_ann['page_number']}")
    print(f"      coordinates: {conv_ann['coordinates']}")
    print(f"      content: '{conv_ann['content']}'")
    print(f"      type: {conv_ann['type']}")
    
    # Verify rectangle is valid
    rect = fitz.Rect(conv_ann['coordinates'])
    print(f"   Rectangle validation:")
    print(f"      Rect: {rect}")
    print(f"      Valid: {rect.is_valid}")
    print(f"      Area: {rect.get_area():.1f}")
    
    return converted


if __name__ == "__main__":
    test_amazon_to_pdf_conversion()