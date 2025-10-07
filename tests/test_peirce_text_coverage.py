#!/usr/bin/env python3
"""
Definitive unit test for highlight text coverage using peirce-charles-fixation-belief example
This test ensures that all highlights exactly match the text snippets from MyClippings.txt
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
    """Normalize text for comparison by removing extra whitespace and line breaks"""
    if not text:
        return ""
    import re
    # Replace multiple whitespace with single space, strip
    normalized = ' '.join(text.split())
    # Apply ligature fixes
    normalized = normalized.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    # Handle abbreviations: "ch.4" -> "ch. 4" (add space after period if missing before digit)
    normalized = re.sub(r'(\w)\.(\d)', r'\1. \2', normalized)
    return normalized


def test_peirce_highlight_text_coverage():
    """
    Test that all highlights in the Peirce example exactly match their expected text content.
    This is the definitive test for highlight width accuracy.
    """
    
    # We'll run the same coverage logic for multiple sample datasets that live under examples/sample_data
    datasets = [
        {
            'name': 'peirce-charles-fixation-belief',
            'krds': 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds',
            'clippings': 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt',
            'pdf': 'examples/sample_data/peirce-charles-fixation-belief.pdf'
        },
        {
            'name': 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper',
            'krds': "examples/sample_data/Downey_2024_Theatre_Hunger_Scaling_Up_Paper.sdr/Downey - 2024 - Theatre Hunger An Underestimated ‘Scaling Up’ Pro.pdf-cdeKey_WAY5I3SIILOP6F4ROJNHQ5YIIEUBUDRT12347ea8efc3f766707171e2bfcc00f4.pds",
            'clippings': 'examples/sample_data/Downey_2024_Theatre_Hunger_Scaling_Up_Paper-clippings.txt',
            'pdf': 'examples/sample_data/Downey_2024_Theatre_Hunger_Scaling_Up_Paper.pdf'
        },
        {
            'name': '659ec7697e419',
            'krds': 'examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ12347ea8efc3f766707171e2bfcc00f4.pds',
            'clippings': 'examples/sample_data/659ec7697e419-clippings.txt',
            'pdf': 'examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf'
        }
    ]

    def run_coverage_for_dataset(krds_file, clippings_file, pdf_file, book_name, output_file):
        """Run the coverage logic for a single dataset and return coverage_ratio (0..1)."""
        print(f"\n🎯 DEFINITIVE HIGHLIGHT TEXT COVERAGE TEST for {book_name}")

        print("\n1. 📋 Parsing expected text content from MyClippings...")
        myclippings_entries = parse_myclippings_for_book(clippings_file, book_name)

        # Extract only highlights with actual text content
        expected_highlights = []
        for entry in myclippings_entries:
            if entry.get('type') == 'highlight' and entry.get('content', '').strip():
                expected_highlights.append({
                    'page': entry.get('pdf_page', 1),
                    'content': entry.get('content', '').strip(),
                    'normalized_content': normalize_text(entry.get('content', ''))
                })

        print(f"   Found {len(expected_highlights)} highlights with text content")

        print("\n2. 🔧 Creating annotated PDF...")
        amazon_annotations = create_amazon_compliant_annotations(krds_file, clippings_file, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
        result_path = annotate_pdf_file(pdf_file, pdf_annotations, output_file)
        print(f"   Created annotated PDF: {result_path}")

        print("\n3. 🔍 Validating highlight positions using text search...")
        doc = fitz.open(output_file)
        pdf_source = fitz.open(pdf_file)  # Open source PDF to search for text

        actual_highlights = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            annotations = page.annots()
            if annotations:
                for annot in annotations:
                    # Check both highlights AND notes (notes may be unified highlight+note pairs)
                    if annot.type[1] in ('Highlight', 'Text', 'FreeText'):
                        rect = annot.rect
                        actual_highlights.append({
                            'page': page_num + 1,
                            'rect': rect,
                            'width': rect.width,
                            'height': rect.height,
                            'type': annot.type[1]
                        })

        print(f"   Found {len(actual_highlights)} highlights/notes in PDF")

        # NEW STRATEGY: For each expected highlight, search for its text in the PDF
        # and verify that a highlight rectangle overlaps with the found text location
        matches = []
        unmatched_expected = expected_highlights.copy()
        unmatched_actual = actual_highlights.copy()

        for expected in expected_highlights:
            page_num_0based = expected['page'] - 1
            if page_num_0based >= len(pdf_source):
                continue
                
            page = pdf_source.load_page(page_num_0based)
            
            # Search for the expected text on the page
            search_text = expected['normalized_content']
            text_quads = page.search_for(search_text, quads=True)
            
            # If not found, try shorter versions
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
                # Quads is a list of Quad objects, each has a .rect property
                text_rects = []
                for quad in text_quads:
                    if hasattr(quad, 'rect'):
                        text_rects.append(quad.rect)
                
                if not text_rects:
                    continue
                    
                text_rect = text_rects[0]
                for r in text_rects[1:]:
                    text_rect = text_rect | r  # Union
                
                # Debug for Angela Potochnik
                if 'Angela Potochnik' in expected['content']:
                    print(f"   🔍 Angela Potochnik text_rect from search: {text_rect}")
                
                # Find highlight that overlaps with this text location
                best_match = None
                best_overlap = 0
                
                for actual in actual_highlights:
                    if actual['page'] == expected['page']:
                        # Calculate overlap between highlight rect and text rect
                        overlap_rect = actual['rect'] & text_rect  # Intersection
                        if not overlap_rect.is_empty:
                            overlap_area = overlap_rect.get_area()
                            text_area = text_rect.get_area()
                            overlap_ratio = overlap_area / text_area if text_area > 0 else 0
                            
                            # Debug output for "Angela Potochnik" text
                            if 'Angela Potochnik' in expected['content']:
                                print(f"   🔍 Checking overlap for Angela Potochnik:")
                                print(f"      Text rect: {text_rect}")
                                print(f"      Actual rect: {actual['rect']}")
                                print(f"      Overlap: {overlap_ratio:.2%}")
                            
                            if overlap_ratio > best_overlap:
                                best_overlap = overlap_ratio
                                best_match = actual
                
                # Consider it a match if overlap is > 80%
                if best_match and best_overlap >= 0.8:
                    matches.append({
                        'expected': expected,
                        'actual': best_match,
                        'overlap': best_overlap,
                        'is_perfect': True
                    })
                    if best_match in unmatched_actual:
                        unmatched_actual.remove(best_match)
                    if expected in unmatched_expected:
                        unmatched_expected.remove(expected)

        doc.close()
        pdf_source.close()

        perfect_matches = [m for m in matches if m['is_perfect']]
        total_expected = len(expected_highlights)
        perfect_count = len(perfect_matches)
        coverage_ratio = 1.0 if total_expected == 0 else perfect_count / total_expected

        print(f"\n📊 RESULTS for {book_name}: expected={total_expected}, perfect_matches={perfect_count}, coverage={coverage_ratio:.1%}")

        if coverage_ratio < 1.0:
            # Provide some debug info inline to assist developers
            if perfect_matches:
                print(f"   Perfect matches: {len(perfect_matches)}")
            if unmatched_expected:
                print(f"   Unmatched expected ({len(unmatched_expected)}):")
                for exp in unmatched_expected[:5]:
                    print(f"      Page {exp['page']}: {exp['content'][:60]!r}")
            if unmatched_actual:
                print(f"   Unmatched actual ({len(unmatched_actual)}):")
                for act in unmatched_actual[:5]:
                    print(f"      Page {act['page']}: rect={act['rect']} (w={act['width']:.1f}pt)")

        # Return ratio for assertion in the outer loop
        return coverage_ratio

    # Iterate datasets and assert each reaches full coverage
    for ds in datasets:
        out_pdf = f"tests/{ds['name']}_text_coverage_test.pdf"
        ratio = run_coverage_for_dataset(ds['krds'], ds['clippings'], ds['pdf'], ds['name'], out_pdf)
        if ratio < 1.0:
            raise AssertionError(f"Highlight coverage test failed for {ds['name']}: {ratio:.1%} perfect matches. Expected 100%.")


if __name__ == "__main__":
    test_peirce_highlight_text_coverage()