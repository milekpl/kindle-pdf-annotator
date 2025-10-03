#!/usr/bin/env python3
"""
Unit test for highlight width coverage - validates that highlights fully cover the expected text
This test addresses the systematic issue where highlights are too narrow on the right side
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
from src.kindle_parser.fixed_clippings_parser import parse_myclippings_for_book


def test_highlight_width_coverage():
    """Test that all highlights properly cover the expected text content"""
    
    print("🧪 TESTING HIGHLIGHT WIDTH COVERAGE")
    
    # Test files
    krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    pdf_file = 'examples/sample_data/peirce-charles-fixation-belief.pdf'
    output_file = 'tests/highlight_width_test.pdf'
    book_name = 'peirce-charles-fixation-belief'
    
    print(f"   Input PDF: {pdf_file}")
    print(f"   Output PDF: {output_file}")
    
    # Step 1: Parse MyClippings to get expected text content
    print("\n1. Parsing MyClippings for expected text content...")
    myclippings_entries = parse_myclippings_for_book(clippings_file, book_name)
    
    highlights_from_clippings = [entry for entry in myclippings_entries if entry.get('type') == 'highlight']
    print(f"   Found {len(highlights_from_clippings)} highlights in MyClippings")
    
    for i, highlight in enumerate(highlights_from_clippings):
        content = highlight.get('content', '')
        page = highlight.get('pdf_page', 1)
        print(f"   Highlight {i+1} (page {page}): {repr(content[:50])}{'...' if len(content) > 50 else ''}")
    
    # Step 2: Get Amazon annotations and create PDF
    print("\n2. Creating Amazon annotations...")
    amazon_annotations = create_amazon_compliant_annotations(krds_file, clippings_file, book_name)
    
    highlights = [ann for ann in amazon_annotations if ann.get('type') == 'highlight']
    print(f"   Found {len(highlights)} highlights from KRDS")
    
    # Step 3: Convert to PDF annotator format and create annotated PDF
    print("\n3. Converting to PDF annotator format...")
    pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
    
    print("\n4. Creating annotated PDF...")
    result_path = annotate_pdf_file(pdf_file, pdf_annotations, output_file)
    print(f"   Created: {result_path}")
    
    # Step 4: Analyze the actual highlight rectangles in the PDF
    print("\n5. Analyzing highlight rectangles in output PDF...")
    doc = fitz.open(output_file)
    
    total_highlights_checked = 0
    coverage_issues = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        annotations = page.annots()
        
        if annotations:
            print(f"\n   Page {page_num + 1}:")
            for annot in annotations:
                if annot.type[1] == 'Highlight':  # Highlight annotation
                    rect = annot.rect
                    total_highlights_checked += 1
                    
                    # Get text under this highlight rectangle
                    highlighted_text = page.get_textbox(rect).strip()
                    
                    # Find corresponding clipping text for this page
                    expected_texts = [h['content'] for h in highlights_from_clippings 
                                    if h.get('pdf_page', 1) == page_num + 1 and h['content'].strip()]
                    
                    print(f"      Highlight {total_highlights_checked}:")
                    print(f"        Rectangle: {rect}")
                    print(f"        Width: {rect.width:.1f} points")
                    print(f"        Text under highlight: {repr(highlighted_text)}")
                    
                    # Check if the highlighted text matches any expected text
                    full_match_found = False
                    partial_match_found = False
                    
                    for expected_text in expected_texts:
                        if expected_text and highlighted_text:
                            # Normalize for comparison (remove extra whitespace)
                            highlighted_normalized = ' '.join(highlighted_text.split())
                            expected_normalized = ' '.join(expected_text.split())
                            
                            if highlighted_normalized == expected_normalized:
                                full_match_found = True
                                print(f"        ✅ FULL MATCH with expected text")
                                break
                            elif highlighted_normalized in expected_normalized or expected_normalized in highlighted_normalized:
                                partial_match_found = True
                                print(f"        ⚠️  PARTIAL MATCH with expected: {repr(expected_text[:50])}{'...' if len(expected_text) > 50 else ''}")
                                coverage_issues.append({
                                    'page': page_num + 1,
                                    'highlighted': highlighted_text,
                                    'expected': expected_text,
                                    'rect_width': rect.width
                                })
                    
                    if not full_match_found and not partial_match_found and expected_texts:
                        print(f"        ❌ NO MATCH with any expected text")
                        coverage_issues.append({
                            'page': page_num + 1,
                            'highlighted': highlighted_text,
                            'expected': expected_texts[0] if expected_texts else 'Unknown',
                            'rect_width': rect.width
                        })
    
    doc.close()
    
    # Step 5: Report coverage analysis
    print(f"\n📊 HIGHLIGHT COVERAGE ANALYSIS:")
    print(f"   Total highlights checked: {total_highlights_checked}")
    print(f"   Coverage issues found: {len(coverage_issues)}")
    
    if coverage_issues:
        print(f"\n❌ COVERAGE ISSUES DETECTED:")
        for issue in coverage_issues:
            print(f"   Page {issue['page']}: Width {issue['rect_width']:.1f}pt")
            print(f"     Highlighted: {repr(issue['highlighted'])}")
            print(f"     Expected:    {repr(issue['expected'][:100])}{'...' if len(issue['expected']) > 100 else ''}")
            print()
    else:
        print(f"\n✅ All highlights properly cover expected text!")
    
    # Assert that coverage is good (allowing for some minor text extraction differences)
    coverage_ratio = (total_highlights_checked - len(coverage_issues)) / max(1, total_highlights_checked)
    print(f"\n📈 Coverage ratio: {coverage_ratio:.2%}")
    
    if coverage_ratio < 0.8:  # Less than 80% coverage is a problem
        raise AssertionError(f"Highlight coverage is too low: {coverage_ratio:.2%}. Width scaling appears insufficient.")
    
    print(f"✅ Test passed with {coverage_ratio:.2%} coverage")
    return output_file


if __name__ == "__main__":
    test_highlight_width_coverage()