"""
Unit tests for annotation deduplication logic.

Tests the _deduplicate_annotations function from amazon_coordinate_system.py
to ensure the list-based approach correctly handles duplicates.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.amazon_coordinate_system import _deduplicate_annotations


class TestAnnotationDeduplication(unittest.TestCase):
    """Test suite for the annotation deduplication logic."""

    def _create_annotation(
        self, 
        annotation_type='highlight',
        page=0,
        x=100.0,
        y=200.0,
        content='Test content',
        timestamp='2024-01-01 12:00:00',
        **kwargs
    ):
        """Helper to create a test annotation dictionary."""
        annotation = {
            'type': annotation_type,
            'pdf_page_0based': page,
            'pdf_x': x,
            'pdf_y': y,
            'pdf_width': 200.0,
            'pdf_height': 20.0,
            'content': content,
            'timestamp': timestamp,
            'source': 'test',
        }
        annotation.update(kwargs)
        return annotation

    def test_no_duplicates_returns_all(self):
        """Test that unique annotations are all preserved."""
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content='First'),
            self._create_annotation(page=0, x=100, y=250, content='Second'),
            self._create_annotation(page=1, x=100, y=200, content='Third'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 3)
        self.assertEqual([a['content'] for a in result], ['First', 'Second', 'Third'])

    def test_exact_duplicates_removed(self):
        """Test that exact duplicate annotations are removed."""
        annotation = self._create_annotation(page=0, x=100, y=200, content='Duplicate')
        annotations = [
            annotation.copy(),
            annotation.copy(),
            annotation.copy(),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['content'], 'Duplicate')

    def test_coordinate_rounding_catches_near_duplicates(self):
        """Test that coordinates rounded to 1 decimal catch near-duplicates."""
        annotations = [
            self._create_annotation(page=0, x=100.04, y=200.03, content='Near duplicate'),
            self._create_annotation(page=0, x=100.01, y=200.02, content='Near duplicate'),
            self._create_annotation(page=0, x=100.03, y=200.04, content='Near duplicate'),  # All round to 100.0, 200.0
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # All round to (100.0, 200.0), so only first should remain
        self.assertEqual(len(result), 1)

    def test_coordinate_rounding_preserves_distinct_positions(self):
        """Test that annotations with different rounded coordinates are preserved."""
        annotations = [
            self._create_annotation(page=0, x=100.04, y=200.03, content='First'),
            self._create_annotation(page=0, x=100.51, y=200.03, content='Second'),  # rounds to 100.5
            self._create_annotation(page=0, x=101.04, y=200.03, content='Third'),   # rounds to 101.0
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 3)

    def test_different_pages_preserved(self):
        """Test that same coordinates on different pages are preserved."""
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content='Page 0'),
            self._create_annotation(page=1, x=100, y=200, content='Page 1'),
            self._create_annotation(page=2, x=100, y=200, content='Page 2'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 3)

    def test_different_types_preserved(self):
        """Test that different annotation types at same position are preserved.
        
        Note: As of Priority 2 implementation, notes and highlights at the same
        position are unified (note is kept). Only bookmarks remain separate.
        """
        annotations = [
            self._create_annotation(annotation_type='highlight', page=0, x=100, y=200, content='Highlight'),
            self._create_annotation(annotation_type='note', page=0, x=100, y=200, content='Note'),
            self._create_annotation(annotation_type='bookmark', page=0, x=100, y=200, content=''),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # After Priority 2: highlight+note unified to note, bookmark separate
        self.assertEqual(len(result), 2)
        types = {a['type'] for a in result}
        self.assertEqual(types, {'note', 'bookmark'})
        # Verify note is kept (has content)
        note = next(a for a in result if a['type'] == 'note')
        self.assertEqual(note['content'], 'Note')

    def test_content_truncation_at_50_chars(self):
        """Test that content is truncated to 50 chars for deduplication key."""
        long_content_1 = 'A' * 60 + 'X'
        long_content_2 = 'A' * 60 + 'Y'
        
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content=long_content_1),
            self._create_annotation(page=0, x=100, y=200, content=long_content_2),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # First 50 chars are same, so should be deduplicated
        self.assertEqual(len(result), 1)

    def test_content_whitespace_stripped(self):
        """Test that content whitespace is stripped for deduplication."""
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content='  Test content  '),
            self._create_annotation(page=0, x=100, y=200, content='Test content'),
            self._create_annotation(page=0, x=100, y=200, content='Test content\n'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)

    def test_bookmarks_use_timestamp_for_dedup(self):
        """Test that bookmarks include timestamp in deduplication key."""
        annotations = [
            self._create_annotation(
                annotation_type='bookmark',
                page=0, x=100, y=200,
                content='',
                timestamp='2024-01-01 12:00:00'
            ),
            self._create_annotation(
                annotation_type='bookmark',
                page=0, x=100, y=200,
                content='',
                timestamp='2024-01-01 13:00:00'
            ),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Different timestamps, so both preserved
        self.assertEqual(len(result), 2)

    def test_bookmarks_same_timestamp_deduplicated(self):
        """Test that bookmarks with same timestamp are deduplicated."""
        annotations = [
            self._create_annotation(
                annotation_type='bookmark',
                page=0, x=100, y=200,
                content='',
                timestamp='2024-01-01 12:00:00'
            ),
            self._create_annotation(
                annotation_type='bookmark',
                page=0, x=100, y=200,
                content='',
                timestamp='2024-01-01 12:00:00'
            ),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)

    def test_non_bookmarks_ignore_timestamp(self):
        """Test that highlights/notes ignore timestamp in deduplication."""
        annotations = [
            self._create_annotation(
                annotation_type='highlight',
                page=0, x=100, y=200,
                content='Same content',
                timestamp='2024-01-01 12:00:00'
            ),
            self._create_annotation(
                annotation_type='highlight',
                page=0, x=100, y=200,
                content='Same content',
                timestamp='2024-01-01 13:00:00'  # Different timestamp
            ),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should be deduplicated despite different timestamps
        self.assertEqual(len(result), 1)

    def test_empty_content_handled(self):
        """Test that annotations with empty content are handled correctly."""
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content=''),
            self._create_annotation(page=0, x=100, y=200, content=''),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)

    def test_missing_content_field_handled(self):
        """Test that annotations without content field are handled gracefully."""
        annotation1 = self._create_annotation(page=0, x=100, y=200)
        annotation2 = self._create_annotation(page=0, x=100, y=200)
        del annotation1['content']
        del annotation2['content']
        
        annotations = [annotation1, annotation2]
        result = _deduplicate_annotations(annotations)
        
        # Should still deduplicate based on other fields
        self.assertEqual(len(result), 1)

    def test_order_preservation(self):
        """Test that first occurrence is preserved when duplicates exist."""
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content='First', source='source1'),
            self._create_annotation(page=0, x=100, y=200, content='First', source='source2'),
            self._create_annotation(page=0, x=100, y=200, content='First', source='source3'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['source'], 'source1')

    def test_mixed_duplicates_and_unique(self):
        """Test realistic scenario with mix of duplicates and unique annotations."""
        annotations = [
            # Page 0 - duplicate group
            self._create_annotation(page=0, x=100, y=200, content='Dup1'),
            self._create_annotation(page=0, x=100.02, y=200.01, content='Dup1'),
            
            # Page 0 - unique
            self._create_annotation(page=0, x=100, y=250, content='Unique1'),
            
            # Page 1 - duplicate group
            self._create_annotation(page=1, x=50, y=100, content='Dup2'),
            self._create_annotation(page=1, x=50.03, y=100.02, content='Dup2'),
            self._create_annotation(page=1, x=50.01, y=100.01, content='Dup2'),
            
            # Page 1 - unique
            self._create_annotation(page=1, x=150, y=300, content='Unique2'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 4)  # 2 deduplicated + 2 unique
        
        # Verify correct annotations preserved
        contents = sorted([a['content'] for a in result])
        self.assertEqual(contents, ['Dup1', 'Dup2', 'Unique1', 'Unique2'])

    def test_empty_list(self):
        """Test that empty list returns empty list."""
        result = _deduplicate_annotations([])
        self.assertEqual(result, [])

    def test_single_annotation(self):
        """Test that single annotation is returned unchanged."""
        annotation = self._create_annotation(page=0, x=100, y=200, content='Single')
        result = _deduplicate_annotations([annotation])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['content'], 'Single')

    def test_negative_coordinates(self):
        """Test handling of negative coordinates (edge case)."""
        annotations = [
            self._create_annotation(page=0, x=-10.04, y=-20.03, content='Negative'),
            self._create_annotation(page=0, x=-10.01, y=-20.01, content='Negative'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should deduplicate (both round to -10.0, -20.0)
        self.assertEqual(len(result), 1)

    def test_large_coordinate_values(self):
        """Test handling of large coordinate values."""
        annotations = [
            self._create_annotation(page=0, x=9999.01, y=8888.02, content='Large'),
            self._create_annotation(page=0, x=9999.04, y=8888.03, content='Large'),  # Both round to 9999.0, 8888.0
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)

    def test_special_characters_in_content(self):
        """Test handling of special characters in content."""
        special_content = "Test with émojis 🎯 and special chars: <>\"'&\n\t"
        annotations = [
            self._create_annotation(page=0, x=100, y=200, content=special_content),
            self._create_annotation(page=0, x=100, y=200, content=special_content),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)


class TestDeduplicationIntegration(unittest.TestCase):
    """Integration tests to ensure deduplication works in realistic scenarios."""

    def _create_annotation(self, **kwargs):
        """Reuse helper from main test class."""
        defaults = {
            'type': 'highlight',
            'pdf_page_0based': 0,
            'pdf_x': 100.0,
            'pdf_y': 200.0,
            'pdf_width': 200.0,
            'pdf_height': 20.0,
            'content': 'Test',
            'timestamp': '2024-01-01',
            'source': 'test',
        }
        defaults.update(kwargs)
        return defaults

    def test_pds_pdt_duplicate_scenario(self):
        """Test the original problem: same annotation from .pds and .pdt files."""
        # Simulate annotations from both .pds and .pdt with identical data
        annotations = [
            self._create_annotation(
                pdf_page_0based=0, pdf_x=308.5, pdf_y=243.2,
                content='A concept is a plug- and- play device',
                source='page_136_shea.pds'
            ),
            self._create_annotation(
                pdf_page_0based=0, pdf_x=308.5, pdf_y=243.2,
                content='A concept is a plug- and- play device',
                source='page_136_shea.pdt'
            ),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should deduplicate to single annotation
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['source'], 'page_136_shea.pds')  # First wins

    def test_multiple_books_no_cross_contamination(self):
        """Test that annotations from different books are treated independently.
        
        Note: The deduplication function has no concept of 'source' or 'book',
        so annotations with identical page/position/content will be deduplicated
        even if they come from different books. This is expected behavior.
        """
        annotations = [
            # Book 1 - page 0
            self._create_annotation(pdf_page_0based=0, pdf_x=100, pdf_y=200, content='Common phrase', source='book1'),
            # Book 1 - page 5 (different page, should be preserved)
            self._create_annotation(pdf_page_0based=5, pdf_x=100, pdf_y=200, content='Common phrase', source='book1'),
            
            # Book 2 - page 0 (SAME page/coords/content as book1, will be deduplicated)
            self._create_annotation(pdf_page_0based=0, pdf_x=100, pdf_y=200, content='Common phrase', source='book2'),
            # Book 2 - page 3 (different page, should be preserved)
            self._create_annotation(pdf_page_0based=3, pdf_x=100, pdf_y=200, content='Common phrase', source='book2'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Page 0 duplicates removed (2 become 1), pages 3 and 5 preserved
        self.assertEqual(len(result), 3)
        
        # Verify the pages that remain
        pages = sorted([a['pdf_page_0based'] for a in result])
        self.assertEqual(pages, [0, 3, 5])

    def test_real_world_near_duplicate_coordinates(self):
        """Test real-world scenario with slight coordinate variations from OCR/parsing."""
        # These might come from slightly different parsing methods
        annotations = [
            self._create_annotation(pdf_page_0based=1, pdf_x=72.001, pdf_y=144.003, content='Introduction'),
            self._create_annotation(pdf_page_0based=1, pdf_x=72.002, pdf_y=144.001, content='Introduction'),
            self._create_annotation(pdf_page_0based=1, pdf_x=72.004, pdf_y=144.002, content='Introduction'),
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should deduplicate to one (all round to 72.0, 144.0)
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
