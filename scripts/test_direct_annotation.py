#!/usr/bin/env python3
"""
Test PDF annotation creation and measurement directly
"""

import fitz
import sys
sys.path.append('src')

from kindle_parser.amazon_coordinate_system import convert_kindle_to_pdf_coordinates, convert_kindle_width_to_pdf

def test_direct_annotation():
    print("🧪 TESTING DIRECT PDF ANNOTATION")
    
    # Open the original PDF
    doc = fitz.open('examples/sample_data/peirce-charles-fixation-belief.pdf')
    page = doc.load_page(0)
    
    # Title coordinates
    kindle_x = 284
    kindle_y = 231
    kindle_width = 46
    kindle_height = 21
    
    # Convert coordinates
    pdf_rect = page.rect
    pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(kindle_x, kindle_y, pdf_rect)
    pdf_width = convert_kindle_width_to_pdf(kindle_width, pdf_rect)
    
    print(f"📐 Coordinate conversion:")
    print(f"   Kindle: x={kindle_x}, w={kindle_width}")
    print(f"   PDF: x={pdf_x:.1f}, w={pdf_width:.1f}")
    
    # Create the highlight rectangle
    highlight_rect = fitz.Rect(pdf_x, pdf_y, pdf_x + pdf_width, pdf_y + kindle_height)
    
    print(f"   Highlight rect: {highlight_rect}")
    print(f"   Calculated width: {highlight_rect.width:.1f}pt")
    
    # Add the annotation to the page
    annot = page.add_highlight_annot(highlight_rect)
    annot.set_info(content="The Fixation of Belief")
    annot.update()
    
    # Save to test file
    doc.save('test_direct_annotation.pdf')
    doc.close()
    
    # Re-open and check the annotation
    print(f"\n🔍 Reading annotation back from PDF:")
    doc = fitz.open('test_direct_annotation.pdf')
    page = doc.load_page(0)
    
    annotations = page.annots()
    if annotations:
        for annot in annotations:
            if annot.type[1] == 'Highlight':
                rect = annot.rect
                highlighted_text = page.get_textbox(rect).strip()
                
                print(f"   Found highlight: '{highlighted_text}'")
                print(f"   Annotation rect: {rect}")
                print(f"   Measured width: {rect.width:.1f}pt")
                print(f"   Expected width: 184.2pt")
                print(f"   Width ratio: {rect.width / 184.2:.3f}")
                
                break
    
    doc.close()

if __name__ == "__main__":
    test_direct_annotation()