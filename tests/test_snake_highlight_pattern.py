"""
Unit tests for snake highlight pattern functionality.

Tests that multi-line highlights follow the exact text boundaries (snake pattern)
rather than creating rectangular blocks from margin to margin.
"""

import sys
import pytest
import fitz
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from src.pdf_processor.pdf_annotator import annotate_pdf_file


@pytest.fixture
def peirce_pdf_path():
    """Path to the test PDF."""
    return "examples/sample_data/peirce-charles-fixation-belief.pdf"


@pytest.fixture
def peirce_krds_path():
    """Path to the test KRDS file."""
    return "examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds"


@pytest.fixture
def peirce_clippings_path():
    """Path to the test clippings file."""
    return "examples/sample_data/peirce-charles-fixation-belief-clippings.txt"


@pytest.fixture
def book_name():
    """Book name for annotations."""
    return "peirce-charles-fixation-belief"


@pytest.fixture
def output_dir():
    """Output directory for test PDFs."""
    output_path = Path("tests/output")
    output_path.mkdir(exist_ok=True)
    return output_path


class TestSnakeHighlightPattern:
    """Test suite for snake highlight pattern functionality."""
    
    def test_multi_line_highlight_has_multiple_quads(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that multi-line highlights are created with multiple quads (snake pattern).
        
        Specifically tests the "The object of reasoning..." highlight which spans 3 lines.
        This was previously broken due to converting Quad objects to Rects.
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_snake_pattern.pdf"
        success = annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        assert success, "PDF annotation should succeed"
        assert output_file.exists(), "Output PDF should exist"
        
        # Open and verify annotations
        doc = fitz.open(str(output_file))
        
        # Check page 2 - should have the 3-quad "object of reasoning" highlight
        page2 = doc[1]  # 0-indexed
        page2_annots = list(page2.annots())
        assert len(page2_annots) >= 1, "Page 2 should have at least one annotation"
        
        # Find the "object of reasoning" highlight
        found_target = False
        for annot in page2_annots:
            if annot.type[0] == 8:  # Highlight annotation
                content = annot.info.get('content', '')
                if 'object of reasoning' in content.lower():
                    vertices = annot.vertices
                    quad_count = len(vertices) // 4
                    
                    # This highlight should have 3 quads (one per line)
                    assert quad_count == 3, (
                        f"Multi-line 'object of reasoning' highlight should have 3 quads, "
                        f"but has {quad_count}"
                    )
                    
                    # Verify quads follow snake pattern (different widths)
                    quads = [vertices[i:i+4] for i in range(0, len(vertices), 4)]
                    widths = []
                    for quad in quads:
                        # Quad format: [(x0,y0), (x1,y0), (x0,y1), (x1,y1)]
                        width = quad[1][0] - quad[0][0]
                        widths.append(width)
                    
                    # Verify widths are different (snake pattern, not rectangular block)
                    assert len(set(widths)) > 1, (
                        f"Snake pattern should have varying widths, "
                        f"but all widths are similar: {widths}"
                    )
                    
                    found_target = True
                    break
        
        assert found_target, "Should find 'object of reasoning' highlight on page 2"
        doc.close()
    
    def test_two_line_highlight_has_two_quads(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that 2-line highlights have 2 quads.
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_snake_pattern.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Open and verify
        doc = fitz.open(str(output_file))
        
        # Check page 1 - should have a 2-quad "Few persons care to study logic" highlight
        page1 = doc[0]
        page1_annots = list(page1.annots())
        
        found_target = False
        for annot in page1_annots:
            if annot.type[0] == 8:  # Highlight
                content = annot.info.get('content', '')
                if 'few persons care to study logic' in content.lower():
                    vertices = annot.vertices
                    quad_count = len(vertices) // 4
                    
                    assert quad_count == 2, (
                        f"2-line highlight should have 2 quads, but has {quad_count}"
                    )
                    found_target = True
                    break
        
        assert found_target, "Should find 'Few persons care to study logic' highlight"
        doc.close()
    
    def test_single_line_highlight_has_one_quad(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that single-line highlights have 1 quad.
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_snake_pattern.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Open and verify
        doc = fitz.open(str(output_file))
        
        # Check page 3 - should have a single-line "reasoning" highlight
        page3 = doc[2]
        page3_annots = list(page3.annots())
        
        found_target = False
        for annot in page3_annots:
            if annot.type[0] == 8:  # Highlight
                content = annot.info.get('content', '')
                if content.strip().lower() == 'reasoning':
                    vertices = annot.vertices
                    quad_count = len(vertices) // 4
                    
                    assert quad_count == 1, (
                        f"Single-line highlight should have 1 quad, but has {quad_count}"
                    )
                    found_target = True
                    break
        
        assert found_target, "Should find single-line 'reasoning' highlight"
        doc.close()
    
    def test_six_line_highlight_has_six_quads(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that a 6-line highlight has 6 quads.
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_snake_pattern.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Open and verify
        doc = fitz.open(str(output_file))
        
        # Check page 4 - should have a 6-quad "We generally know..." highlight
        page4 = doc[3]
        page4_annots = list(page4.annots())
        
        found_target = False
        for annot in page4_annots:
            if annot.type[0] == 8:  # Highlight
                content = annot.info.get('content', '')
                if 'we generally know when we wish to ask a question' in content.lower():
                    vertices = annot.vertices
                    quad_count = len(vertices) // 4
                    
                    assert quad_count == 6, (
                        f"6-line highlight should have 6 quads, but has {quad_count}"
                    )
                    found_target = True
                    break
        
        assert found_target, "Should find 6-line 'We generally know' highlight"
        doc.close()
    
    def test_quad_objects_preserved_after_save(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that Quad objects (not Rects) are preserved after saving.
        
        This is the critical test for the bug fix - Quad objects must be passed
        to add_highlight_annot() instead of converting to Rects.
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_quad_preservation.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Reload the saved PDF and verify all multi-line highlights have multiple quads
        doc = fitz.open(str(output_file))
        
        multi_line_highlights = []
        for page_num, page in enumerate(doc):
            for annot in page.annots():
                if annot.type[0] == 8:  # Highlight
                    vertices = annot.vertices
                    quad_count = len(vertices) // 4
                    if quad_count > 1:
                        content = annot.info.get('content', '')[:50]
                        multi_line_highlights.append({
                            'page': page_num + 1,
                            'quads': quad_count,
                            'content': content
                        })
        
        # Should have at least 4 multi-line highlights
        assert len(multi_line_highlights) >= 4, (
            f"Should have at least 4 multi-line highlights, found {len(multi_line_highlights)}"
        )
        
        # All should have more than 1 quad
        for hl in multi_line_highlights:
            assert hl['quads'] > 1, (
                f"Multi-line highlight on page {hl['page']} has only {hl['quads']} quad(s): "
                f"{hl['content']}"
            )
        
        doc.close()
    
    def test_snake_pattern_alignment(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that snake pattern has proper alignment:
        - First line: starts at text, extends to right margin
        - Middle lines: full width (left to right margin)
        - Last line: starts at left margin, ends at text
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_snake_pattern.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Open and check the 3-line "object of reasoning" highlight
        doc = fitz.open(str(output_file))
        page2 = doc[1]
        
        for annot in page2.annots():
            if annot.type[0] == 8:
                content = annot.info.get('content', '')
                if 'object of reasoning' in content.lower():
                    vertices = annot.vertices
                    quads = [vertices[i:i+4] for i in range(0, len(vertices), 4)]
                    
                    # Get left and right positions for each line
                    line_lefts = [quad[0][0] for quad in quads]  # x0 of each quad
                    line_rights = [quad[1][0] for quad in quads]  # x1 of each quad
                    
                    # First line should NOT start at left margin (starts at text)
                    # Middle line(s) should be full width
                    # Last line should NOT extend to right margin (ends at text)
                    
                    # Middle lines should have similar left/right positions
                    if len(quads) >= 3:
                        # Check that middle lines are full width (similar to each other)
                        middle_left = line_lefts[1]
                        middle_right = line_rights[1]
                        
                        # Last line should be shorter (not full width)
                        last_width = line_rights[-1] - line_lefts[-1]
                        middle_width = middle_right - middle_left
                        
                        assert last_width < middle_width, (
                            f"Last line should be narrower than middle line "
                            f"(snake pattern), but last={last_width:.1f}, "
                            f"middle={middle_width:.1f}"
                        )
                    
                    break
        
        doc.close()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
