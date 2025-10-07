"""
Strict unit tests for note/highlight unification with PDF rendering validation.

Tests verify:
1. Notes unify with highlights at START or END positions
2. Unified notes have highlight_content field populated
3. Unified notes render as highlights (not note icons) in PDF
4. Regular highlights have NO content in PDF
5. Unified notes have note content in PDF
6. highlight_content passes through the adapter
"""

import unittest
import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fitz
from kindle_parser.amazon_coordinate_system import (
    _deduplicate_annotations,
    create_amazon_compliant_annotations
)
from pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from pdf_processor.pdf_annotator import annotate_pdf_file


class TestUnifiedNoteRendering(unittest.TestCase):
    """Strict tests for unified note rendering behavior"""
    
    def setUp(self):
        """Set up test data"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temp files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_note_unifies_at_highlight_start_position(self):
        """Note positioned at highlight START should unify"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_x_end': 150.0,
                'pdf_y_end': 200.0,
                'content': 'highlighted text',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,  # At START
                'pdf_y': 200.0,
                'content': 'my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should unify to 1 annotation
        self.assertEqual(len(result), 1, "Note at highlight START should unify")
        self.assertEqual(result[0]['type'], 'note')
        self.assertEqual(result[0]['content'], 'my note')
        # CRITICAL: Must have highlight_content field
        self.assertIn('highlight_content', result[0], 
                     "Unified note MUST have highlight_content field")
        self.assertEqual(result[0]['highlight_content'], 'highlighted text')
    
    def test_note_unifies_at_highlight_end_position(self):
        """Note positioned at highlight END should unify (Kindle adds notes at end)"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_x_end': 150.0,
                'pdf_y_end': 210.0,
                'content': 'highlighted text',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 150.0,  # At END
                'pdf_y': 210.0,
                'content': 'my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should unify to 1 annotation
        self.assertEqual(len(result), 1, "Note at highlight END should unify")
        self.assertEqual(result[0]['type'], 'note')
        self.assertEqual(result[0]['content'], 'my note')
        # CRITICAL: Must have highlight_content field
        self.assertIn('highlight_content', result[0],
                     "Unified note MUST have highlight_content field")
        self.assertEqual(result[0]['highlight_content'], 'highlighted text')
    
    def test_note_between_start_and_end_does_not_unify(self):
        """Note in middle of highlight (not at start/end) should NOT unify"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_x_end': 200.0,
                'pdf_y_end': 200.0,
                'content': 'highlighted text',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 150.0,  # In MIDDLE, not at start (100) or end (200)
                'pdf_y': 200.0,
                'content': 'my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should remain separate
        self.assertEqual(len(result), 2, 
                        "Note in middle (not at start/end) should NOT unify")
    
    def test_position_tolerance_within_5pt(self):
        """Notes within 5pt of highlight start/end should unify"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_x_end': 150.0,
                'pdf_y_end': 200.0,
                'content': 'highlighted text',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 103.0,  # 3pt away from start (within 5pt tolerance)
                'pdf_y': 202.0,  # 2pt away (within tolerance)
                'content': 'my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should unify within tolerance
        self.assertEqual(len(result), 1, 
                        "Note within 5pt tolerance should unify")
        self.assertIn('highlight_content', result[0])
    
    def test_position_tolerance_beyond_5pt_does_not_unify(self):
        """Notes beyond 5pt of highlight start/end should NOT unify"""
        annotations = [
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_x_end': 150.0,
                'pdf_y_end': 200.0,
                'content': 'highlighted text',
                'timestamp': '2024-01-01 10:00:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 107.0,  # 7pt away from start (beyond 5pt tolerance)
                'pdf_y': 200.0,
                'content': 'my note',
                'timestamp': '2024-01-01 10:01:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should NOT unify beyond tolerance
        self.assertEqual(len(result), 2,
                        "Note beyond 5pt tolerance should NOT unify")
    
    def test_highlight_content_passes_through_adapter(self):
        """Adapter must pass through highlight_content field"""
        amazon_annotations = [
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_width': 50.0,
                'pdf_height': 10.0,
                'content': 'my note text',
                'highlight_content': 'the highlighted text',  # Must be preserved
                'start_position': '0 0 0 0 100 200 50 10',
                'end_position': '0 0 0 0 150 200 50 10',
                'timestamp': '2024-01-01 10:00:00',
            }
        ]
        
        pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
        
        # CRITICAL: highlight_content must pass through
        self.assertEqual(len(pdf_annotations), 1)
        self.assertIn('highlight_content', pdf_annotations[0],
                     "Adapter MUST pass through highlight_content field")
        self.assertEqual(pdf_annotations[0]['highlight_content'], 
                        'the highlighted text')
    
    def test_unified_note_converts_to_highlight_type(self):
        """Unified notes (with highlight_content) should convert to highlight type"""
        pdf_annotations = [
            {
                'type': 'note',
                'page_number': 0,
                'content': 'my note',
                'highlight_content': 'highlighted text',  # This makes it unified
                'coordinates': [100, 200, 150, 210],
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_width': 50.0,
                'pdf_height': 10.0,
            }
        ]
        
        # Create a temp PDF to test rendering
        doc = fitz.open()  # Empty PDF
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 200), "test text")
        
        temp_pdf = os.path.join(self.temp_dir, "test_unified.pdf")
        doc.save(temp_pdf)
        doc.close()
        
        # Add annotation using annotate_pdf_file
        output_pdf = os.path.join(self.temp_dir, "test_unified_output.pdf")
        success = annotate_pdf_file(temp_pdf, pdf_annotations, output_pdf)
        self.assertTrue(success, "PDF annotation should succeed")
        
        # VERIFY: Annotation should be Highlight type, not Text/FreeText
        result_doc = fitz.open(output_pdf)
        result_page = result_doc[0]
        annots = list(result_page.annots())
        
        self.assertEqual(len(annots), 1, "Should have 1 annotation")
        self.assertEqual(annots[0].type[1], 'Highlight',
                        "Unified note MUST render as Highlight, not Text")
        
        # VERIFY: Should have content (the note text)
        info = annots[0].info
        self.assertEqual(info.get('content', ''), 'my note',
                        "Unified note MUST have note content in PDF")
        self.assertEqual(info.get('title', ''), 'Kindle Note',
                        "Unified note should have 'Kindle Note' title")
        
        result_doc.close()
    
    def test_regular_highlight_has_no_content(self):
        """Regular highlights (no highlight_content field) should have NO content"""
        pdf_annotations = [
            {
                'type': 'highlight',
                'page_number': 0,
                'content': 'some highlight text',  # This should NOT appear in PDF
                'coordinates': [100, 200, 150, 210],
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_width': 50.0,
                'pdf_height': 10.0,
                # NO highlight_content field = regular highlight
            }
        ]
        
        # Create a temp PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 200), "test text")
        
        temp_pdf = os.path.join(self.temp_dir, "test_regular.pdf")
        doc.save(temp_pdf)
        doc.close()
        
        # Add annotation
        output_pdf = os.path.join(self.temp_dir, "test_regular_output.pdf")
        success = annotate_pdf_file(temp_pdf, pdf_annotations, output_pdf)
        self.assertTrue(success, "PDF annotation should succeed")
        
        # VERIFY: Regular highlight should have NO content
        result_doc = fitz.open(output_pdf)
        result_page = result_doc[0]
        annots = list(result_page.annots())
        
        self.assertEqual(len(annots), 1)
        self.assertEqual(annots[0].type[1], 'Highlight')
        
        info = annots[0].info
        content = info.get('content', '')
        self.assertEqual(content, '',
                        "Regular highlight MUST have empty content")
        self.assertEqual(info.get('title', ''), 'Kindle Highlight',
                        "Regular highlight should have 'Kindle Highlight' title")
        
        result_doc.close()
    
    def test_standalone_note_renders_as_note_icon(self):
        """Standalone notes (no highlight_content) should render as note icons"""
        pdf_annotations = [
            {
                'type': 'note',
                'page_number': 0,
                'content': 'standalone note',
                # NO highlight_content field = standalone note
                'coordinates': [100, 200, 110, 210],
                'pdf_x': 100.0,
                'pdf_y': 200.0,
            }
        ]
        
        # Create a temp PDF
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 200), "test text")
        
        temp_pdf = os.path.join(self.temp_dir, "test_standalone.pdf")
        doc.save(temp_pdf)
        doc.close()
        
        # Add annotation
        output_pdf = os.path.join(self.temp_dir, "test_standalone_output.pdf")
        success = annotate_pdf_file(temp_pdf, pdf_annotations, output_pdf)
        self.assertTrue(success, "PDF annotation should succeed")
        
        # VERIFY: Standalone note should be Text type (note icon)
        result_doc = fitz.open(output_pdf)
        result_page = result_doc[0]
        annots = list(result_page.annots())
        
        self.assertEqual(len(annots), 1)
        self.assertEqual(annots[0].type[1], 'Text',
                        "Standalone note should render as Text (note icon)")
        
        info = annots[0].info
        self.assertEqual(info.get('content', ''), 'standalone note',
                        "Standalone note should have its content")
        
        result_doc.close()
    
    def test_multiple_highlights_same_page_unify_by_y_position(self):
        """
        When multiple highlights exist on same page, notes should unify based on Y-position.
        
        This tests the logic that matches notes to highlights by position, ensuring notes
        unify with the spatially closest highlight.
        """
        # Simulate 3 highlights on page 0, at different Y positions
        annotations = [
            # First highlight (top) - y=100
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 50.0,
                'pdf_y': 100.0,
                'pdf_x_end': 200.0,
                'pdf_y_end': 115.0,
                'pdf_width': 150.0,
                'pdf_height': 15.0,
                'content': 'first highlight text',
            },
            # Second highlight (middle) - y=200
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 50.0,
                'pdf_y': 200.0,
                'pdf_x_end': 200.0,
                'pdf_y_end': 215.0,
                'pdf_width': 150.0,
                'pdf_height': 15.0,
                'content': 'second highlight text',
            },
            # Third highlight (bottom) - y=300
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 50.0,
                'pdf_y': 300.0,
                'pdf_x_end': 200.0,
                'pdf_y_end': 315.0,
                'pdf_width': 150.0,
                'pdf_height': 15.0,
                'content': 'third highlight text',
            },
            # Note near the END of second highlight (middle)
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 200.0,  # At end X of second highlight
                'pdf_y': 215.0,  # At end Y of second highlight
                'content': 'note for middle highlight',
            },
        ]
        
        deduplicated = _deduplicate_annotations(annotations)
        
        # Should unify: 3 highlights + 1 note -> 2 highlights + 1 unified note
        self.assertEqual(len(deduplicated), 3,
                        "Should have 3 annotations after unification")
        
        # Find the unified note
        notes = [a for a in deduplicated if a['type'] == 'note']
        self.assertEqual(len(notes), 1, "Should have 1 note")
        
        note = notes[0]
        
        # CRITICAL: Note should be unified with second highlight, NOT first or third
        self.assertIn('highlight_content', note,
                     "Note should have highlight_content (unified)")
        self.assertEqual(note['highlight_content'], 'second highlight text',
                        "Note should unify with second highlight at y=200 (not first at y=100 or third at y=300)")
        
        # Verify the other two highlights still exist separately
        highlights = [a for a in deduplicated if a['type'] == 'highlight']
        self.assertEqual(len(highlights), 2, "Should have 2 separate highlights")
        
        highlight_contents = [h['content'] for h in highlights]
        self.assertIn('first highlight text', highlight_contents)
        self.assertIn('third highlight text', highlight_contents)
    
    def test_multiple_annotations_mixed_types(self):
        """Test mixed regular highlights, unified notes, and standalone notes"""
        annotations = [
            # Regular highlight
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 100.0,
                'pdf_x_end': 150.0,
                'pdf_y_end': 100.0,
                'content': 'highlight 1',
                'timestamp': '2024-01-01 10:00:00',
            },
            # Unified note (at highlight start)
            {
                'type': 'highlight',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 200.0,
                'pdf_x_end': 150.0,
                'pdf_y_end': 200.0,
                'content': 'highlight 2',
                'timestamp': '2024-01-01 10:01:00',
            },
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,  # Unifies with highlight 2
                'pdf_y': 200.0,
                'content': 'note for highlight 2',
                'timestamp': '2024-01-01 10:02:00',
            },
            # Standalone note
            {
                'type': 'note',
                'pdf_page_0based': 0,
                'pdf_x': 100.0,
                'pdf_y': 300.0,
                'content': 'standalone note',
                'timestamp': '2024-01-01 10:03:00',
            },
        ]
        
        result = _deduplicate_annotations(annotations)
        
        # Should have 3 annotations: 1 regular highlight, 1 unified note, 1 standalone note
        self.assertEqual(len(result), 3)
        
        # Count types
        highlights = [a for a in result if a['type'] == 'highlight']
        notes = [a for a in result if a['type'] == 'note']
        
        self.assertEqual(len(highlights), 1, "Should have 1 regular highlight")
        self.assertEqual(len(notes), 2, "Should have 2 notes (1 unified, 1 standalone)")
        
        # Check unified note has highlight_content
        unified_notes = [n for n in notes if 'highlight_content' in n]
        standalone_notes = [n for n in notes if 'highlight_content' not in n]
        
        self.assertEqual(len(unified_notes), 1, "Should have 1 unified note")
        self.assertEqual(len(standalone_notes), 1, "Should have 1 standalone note")
        
        # Verify unified note content
        unified = unified_notes[0]
        self.assertEqual(unified['content'], 'note for highlight 2')
        self.assertEqual(unified['highlight_content'], 'highlight 2')


class TestPeirceUnification(unittest.TestCase):
    """Integration test with real Peirce data"""
    
    def test_peirce_unification_produces_correct_counts(self):
        """Peirce example should unify 2 notes with highlights"""
        krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
        clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
        book_name = 'peirce-charles-fixation-belief'
        
        # Skip if files don't exist
        if not os.path.exists(krds_file) or not os.path.exists(clippings_file):
            self.skipTest("Peirce example files not found")
        
        annotations = create_amazon_compliant_annotations(
            krds_file, clippings_file, book_name
        )
        
        # Should have 10 total (12 original - 2 unified)
        self.assertEqual(len(annotations), 10,
                        "Peirce should have 10 annotations after unification")
        
        # Count types
        highlights = [a for a in annotations if a['type'] == 'highlight']
        notes = [a for a in annotations if a['type'] == 'note']
        bookmarks = [a for a in annotations if a['type'] == 'bookmark']
        
        self.assertEqual(len(highlights), 6, "Should have 6 regular highlights")
        self.assertEqual(len(notes), 2, "Should have 2 unified notes")
        self.assertEqual(len(bookmarks), 2, "Should have 2 bookmarks")
        
        # CRITICAL: Both notes must have highlight_content
        for note in notes:
            self.assertIn('highlight_content', note,
                         f"Note on page {note['pdf_page_0based']} missing highlight_content")
            self.assertTrue(note['highlight_content'].strip(),
                          f"Note on page {note['pdf_page_0based']} has empty highlight_content")
    
    def test_peirce_note_matches_correct_highlight_by_position(self):
        """
        Regression test: Verify note on page 4 is unified with correct highlight.
        
        The note "Note for a paragraph and one word more" should be unified with
        "We generally know..." (which comes BEFORE it in reading order), NOT with
        "The Assassins..." (which comes AFTER it).
        
        This tests that the PRE-STEP correctly matches clippings to KRDS highlights
        by Y-position ordering, not just by appearance order.
        """
        krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
        clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
        book_name = 'peirce-charles-fixation-belief'
        
        # Skip if files don't exist
        if not os.path.exists(krds_file) or not os.path.exists(clippings_file):
            self.skipTest("Peirce example files not found")
        
        annotations = create_amazon_compliant_annotations(
            krds_file, clippings_file, book_name
        )
        
        # Find the note on page 3 (0-based) / page 4 (1-based)
        notes_on_page_3 = [a for a in annotations 
                          if a['type'] == 'note' and a['pdf_page_0based'] == 3]
        
        # Should have exactly 1 note on page 3
        self.assertEqual(len(notes_on_page_3), 1,
                        "Should have exactly 1 note on page 4 of Peirce PDF")
        
        note = notes_on_page_3[0]
        
        # Verify it's the correct note
        self.assertIn('Note for a paragraph', note['content'],
                     f"Expected note 'Note for a paragraph...', got: {note['content'][:50]}")
        
        # CRITICAL: The note must be unified with "We generally know..." NOT "The Assassins..."
        self.assertIn('highlight_content', note,
                     "Note should have highlight_content (unified with highlight)")
        
        highlight_content = note['highlight_content']
        self.assertIn('We generally know', highlight_content,
                     f"Note should be unified with 'We generally know...' but got: {highlight_content[:50]}")
        self.assertNotIn('Assassins', highlight_content,
                        f"Note should NOT be unified with 'Assassins...' but got: {highlight_content[:50]}")
        
        # Also verify that "The Assassins..." exists as a separate highlight on the same page
        highlights_on_page_3 = [a for a in annotations 
                               if a['type'] == 'highlight' and a['pdf_page_0based'] == 3]
        
        assassins_highlights = [h for h in highlights_on_page_3 
                               if 'Assassins' in h.get('content', '')]
        
        self.assertEqual(len(assassins_highlights), 1,
                        "'The Assassins...' should exist as a separate highlight")


if __name__ == '__main__':
    unittest.main()
