"""
Test KRDS Parser - Unit tests for the Kindle Reader Data Store parser
"""

import unittest
import tempfile
import json
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kindle_parser.krds_parser import (
    KindlePosition, KindleAnnotation, KindleReaderDataStore, 
    parse_krds_file, find_krds_files
)


class TestKindlePosition(unittest.TestCase):
    """Test Kindle position parsing"""
    
    def test_valid_position_parsing(self):
        """Test parsing valid position string"""
        pos = KindlePosition("15 0 1020 1 377 517 44 14")
        
        self.assertTrue(pos.valid)
        self.assertEqual(pos.page, 15)
        self.assertEqual(pos.x, 377)
        self.assertEqual(pos.y, 517)
        self.assertEqual(pos.width, 44)
        self.assertEqual(pos.height, 14)
    
    def test_invalid_position_parsing(self):
        """Test parsing invalid position string"""
        pos = KindlePosition("invalid")
        
        self.assertFalse(pos.valid)
        self.assertEqual(pos.page, 0)
        self.assertEqual(pos.x, 0)
        self.assertEqual(pos.y, 0)
    
    def test_empty_position(self):
        """Test empty position string"""
        pos = KindlePosition("")
        
        self.assertFalse(pos.valid)
        self.assertEqual(pos.page, 0)
    
    def test_pdf_rect_conversion(self):
        """Test conversion to PDF rectangle"""
        pos = KindlePosition("15 0 1020 1 377 517 44 14")
        rect = pos.to_pdf_rect()
        
        self.assertEqual(rect, [377.0, 517.0, 421.0, 531.0])


class TestKindleAnnotation(unittest.TestCase):
    """Test Kindle annotation parsing"""
    
    def test_highlight_annotation(self):
        """Test parsing highlight annotation"""
        data = {
            "startPosition": "15 0 1020 1 377 517 44 14",
            "endPosition": "15 0 1020 1 377 517 44 14", 
            "creationTime": "2025-09-10T13:45:45.762000",
            "lastModificationTime": "2025-09-10T13:45:45.762000",
            "template": "0\ufffc0"
        }
        
        annotation = KindleAnnotation("annotation.personal.highlight", data)
        
        self.assertEqual(annotation.type, "annotation.personal.highlight")
        self.assertEqual(annotation.category, "highlight")
        self.assertEqual(annotation.start_position.page, 15)
        self.assertEqual(annotation.note_text, "")
    
    def test_note_annotation(self):
        """Test parsing note annotation"""
        data = {
            "startPosition": "23 0 1348 1 329 524 59 14",
            "endPosition": "23 0 1348 1 329 524 59 14",
            "creationTime": "2025-09-24T07:59:47.924000", 
            "lastModificationTime": "2025-09-24T07:59:47.924000",
            "template": "0\ufffc0",
            "note": "Citation"
        }
        
        annotation = KindleAnnotation("annotation.personal.note", data)
        
        self.assertEqual(annotation.category, "note")
        self.assertEqual(annotation.note_text, "Citation")
        self.assertEqual(annotation.start_position.page, 23)
    
    def test_annotation_to_dict(self):
        """Test annotation serialization"""
        data = {
            "startPosition": "15 0 1020 1 377 517 44 14",
            "endPosition": "15 0 1020 1 377 517 44 14",
            "creationTime": "2025-09-10T13:45:45.762000",
            "lastModificationTime": "2025-09-10T13:45:45.762000",
            "template": "0\ufffc0"
        }
        
        annotation = KindleAnnotation("annotation.personal.highlight", data)
        result = annotation.to_dict()
        
        self.assertEqual(result["page_number"], 15)
        self.assertEqual(result["category"], "highlight")
        self.assertEqual(result["coordinates"], [377.0, 517.0, 421.0, 531.0])
        self.assertTrue(result["valid_position"])


class TestKRDSIntegration(unittest.TestCase):
    """Integration tests with real KRDS data"""
    
    def setUp(self):
        """Set up test with real sample data"""
        # Path to the real PDS file in examples
        self.sample_pds = Path(__file__).parent.parent / "examples" / "sample_data" / \
                         "peirce-charles-fixation-belief.sdr" / \
                         "peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds"
        
        self.sample_json = self.sample_pds.with_suffix(".pds.json")
        
    def test_parse_real_krds_file(self):
        """Test parsing real KRDS file"""
        if not self.sample_pds.exists():
            self.skipTest("Sample PDS file not found")
        
        annotations = parse_krds_file(str(self.sample_pds))
        
        # Should have annotations
        self.assertGreater(len(annotations), 0, "Should find annotations in sample file")
        
        # Check that annotations are on different pages
        pages = [a.start_position.page for a in annotations if a.start_position.valid]
        unique_pages = set(pages)
        
        self.assertGreater(len(unique_pages), 1, "Annotations should be on multiple pages")
        # Allow page 0 as it can be valid (e.g., cover page, title page)
        for page in unique_pages:
            self.assertGreaterEqual(page, 0, f"Page should be >= 0, got {page}")
            self.assertLess(page, 1000, f"Page should be < 1000, got {page}")
        
        # Should have both highlights and notes
        categories = [a.category for a in annotations]
        self.assertIn("highlight", categories, "Should have highlights")
        self.assertIn("note", categories, "Should have notes")
    
    def test_page_distribution(self):
        """Test that annotations are properly distributed across pages"""
        if not self.sample_pds.exists():
            self.skipTest("Sample PDS file not found")
        
        annotations = parse_krds_file(str(self.sample_pds))
        valid_annotations = [a for a in annotations if a.start_position.valid]
        
        # All valid annotations should have reasonable page numbers
        for annotation in valid_annotations:
            self.assertGreaterEqual(annotation.start_position.page, 0, 
                             f"Page should be >= 0, got {annotation.start_position.page}")
            self.assertLess(annotation.start_position.page, 1000,
                           f"Page should be < 1000, got {annotation.start_position.page}")
    
    def test_coordinate_validity(self):
        """Test that annotations have valid coordinates"""
        if not self.sample_pds.exists():
            self.skipTest("Sample PDS file not found")
        
        annotations = parse_krds_file(str(self.sample_pds))
        valid_annotations = [a for a in annotations if a.start_position.valid]
        
        for annotation in valid_annotations:
            # Coordinates should be reasonable
            self.assertGreaterEqual(annotation.start_position.x, 0)
            self.assertGreaterEqual(annotation.start_position.y, 0)
            
            # Width and height requirements depend on annotation type
            if 'bookmark' in annotation.annotation_type:
                # Bookmarks may have zero width/height as they're point locations
                self.assertGreaterEqual(annotation.start_position.width, 0)
                self.assertGreaterEqual(annotation.start_position.height, 0)
            else:
                # Highlights and notes should have positive dimensions
                self.assertGreater(annotation.start_position.width, 0)
                self.assertGreater(annotation.start_position.height, 0)
            
            # PDF rect should be valid
            rect = annotation.start_position.to_pdf_rect()
            self.assertEqual(len(rect), 4)
            self.assertLessEqual(rect[0], rect[2])  # x1 <= x2
            self.assertLessEqual(rect[1], rect[3])  # y1 <= y2
    
    def test_comparison_with_json(self):
        """Test that parsed data matches the JSON reference"""
        if not self.sample_pds.exists() or not self.sample_json.exists():
            self.skipTest("Sample files not found")
        
        # Parse KRDS file
        annotations = parse_krds_file(str(self.sample_pds))
        
        # Load JSON reference
        with open(self.sample_json, 'r') as f:
            json_data = json.load(f)
        
        # Compare highlights count
        if "annotation.cache.object" in json_data:
            cache = json_data["annotation.cache.object"]
            
            json_highlights = cache.get("annotation.personal.highlight", [])
            json_notes = cache.get("annotation.personal.note", [])
            
            parsed_highlights = [a for a in annotations if a.category == "highlight"]
            parsed_notes = [a for a in annotations if a.category == "note"]
            
            self.assertEqual(len(parsed_highlights), len(json_highlights),
                           "Highlight count should match JSON reference")
            self.assertEqual(len(parsed_notes), len(json_notes),
                           "Note count should match JSON reference")
            
            # Check that we have matching positions (order might differ)
            if json_highlights and parsed_highlights:
                json_positions = set(h["startPosition"] for h in json_highlights)
                parsed_positions = set(h.start_position.raw for h in parsed_highlights)
                
                # Find common positions
                common_positions = json_positions.intersection(parsed_positions)
                self.assertGreater(len(common_positions), 0,
                                 "Should have some matching positions between JSON and parsed data")


class TestFindKRDSFiles(unittest.TestCase):
    """Test KRDS file discovery"""
    
    def test_find_files_in_sample_data(self):
        """Test finding KRDS files in sample data"""
        sample_dir = Path(__file__).parent.parent / "examples" / "sample_data"
        
        if not sample_dir.exists():
            self.skipTest("Sample data directory not found")
        
        files = find_krds_files(str(sample_dir), "peirce-charles-fixation-belief")
        
        # Should find at least one file (we have Peirce sample data)
        self.assertGreater(len(files), 0, "Should find KRDS files")
        
        # All found files should exist and be .pds or .pdt
        for file in files:
            self.assertTrue(file.exists(), f"File should exist: {file}")
            self.assertIn(file.suffix, ['.pds', '.pdt'], 
                         f"Should be .pds or .pdt file: {file}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)