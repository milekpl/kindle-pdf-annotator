"""
Amazon to PDF Annotator Adapter
Converts Amazon coordinate system annotations to the format expected by pdf_annotator.py
"""

from typing import List, Dict, Any
import fitz


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
            # For highlights, calculate actual dimensions from Kindle data
            kindle_width = ann.get('kindle_width', 100)  # Width in Kindle units
            kindle_height = ann.get('kindle_height', 14)  # Height in Kindle units
            
            # Convert Kindle dimensions to PDF points using the same scale factor as coordinates
            # X scale factor from coordinate system: 0.717895
            # Y scale factor from coordinate system: 0.009971 (but we use actual height conversion)
            pdf_width = kindle_width * 0.717895  # Convert width using X scale
            pdf_height = kindle_height * 0.717895  # Use same scale for height consistency
            
            # For highlights with startPosition and endPosition, calculate span
            start_pos = ann.get('start_position', '')
            end_pos = ann.get('end_position', '')
            
            if start_pos and end_pos and start_pos != end_pos:
                # Multi-position highlight - calculate from start to end
                start_parts = start_pos.split()
                end_parts = end_pos.split()
                
                if len(start_parts) >= 8 and len(end_parts) >= 8:
                    start_x = float(start_parts[4])
                    end_x = float(end_parts[4])
                    end_width = float(end_parts[6])
                    
                    # Calculate actual highlight span
                    total_kindle_width = end_x + end_width - start_x
                    pdf_width = total_kindle_width * 0.717895
            
            coordinates = [
                pdf_x,                        # x0 - left
                pdf_y,                        # y0 - top  
                pdf_x + pdf_width,            # x1 - right (actual width)
                pdf_y + pdf_height            # y1 - bottom (actual height)
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