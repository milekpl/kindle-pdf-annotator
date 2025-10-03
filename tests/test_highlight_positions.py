#!/usr/bin/env python3
"""
Test to verify that highlights are placed at the correct positions in the output PDFs.
This test checks that the highlight rectangles match the text locations we found.
"""

import sys
import fitz
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from src.pdf_processor.pdf_annotator import annotate_pdf_file


def test_highlight_positions():
    """
    Test that highlights are placed at correct positions by:
    1. Finding where text should be in source PDF
    2. Creating annotated PDF
    3. Verifying highlights are at the same positions
    """
    
    # Use peirce example
    krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    source_pdf = 'examples/sample_data/peirce-charles-fixation-belief.pdf'
    output_pdf = 'tests/output/position_test.pdf'
    
    print("🎯 HIGHLIGHT POSITION TEST")
    print("=" * 70)
    
    # Step 1: Find where text should be in source PDF
    print("\n1️⃣ Finding expected text positions in source PDF...")
    source_doc = fitz.open(source_pdf)
    
    expected_positions = []
    test_texts = [
        ('The Fixation of Belief', 1),  # Page 1 (0-indexed: 0)
        ('Few persons care to study logic', 1),  # Page 1
        ('The object of reasoning is to', 2),  # Page 2
    ]
    
    for text, page_num in test_texts:
        page = source_doc[page_num - 1]  # Convert to 0-indexed
        quads = page.search_for(text, quads=True)
        
        if quads:
            # Get bounding rectangle
            text_rect = quads[0].rect if hasattr(quads[0], 'rect') else fitz.Rect(quads[0])
            for quad in quads[1:]:
                r = quad.rect if hasattr(quad, 'rect') else fitz.Rect(quad)
                text_rect = text_rect | r  # Union
            
            expected_positions.append({
                'text': text,
                'page': page_num - 1,  # Store as 0-indexed
                'rect': text_rect
            })
            print(f"   ✓ Page {page_num}: '{text[:30]}...' at {text_rect}")
        else:
            print(f"   ✗ Page {page_num}: '{text[:30]}...' NOT FOUND!")
    
    source_doc.close()
    
    # Step 2: Create annotated PDF
    print("\n2️⃣ Creating annotated PDF...")
    amazon_annotations = create_amazon_compliant_annotations(krds_file, clippings_file, 'peirce-charles-fixation-belief')
    pdf_annotator_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
    annotate_pdf_file(source_pdf, pdf_annotator_annotations, output_path=output_pdf)
    print(f"   ✓ Created: {output_pdf}")
    
    # Step 3: Check highlight positions in output PDF
    print("\n3️⃣ Verifying highlight positions in output PDF...")
    output_doc = fitz.open(output_pdf)
    
    all_correct = True
    total_checked = 0
    
    for expected in expected_positions:
        page = output_doc[expected['page']]
        annotations = page.annots()
        
        if not annotations:
            print(f"   ✗ Page {expected['page'] + 1}: NO ANNOTATIONS FOUND!")
            all_correct = False
            continue
        
        # Find highlight that matches this text
        found_match = False
        for annot in annotations:
            if annot.type[0] == 8:  # Highlight annotation
                highlight_rect = annot.rect
                expected_rect = expected['rect']
                
                # Calculate overlap
                overlap_rect = highlight_rect & expected_rect
                if not overlap_rect.is_empty:
                    overlap_area = overlap_rect.get_area()
                    expected_area = expected_rect.get_area()
                    overlap_ratio = overlap_area / expected_area if expected_area > 0 else 0
                    
                    # Check if highlight is within page bounds
                    page_rect = page.rect
                    is_within_page = (
                        highlight_rect.x0 >= page_rect.x0 and
                        highlight_rect.x1 <= page_rect.x1 and
                        highlight_rect.y0 >= page_rect.y0 and
                        highlight_rect.y1 <= page_rect.y1
                    )
                    
                    if overlap_ratio >= 0.8:
                        found_match = True
                        total_checked += 1
                        
                        if is_within_page:
                            print(f"   ✓ Page {expected['page'] + 1}: '{expected['text'][:30]}...'")
                            print(f"      Expected: {expected_rect}")
                            print(f"      Actual:   {highlight_rect}")
                            print(f"      Overlap:  {overlap_ratio:.1%}")
                        else:
                            print(f"   ⚠️  Page {expected['page'] + 1}: '{expected['text'][:30]}...' - OUTSIDE PAGE BOUNDS!")
                            print(f"      Page bounds: {page_rect}")
                            print(f"      Expected:    {expected_rect}")
                            print(f"      Actual:      {highlight_rect}")
                            print(f"      Overlap:     {overlap_ratio:.1%}")
                            all_correct = False
                        break
        
        if not found_match:
            print(f"   ✗ Page {expected['page'] + 1}: '{expected['text'][:30]}...' - NO MATCHING HIGHLIGHT!")
            print(f"      Expected at: {expected['rect']}")
            print(f"      Available highlights on page:")
            for annot in annotations:
                if annot.type[0] == 8:
                    print(f"         - {annot.rect}")
            all_correct = False
    
    output_doc.close()
    
    # Summary
    print("\n" + "=" * 70)
    if all_correct and total_checked > 0:
        print(f"✅ SUCCESS: All {total_checked} highlights are correctly positioned!")
        return True
    else:
        print(f"❌ FAILURE: Highlights are NOT at expected positions!")
        print("\n🔍 DEBUGGING INFO:")
        print("   The highlights were created but may be placed incorrectly.")
        print("   Possible issues:")
        print("   - Coordinate system mismatch between annotation creation and PDF rendering")
        print("   - PDF coordinate origin (top-left vs bottom-left)")
        print("   - Incorrect rectangle calculation in pdf_annotator.py")
        return False


if __name__ == '__main__':
    success = test_highlight_positions()
    sys.exit(0 if success else 1)
