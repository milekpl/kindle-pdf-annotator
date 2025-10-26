#!/usr/bin/env python3
"""
Unit test for highlight width coverage - validates that highlights fully cover the expected text
This test uses text search and overlap validation (same as test_peirce_text_coverage.py)
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
from src.kindle_parser.clippings_parser import parse_myclippings_for_book


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""
    import re
    normalized = ' '.join(text.split())
    normalized = normalized.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    normalized = re.sub(r'(\w)\.(\d)', r'\1. \2', normalized)
    return normalized


def test_highlight_width_coverage():
    """Test that all highlights properly cover the expected text content using text search validation"""
    
    print("🧪 TESTING HIGHLIGHT WIDTH COVERAGE (Text Search Method)")
    print("="*70)
    
    # Test files
    krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    pdf_file = 'examples/sample_data/peirce-charles-fixation-belief.pdf'
    output_file = 'tests/output/highlight_width_test.pdf'
    book_name = 'peirce-charles-fixation-belief'
    
    # Step 1: Parse MyClippings to get expected text content
    print("\n1. Parsing MyClippings for expected text content...")
    myclippings_entries = parse_myclippings_for_book(clippings_file, book_name)
    
    expected_highlights = []
    for entry in myclippings_entries:
        if entry.get('type') == 'highlight' and entry.get('content', '').strip():
            expected_highlights.append({
                'page': entry.get('pdf_page', 1) - 1,  # 0-indexed
                'content': entry.get('content', ''),
                'normalized_content': normalize_text(entry.get('content', ''))
            })
    
    print(f"   Found {len(expected_highlights)} highlights with text content")
    
    # Step 2: Create annotated PDF
    print("\n2. Creating annotated PDF...")
    amazon_annotations = create_amazon_compliant_annotations(krds_file, clippings_file, book_name)
    pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
    annotate_pdf_file(pdf_file, pdf_annotations, output_path=output_file)
    print(f"   Created: {output_file}")
    
    # Step 3: Validate highlights using text search
    print("\n3. Validating highlight positions using text search...")
    
    # Open BOTH PDFs - source for text search, output for highlight rectangles
    pdf_source = fitz.open(pdf_file)
    pdf_output = fitz.open(output_file)
    
    # Get actual highlight rectangles from output PDF
    actual_highlights = []
    for page_num in range(len(pdf_output)):
        page = pdf_output[page_num]
        annots = page.annots()
        if annots:
            for annot in annots:
                if annot.type[0] == 8:  # Highlight
                    actual_highlights.append({
                        'page': page_num,
                        'rect': annot.rect
                    })
    
    print(f"   Found {len(actual_highlights)} highlights in PDF")
    
    # Match expected highlights to actual highlights
    matches = []
    unmatched_expected = list(expected_highlights)
    unmatched_actual = list(actual_highlights)
    
    for expected in expected_highlights:
        page_num_0based = expected['page']
        if page_num_0based >= len(pdf_source):
            continue
            
        page = pdf_source[page_num_0based]
        
        # Search for the expected text on the page
        search_text = expected['normalized_content']
        text_quads = page.search_for(search_text, quads=True)
        
        # Try shorter versions if not found
        if not text_quads and len(search_text) > 50:
            text_quads = page.search_for(search_text[:50], quads=True)
        if not text_quads and len(search_text) > 30:
            text_quads = page.search_for(search_text[:30], quads=True)
        if not text_quads:
            words = search_text.split()
            if len(words) > 5:
                text_quads = page.search_for(' '.join(words[:5]), quads=True)
        
        if text_quads:
            # Get bounding rectangle of found text
            text_rects = []
            for quad in text_quads:
                if hasattr(quad, 'rect'):
                    text_rects.append(quad.rect)
            
            if not text_rects:
                continue
                
            text_rect = text_rects[0]
            for r in text_rects[1:]:
                text_rect = text_rect | r  # Union
            
            # Find highlight that overlaps with this text location
            best_match = None
            best_overlap = 0
            
            for actual in actual_highlights:
                if actual['page'] == page_num_0based:
                    # Calculate overlap
                    overlap_rect = actual['rect'] & text_rect
                    if not overlap_rect.is_empty:
                        overlap_area = overlap_rect.get_area()
                        text_area = text_rect.get_area()
                        overlap_ratio = overlap_area / text_area if text_area > 0 else 0
                        
                        if overlap_ratio > best_overlap:
                            best_overlap = overlap_ratio
                            best_match = actual
            
            # Consider it a match if overlap is > 80%
            if best_match and best_overlap >= 0.8:
                matches.append({
                    'expected': expected,
                    'actual': best_match,
                    'overlap': best_overlap
                })
                if best_match in unmatched_actual:
                    unmatched_actual.remove(best_match)
                if expected in unmatched_expected:
                    unmatched_expected.remove(expected)
    
    pdf_source.close()
    pdf_output.close()
    
    # Report results
    print(f"\n📊 RESULTS:")
    total_expected = len(expected_highlights)
    matched_count = len(matches)
    coverage_ratio = matched_count / max(1, total_expected)
    
    print(f"   Expected highlights: {total_expected}")
    print(f"   Matched highlights: {matched_count}")
    print(f"   Coverage: {coverage_ratio:.1%}")
    
    if unmatched_expected:
        print(f"\n   ⚠️  Unmatched expected ({len(unmatched_expected)}):")
        for exp in unmatched_expected[:3]:
            print(f"      Page {exp['page'] + 1}: {exp['content'][:50]}...")
    
    if coverage_ratio >= 0.8:
        print(f"\n✅ Test passed with {coverage_ratio:.1%} coverage")
    else:
        raise AssertionError(f"Highlight coverage is too low: {coverage_ratio:.1%}. Expected >= 80%")


if __name__ == "__main__":
    test_highlight_width_coverage()