"""
Amazon to PDF Annotator Adapter
Converts Amazon coordinate system annotations to the format expected by pdf_annotator.py
"""

from typing import List, Dict, Any, Optional
import fitz

from kindle_parser.amazon_coordinate_system import convert_kindle_to_pdf_coordinates


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
        
        # Skip empty annotations, but NOT for highlights (they don't need content)
        if not content and ann_type != 'highlight':
            continue
            
        # Create proper coordinates based on annotation type
        if ann_type == 'highlight':
            # Build a PDF rectangle using Kindle geometry for the full span
            kindle_x = float(ann.get('kindle_x', 0.0))
            kindle_y = float(ann.get('kindle_y', 0.0))
            kindle_width = float(ann.get('kindle_width', 0.0))
            kindle_height = float(ann.get('kindle_height', 0.0))

            pdf_rect_width = float(ann.get('pdf_rect_width', 595.3))
            pdf_rect_height = float(ann.get('pdf_rect_height', 841.9))
            pdf_rect = fitz.Rect(0, 0, pdf_rect_width, pdf_rect_height)

            # Initial right/bottom edges based on start segment
            right_candidates: List[float] = []
            bottom_candidates: List[float] = []
            top_candidates = [pdf_y]

            # Track individual segment rectangles for downstream multi-line handling
            segment_rects: List[fitz.Rect] = []

            # Base rectangle derived from the start position
            right_from_width, _ = convert_kindle_to_pdf_coordinates(kindle_x + kindle_width, kindle_y, pdf_rect)
            _, bottom_from_height = convert_kindle_to_pdf_coordinates(kindle_x, kindle_y + kindle_height, pdf_rect)
            start_rect = fitz.Rect(pdf_x, pdf_y, right_from_width, bottom_from_height)

            segment_rects.append(start_rect)

            right_candidates.append(right_from_width)
            bottom_candidates.append(bottom_from_height)
            start_line_height = max(0.1, start_rect.height)
            end_line_height: Optional[float] = None

            # Use start/end position strings for multi-word / multi-line spans
            start_pos = ann.get('start_position')
            end_pos = ann.get('end_position')

            if start_pos and end_pos and start_pos != end_pos:
                start_parts = start_pos.split()
                end_parts = end_pos.split()

                if len(start_parts) >= 8 and len(end_parts) >= 8:
                    end_x = float(end_parts[4])
                    end_y = float(end_parts[5])
                    end_width = float(end_parts[6])
                    end_height = float(end_parts[7])

                    end_left_pdf, end_top_pdf = convert_kindle_to_pdf_coordinates(end_x, end_y, pdf_rect)
                    top_candidates.append(end_top_pdf)

                    end_right_pdf, _ = convert_kindle_to_pdf_coordinates(end_x + end_width, end_y, pdf_rect)
                    right_candidates.append(end_right_pdf)

                    _, end_bottom_pdf = convert_kindle_to_pdf_coordinates(end_x, end_y + end_height, pdf_rect)
                    bottom_candidates.append(end_bottom_pdf)

                    end_rect = fitz.Rect(end_left_pdf, end_top_pdf, end_right_pdf, end_bottom_pdf)
                    end_line_height = max(0.1, end_rect.height)

                    # Avoid duplicating identical segments (single line highlight)
                    if any(abs(getattr(end_rect, attr) - getattr(start_rect, attr)) > 0.1
                           for attr in ("x0", "y0", "x1", "y1")):
                        segment_rects.append(end_rect)

                    # Estimate intermediate segments if vertical span indicates multi-line highlight
                    vertical_span = end_rect.y0 - start_rect.y0
                    if start_line_height > 0 and vertical_span > (start_line_height * 1.5):
                        avg_line_height = (start_line_height + (end_line_height or start_line_height)) / 2
                        num_total_lines_estimate = max(2, int(round(vertical_span / max(1.0, avg_line_height))) + 1)
                        num_additional_lines = max(0, num_total_lines_estimate - 2)
                        if num_additional_lines > 0:
                            # Determine interior rectangle width: use union of start / end widths
                            interior_left = min(start_rect.x0, end_rect.x0)
                            interior_right = max(start_rect.x1, end_rect.x1)
                            line_gap = vertical_span / (num_additional_lines + 1)
                            line_height = avg_line_height
                            for line_idx in range(num_additional_lines):
                                top_offset = start_rect.y0 + line_gap * (line_idx + 1)
                                intermediate_rect = fitz.Rect(
                                    interior_left,
                                    top_offset,
                                    interior_right,
                                    top_offset + line_height
                                )
                                segment_rects.append(intermediate_rect)

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