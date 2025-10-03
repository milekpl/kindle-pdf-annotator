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
        
        After the period normalization fix, the "object of reasoning" highlight now spans 6 lines.
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
        
        # Check page 2 - should have the 6-quad "object of reasoning" highlight
        page2 = doc[1]  # 0-indexed
        page2_annots = list(page2.annots())
        assert len(page2_annots) >= 1, "Page 2 should have at least one annotation"
        
        # Find the multi-line highlight (6 quads after period fix)
        found_target = False
        for annot in page2_annots:
            if annot.type[0] == 8:  # Highlight annotation
                vertices = annot.vertices
                if vertices:
                    quad_count = len(vertices) // 4
                    
                    # After the period normalization fix, this should now be 6 quads
                    if quad_count >= 6:
                        # Verify it's exactly 6
                        assert quad_count == 6, (
                            f"Multi-line highlight should have 6 quads "
                            f"(after period fix), but has {quad_count}"
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
                        
                        # Verify no content field (Kindle only adds content to notes, not highlights)
                        content = annot.info.get('content', '')
                        assert content == '', f"Highlight should have no content, but has: {repr(content[:50])}"
                        
                        found_target = True
                        break
        
        assert found_target, "Should find multi-line highlight (6 quads) on page 2"
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
        
        # Check page 1 - should have a 2-quad highlight
        page1 = doc[0]
        page1_annots = list(page1.annots())
        
        # Find a 2-quad highlight
        found_target = False
        for annot in page1_annots:
            if annot.type[0] == 8:  # Highlight
                vertices = annot.vertices
                if vertices:
                    quad_count = len(vertices) // 4
                    if quad_count == 2:
                        found_target = True
                        break
        
        assert found_target, "Should find a 2-quad highlight on page 1"
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
        
        # Check page 3 - should have a single-line highlight
        page3 = doc[2]
        page3_annots = list(page3.annots())
        
        # Find a 1-quad highlight
        found_target = False
        for annot in page3_annots:
            if annot.type[0] == 8:  # Highlight
                vertices = annot.vertices
                if vertices:
                    quad_count = len(vertices) // 4
                    if quad_count == 1:
                        found_target = True
                        break
        
        assert found_target, "Should find a 1-quad highlight on page 3"
        doc.close()
    
    def test_all_highlights_have_no_content(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that all highlights have no content field (Kindle distinction).
        
        Kindle differentiates between highlights (no content) and notes (with content).
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_no_content.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Verify all highlights have no content
        doc = fitz.open(str(output_file))
        
        highlight_count = 0
        for page in doc:
            for annot in page.annots():
                if annot.type[0] == 8:  # Highlight
                    highlight_count += 1
                    content = annot.info.get('content', '')
                    assert content == '', (
                        f"Highlight on page {page.number + 1} should have no content, "
                        f"but has: {repr(content[:50])}"
                    )
        
        assert highlight_count > 0, "Should have at least one highlight to test"
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
                    if vertices:
                        quad_count = len(vertices) // 4
                        if quad_count > 1:
                            multi_line_highlights.append({
                                'page': page_num + 1,
                                'quads': quad_count
                            })
        
        # Should have at least 3 multi-line highlights
        assert len(multi_line_highlights) >= 3, (
            f"Should have at least 3 multi-line highlights, found {len(multi_line_highlights)}"
        )
        
        # All should have more than 1 quad
        for hl in multi_line_highlights:
            assert hl['quads'] > 1, (
                f"Multi-line highlight on page {hl['page']} has only {hl['quads']} quad(s)"
            )
        
        doc.close()
    
    def test_snake_pattern_alignment(self, peirce_pdf_path, peirce_krds_path, peirce_clippings_path, book_name, output_dir):
        """
        Test that snake pattern has proper alignment with varying widths.
        """
        # Parse and create annotations
        annotations = create_amazon_compliant_annotations(peirce_krds_path, peirce_clippings_path, book_name)
        pdf_annotations = convert_amazon_to_pdf_annotator_format(annotations)
        
        # Create annotated PDF
        output_file = output_dir / "test_snake_pattern.pdf"
        annotate_pdf_file(peirce_pdf_path, pdf_annotations, output_path=str(output_file))
        
        # Open and check multi-line highlights have varying widths
        doc = fitz.open(str(output_file))
        
        found_varying_width = False
        for page in doc:
            for annot in page.annots():
                if annot.type[0] == 8:
                    vertices = annot.vertices
                    if vertices:
                        quad_count = len(vertices) // 4
                        if quad_count >= 3:
                            quads = [vertices[i:i+4] for i in range(0, len(vertices), 4)]
                            
                            # Get widths
                            widths = [quad[1][0] - quad[0][0] for quad in quads]
                            
                            # Last line should be narrower than middle lines (snake pattern)
                            if len(set(widths)) > 1:
                                found_varying_width = True
                                break
            if found_varying_width:
                break
        
        assert found_varying_width, "Should find at least one multi-line highlight with varying widths (snake pattern)"
        doc.close()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
