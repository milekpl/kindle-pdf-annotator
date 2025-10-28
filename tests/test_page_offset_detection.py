"""
Unit tests for PDF page offset detection.

Tests the _detect_page_offset function to ensure it correctly handles:
- PDFs with page label metadata (the proper way)
- PDFs without page labels (fallback to content search)
- Various offset scenarios (preliminary pages, covers, TOC)
- Edge cases and error handling
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import MagicMock, patch
import fitz

from src.kindle_parser.amazon_coordinate_system import _detect_page_offset


class MockPage:
    """Mock PyMuPDF page for testing"""
    def __init__(self, text_content):
        self.text_content = text_content
    
    def get_text(self):
        return self.text_content


class MockPDF:
    """Mock PyMuPDF document for testing"""
    def __init__(self, pages, page_labels=None):
        self.pages = pages
        self.page_labels = page_labels
        self._label_call_count = 0
    
    def __len__(self):
        return len(self.pages)
    
    def __getitem__(self, index):
        if index < 0 or index >= len(self.pages):
            raise IndexError(f"Page index {index} out of range")
        return self.pages[index]
    
    def get_page_labels(self):
        """Return page label metadata"""
        if self.page_labels is None:
            return []
        return self.page_labels


class TestPageOffsetDetection:
    """Test suite for PDF page offset detection"""
    
    def test_pdf_with_page_labels_standard_offset(self):
        """Test PDF with standard page labels (preliminary pages 1-10, content starts page 1 at index 10)"""
        # Create mock PDF with page labels
        # Pages 0-9: preliminary (cover, copyright, TOC)
        # Page 10+: main content starting at "page 1"
        
        pages = [MockPage(f"Preliminary page {i}") for i in range(10)]
        pages.extend([MockPage(f"Main content page {i+1}") for i in range(20)])
        
        page_labels = [
            {'startpage': 0, 'prefix': 'Cover', 'firstpagenum': 1},
            {'startpage': 10, 'prefix': '', 'firstpagenum': 1, 'style': 'D'}
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        # Mock clippings that reference logical page 1 (which is PDF index 10)
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Main content page 1'}
        ]
        
        mock_highlights = []  # Not needed for page label detection
        
        offset = _detect_page_offset(mock_clippings, mock_highlights, mock_pdf)
        
        # Offset should be +10
        # Because: clipping page 1 + 10 = PDF index 10 + 1 = 11 (1-based)
        assert offset == 10, f"Expected offset +10, got {offset}"
    
    def test_pdf_with_page_labels_roman_numerals(self):
        """Test PDF with roman numeral preliminaries"""
        pages = [MockPage(f"Intro page {i}") for i in range(5)]
        pages.extend([MockPage(f"Chapter content {i+1}") for i in range(15)])
        
        page_labels = [
            {'startpage': 0, 'prefix': '', 'firstpagenum': 1, 'style': 'r'},  # Roman i, ii, iii...
            {'startpage': 5, 'prefix': '', 'firstpagenum': 1, 'style': 'D'}   # Arabic 1, 2, 3...
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Chapter content 1'}
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Logical page 1 starts at PDF index 5
        # Offset: 5 + 1 - 1 = 5
        assert offset == 5, f"Expected offset +5, got {offset}"
    
    def test_pdf_without_page_labels_no_offset(self):
        """Test PDF without page labels, content matches exactly"""
        pages = [MockPage(f"Page {i+1} content here") for i in range(10)]
        
        mock_pdf = MockPDF(pages, page_labels=None)  # No page labels
        
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Page 1 content here'},
            {'pdf_page': 3, 'content': 'Page 3 content here'},
            {'pdf_page': 5, 'content': 'Page 5 content here'},
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # No offset needed - pages match
        assert offset == 0, f"Expected no offset, got {offset}"
    
    def test_pdf_without_page_labels_with_offset(self):
        """Test PDF without page labels but content is offset"""
        # PDF has 10 preliminary pages, then main content
        pages = [MockPage(f"Preliminary {i}") for i in range(10)]
        # Make content searchable with enough text
        pages.extend([MockPage(f"This is main page {i+1} text with enough content to search for properly") for i in range(20)])
        
        mock_pdf = MockPDF(pages, page_labels=None)  # No page labels
        
        # Clippings reference logical page numbers (starting at 1)
        # But content is actually at PDF indices 10+
        mock_clippings = [
            {'pdf_page': 1, 'content': 'This is main page 1 text with enough'},
            {'pdf_page': 5, 'content': 'This is main page 5 text with enough'},
            {'pdf_page': 10, 'content': 'This is main page 10 text with enough'},
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should detect +10 offset via content search
        assert offset == 10, f"Expected offset +10 from content search, got {offset}"
    
    def test_philosophy_pdf_case(self):
        """Test the real Philosophy PDF case (10-page offset)"""
        # Philosophy PDF: pages 0-9 are preliminary, page 10 starts as "page 1"
        # Clipping says "page 68", actual content on PDF index 77 (labeled as page 68)
        
        pages = [MockPage(f"Cover/TOC {i}") for i in range(10)]
        pages.extend([MockPage(f"Philosophy content page {i+1}") for i in range(100)])
        
        page_labels = [
            {'startpage': 10, 'prefix': '', 'firstpagenum': 1, 'style': 'D'}
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        # Clipping references page 68 (logical)
        mock_clippings = [
            {'pdf_page': 68, 'content': 'First, syntax is not semantics'}
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Page 68 (logical) = PDF index 77
        # Offset = 77 + 1 - 68 = 10
        assert offset == 10, f"Expected Philosophy PDF offset +10, got {offset}"
    
    def test_negative_offset_unusual_numbering(self):
        """Test unusual case where PDF numbering starts before logical numbering"""
        # Some PDFs might number cover as page 1, but content declares page 1 later
        
        pages = [MockPage("Cover page"), MockPage("Copyright")]
        pages.extend([MockPage(f"Content {i}") for i in range(10)])
        
        # Content starts at index 2 but is numbered from page 3
        page_labels = [
            {'startpage': 0, 'prefix': '', 'firstpagenum': 1, 'style': 'D'},
            {'startpage': 2, 'prefix': '', 'firstpagenum': 3, 'style': 'D'}
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        mock_clippings = [
            {'pdf_page': 3, 'content': 'Content 0'}
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Logical page 3 is at PDF index 2
        # Offset = 2 + 1 - 3 = 0
        assert offset == 0, f"Expected offset 0, got {offset}"
    
    def test_empty_clippings_list(self):
        """Test behavior with no clippings"""
        pages = [MockPage(f"Page {i}") for i in range(10)]
        mock_pdf = MockPDF(pages, page_labels=None)
        
        offset = _detect_page_offset([], [], mock_pdf)
        
        # Should return 0 when no clippings to analyze
        assert offset == 0, f"Expected 0 for empty clippings, got {offset}"
    
    def test_clippings_without_content(self):
        """Test clippings that have no content (bookmarks)"""
        pages = [MockPage(f"Page {i}") for i in range(10)]
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Clippings without content field
        mock_clippings = [
            {'pdf_page': 1},
            {'pdf_page': 2, 'content': ''},  # Empty content
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should handle gracefully, return 0
        assert offset == 0, f"Expected 0 for contentless clippings, got {offset}"
    
    def test_clippings_with_short_content(self):
        """Test clippings with very short content (< 20 chars)"""
        pages = [MockPage("Short") for i in range(10)]
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Short content that won't be sampled
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Hi'},
            {'pdf_page': 2, 'content': 'Test'},
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should skip short content, return 0
        assert offset == 0, f"Expected 0 for short content clippings, got {offset}"
    
    def test_content_not_found_in_pdf(self):
        """Test when clipping content doesn't appear in PDF at all"""
        pages = [MockPage(f"Different content {i}") for i in range(10)]
        mock_pdf = MockPDF(pages, page_labels=None)
        
        mock_clippings = [
            {'pdf_page': 1, 'content': 'This text does not exist in the PDF at all'},
            {'pdf_page': 2, 'content': 'Neither does this one'},
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should return 0 when no content found
        assert offset == 0, f"Expected 0 when content not found, got {offset}"
    
    def test_multiple_conflicting_offsets_picks_most_common(self):
        """Test when different clippings suggest different offsets"""
        # PDF with content scattered
        pages = [MockPage("Intro with some text")]
        pages.extend([MockPage(f"This is Section A page {i} with searchable content here") for i in range(10)])
        pages.extend([MockPage(f"This is Section B page {i} with more content to find") for i in range(10)])
        
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Most clippings have +1 offset, one has different
        mock_clippings = [
            {'pdf_page': 1, 'content': 'This is Section A page 0 with searchable'},  # Found at index 1, offset +1
            {'pdf_page': 2, 'content': 'This is Section A page 1 with searchable'},  # Found at index 2, offset +1
            {'pdf_page': 3, 'content': 'This is Section A page 2 with searchable'},  # Found at index 3, offset +1
            {'pdf_page': 10, 'content': 'This is Section B page 0 with more'}, # Found at index 11, offset +1
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should pick most common offset (+1 appears 4 times)
        assert offset == 1, f"Expected most common offset +1, got {offset}"
    
    def test_small_offset_accepted(self):
        """Test that small offsets (1 page) are properly detected (e.g., cover page)"""
        pages = [MockPage(f"This is page {i} with enough text content here") for i in range(20)]
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Content found at slightly different page (1 page off - common for cover pages)
        # Page 5 content is at index 5, claiming page 5 would give offset (5+1)-5=1
        mock_clippings = [
            {'pdf_page': 5, 'content': 'This is page 5 with enough text content'},  # Found at index 5, offset = (5+1)-5 = 1
            {'pdf_page': 10, 'content': 'This is page 10 with enough text content'}, # Found at index 10, offset = (10+1)-10 = 1
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Offset of 1 should be accepted (common case: cover page)
        assert offset == 1, f"Expected offset +1 for single page offset, got {offset}"
    
    def test_large_offset_accepted(self):
        """Test that large offsets (>= 2 pages) are accepted"""
        pages = [MockPage("Cover page content"), MockPage("Title page content")]
        pages.extend([MockPage(f"Main content for chapter {i} with enough text to match") for i in range(20)])
        
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Content consistently off by 2 pages
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Main content for chapter 0 with enough'},  # Found at index 2, offset +2
            {'pdf_page': 5, 'content': 'Main content for chapter 4 with enough'},  # Found at index 6, offset +2
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Offset of 2 should be accepted (>= 2 threshold)
        assert offset == 2, f"Expected offset +2, got {offset}"
    
    def test_search_range_limits(self):
        """Test that search only looks in reasonable range around claimed page"""
        # Create large PDF
        pages = [MockPage(f"Page {i}") for i in range(100)]
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Clipping claims page 50, but content is way off at page 90
        # Should not find it (outside ±20 page search range)
        mock_clippings = [
            {'pdf_page': 50, 'content': 'Page 90'},
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should not find content outside range, return 0
        assert offset == 0, f"Expected 0 when content outside search range, got {offset}"
    
    def test_case_insensitive_content_matching(self):
        """Test that content matching is case-insensitive"""
        pages = [MockPage("PRELIMINARY CONTENT HERE")]
        pages.extend([MockPage(f"Chapter {i} CONTENT with MORE TEXT for searching purposes") for i in range(10)])
        
        mock_pdf = MockPDF(pages, page_labels=None)
        
        # Clipping has lowercase, PDF has uppercase
        mock_clippings = [
            {'pdf_page': 1, 'content': 'chapter 0 content with more text for'},
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should find match despite case difference
        # Page 1 clipping found at index 1, offset = 1
        assert offset == 1, f"Expected offset +1 with case-insensitive match, got {offset}"
    
    def test_page_labels_with_no_decimal_style(self):
        """Test PDF with page labels but no 'D' (decimal) style"""
        pages = [MockPage(f"Page {i}") for i in range(20)]
        
        # Only roman numerals, no decimal section
        page_labels = [
            {'startpage': 0, 'prefix': '', 'firstpagenum': 1, 'style': 'r'},
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Page 0'}
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should still use the roman numeral rule (fallback)
        # startpage=0, firstpagenum=1 -> offset = 0 + 1 - 1 = 0
        assert offset == 0, f"Expected offset 0 with roman style fallback, got {offset}"
    
    def test_page_labels_multiple_decimal_rules(self):
        """Test PDF with multiple decimal numbering rules (pick the main one)"""
        pages = [MockPage(f"Page {i}") for i in range(50)]
        
        # Multiple decimal sections
        # The logic should pick the first one with firstpagenum=1
        page_labels = [
            {'startpage': 10, 'prefix': '', 'firstpagenum': 1, 'style': 'D'},  # Main content - should pick this
            {'startpage': 0, 'prefix': 'Appendix ', 'firstpagenum': 5, 'style': 'D'},  # Not firstpagenum=1
            {'startpage': 40, 'prefix': 'Index ', 'firstpagenum': 10, 'style': 'D'},  # Not firstpagenum=1
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        mock_clippings = [
            {'pdf_page': 1, 'content': 'Page 0'}
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        # Should pick the one with startpage=10 and firstpagenum=1 (main content)
        assert offset == 10, f"Expected offset +10 from main content rule, got {offset}"
    
    def test_regression_philosophy_pdf(self):
        """Regression test for Philosophy PDF (real-world case)"""
        # Simulate Philosophy PDF structure
        pages = []
        # Pages 0-9: Cover, copyright, TOC (not numbered)
        for i in range(10):
            pages.append(MockPage(f"Preliminary material {i}"))
        
        # Pages 10-109: Main content numbered 1-100
        for i in range(100):
            pages.append(MockPage(f"{i+1}\nPhilosophy in a new century\nContent for page {i+1}"))
        
        # Actual page labels from Philosophy PDF
        page_labels = [
            {'startpage': 0, 'prefix': 'Cover', 'firstpagenum': 1},
            {'startpage': 1, 'prefix': '', 'firstpagenum': 3, 'style': 'a'},
            {'startpage': 2, 'prefix': '', 'firstpagenum': 1, 'style': 'r'},
            {'startpage': 10, 'prefix': '', 'firstpagenum': 1, 'style': 'D'}
        ]
        
        mock_pdf = MockPDF(pages, page_labels)
        
        # Clipping from page 68 (which is actually PDF index 77)
        mock_clippings = [
            {'pdf_page': 68, 'content': 'First, syntax is not semantics, and second, simulation is not duplication'}
        ]
        
        offset = _detect_page_offset(mock_clippings, [], mock_pdf)
        
        assert offset == 10, f"Expected Philosophy PDF offset +10, got {offset}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
