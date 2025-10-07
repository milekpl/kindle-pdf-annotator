"""
Unit tests for note and highlight unification.

Tests that notes with the same coordinates as highlights are unified into a single
annotation rather than creating duplicates.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kindle_parser.amazon_coordinate_system import _deduplicate_annotations


class TestNoteHighlightUnification(unittest.TestCase):
    """Test unification of notes and highlights with matching coordinates"""
    
    def test_note_and_highlight_same_position_unified(self):
        """Notes and highlights at same position should be unified"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'This is my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have only 1 annotation (unified)
        self.assertEqual(len(result), 1)
        # Should keep the note type (has content)
        self.assertEqual(result[0]['type'], 'note')
        # Should keep the note content
        self.assertEqual(result[0]['content'], 'This is my note')
    
    def test_note_and_highlight_different_position_kept_separate(self):
        """Notes and highlights at different positions should remain separate"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 150.0,  # Different X
                'pdf_y': 200.0,
                'content': 'This is my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have 2 annotations (separate)
        self.assertEqual(len(result), 2)
    
    def test_note_and_highlight_different_page_kept_separate(self):
        """Notes and highlights on different pages should remain separate"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 1,  # Different page
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'This is my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have 2 annotations (separate)
        self.assertEqual(len(result), 2)
    
    def test_multiple_notes_same_highlight_position(self):
        """Multiple notes at same highlight position should be unified"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'First note',
                'timestamp': '2024-01-01 10:01:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'Second note',
                'timestamp': '2024-01-01 10:02:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have only 1 annotation (all unified)
        self.assertEqual(len(result), 1)
        # Should be a note type
        self.assertEqual(result[0]['type'], 'note')
    
    def test_note_without_highlight_preserved(self):
        """Notes without matching highlights should be preserved"""
        annotations = [
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'Standalone note',
                'timestamp': '2024-01-01 10:00:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have 1 annotation
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'note')
        self.assertEqual(result[0]['content'], 'Standalone note')
    
    def test_highlight_without_note_preserved(self):
        """Highlights without matching notes should be preserved"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have 1 annotation
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'highlight')
    
    def test_near_coordinates_unified(self):
        """Notes and highlights with coordinates within rounding threshold should unify"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.04,  # Rounds to 100.0
                'pdf_y': 200.03,  # Rounds to 200.0
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.06,  # Rounds to 100.1
                'pdf_y': 199.97,  # Rounds to 200.0
                'content': 'Close note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should unify if within rounding threshold (0.1 pt precision)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'note')
    
    def test_unification_preserves_note_content(self):
        """When unifying, note content should be preserved over empty highlight content"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',  # Empty content
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'Important note text',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        self.assertEqual(len(result), 1)
        # Content should be from the note, not empty
        self.assertEqual(result[0]['content'], 'Important note text')
    
    def test_mixed_annotations_with_unification(self):
        """Complex case with multiple highlights, notes, and bookmarks"""
        annotations = [
            # Page 0 - unified group
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': '',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'content': 'Note 1',
                'timestamp': '2024-01-01 10:01:00',
            },
            # Page 0 - separate highlight
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 150.0,
                'pdf_y': 300.0,
                'content': '',
                'timestamp': '2024-01-01 10:02:00',
            },
            # Page 1 - bookmark (should not unify with anything)
            {
                'type': 'bookmark',
                'pdf_page_0based': 1,
                'pdf_x': 0.0,
                'pdf_y': 0.0,
                'content': '',
                'timestamp': '2024-01-01 10:03:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have 3 annotations: 1 unified note, 1 highlight, 1 bookmark
        self.assertEqual(len(result), 3)
        
        # Check types
        types = [ann['type'] for ann in result]
        self.assertIn('note', types)
        self.assertIn('highlight', types)
        self.assertIn('bookmark', types)


if __name__ == '__main__':
    unittest.main()
