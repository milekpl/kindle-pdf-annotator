"""
Test Parsers - Unit tests for Kindle parsers
"""

import unittest
import tempfile
import json
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kindle_parser.pds_parser import PDSParser, parse_pds_file
from kindle_parser.clippings_parser import ClippingsParser, parse_clippings_file


class TestPDSParser(unittest.TestCase):
    """Test PDS file parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_pds_parser_init(self):
        """Test PDS parser initialization"""
        test_file = self.temp_path / "test.pds"
        parser = PDSParser(str(test_file))
        
        self.assertEqual(parser.file_path, test_file)
        self.assertEqual(parser.metadata, {})
        self.assertEqual(parser.annotations, [])
    
    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file"""
        parser = PDSParser("nonexistent.pds")
        result = parser.parse()
        
        self.assertIn("error", result)
        self.assertIn("metadata", result)
        self.assertIn("annotations", result)
    
    def test_parse_empty_file(self):
        """Test parsing empty file"""
        test_file = self.temp_path / "empty.pds"
        test_file.write_bytes(b"")
        
        parser = PDSParser(str(test_file))
        result = parser.parse()
        
        self.assertIn("error", result)
    
    def test_convenience_function(self):
        """Test convenience function"""
        test_file = self.temp_path / "test.pds"
        test_file.write_bytes(b"test data")
        
        result = parse_pds_file(str(test_file))
        self.assertIsInstance(result, dict)


class TestClippingsParser(unittest.TestCase):
    """Test MyClippings.txt parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Sample MyClippings.txt content with multiple books and types
        self.sample_clippings = """Test Book (Test Author)
- Your Highlight on Location 123-124 | Added on Monday, January 1, 2024 12:00:00 PM

This is a sample highlight from the book.
==========
Test Book (Test Author)
- Your Note on Location 125 | Added on Monday, January 1, 2024 12:05:00 PM

This is a sample note.
==========
Another Book (Another Author)
- Your Bookmark on Page 45 | Added on Tuesday, January 2, 2024 3:30:00 PM

==========
Third Book (Third Author)
- Your Highlight on Location 200-205 | Added on Wednesday, January 3, 2024 10:15:00 AM

This is another highlight from a different book.
==========
Another Book (Another Author)
- Your Note on Page 50 | Added on Tuesday, January 2, 2024 4:00:00 PM

A note in the second book.
=========="""
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_clippings_parser_init(self):
        """Test clippings parser initialization"""
        test_file = self.temp_path / "MyClippings.txt"
        parser = ClippingsParser(str(test_file))
        
        self.assertEqual(parser.file_path, test_file)
        self.assertEqual(parser.clippings, [])
    
    def test_parse_sample_clippings(self):
        """Test parsing sample clippings"""
        test_file = self.temp_path / "MyClippings.txt"
        test_file.write_text(self.sample_clippings, encoding='utf-8')
        
        parser = ClippingsParser(str(test_file))
        result = parser.parse()
        
        self.assertIsInstance(result, dict)
        self.assertIn("clippings", result)
        self.assertIn("books", result)
        self.assertIn("total_clippings", result)
        self.assertIn("total_books", result)
        
        # Should have parsed clippings
        self.assertGreater(result["total_clippings"], 0)
        self.assertGreater(result["total_books"], 0)
    
    def test_parse_title_author(self):
        """Test title and author parsing"""
        test_file = self.temp_path / "MyClippings.txt"
        test_file.write_text(self.sample_clippings, encoding='utf-8')
        
        parser = ClippingsParser(str(test_file))
        result = parser.parse()
        
        # Check if titles and authors are parsed correctly
        books = result["books"]
        self.assertIn("Test Book", books)
        self.assertIn("Another Book", books)
        self.assertIn("Third Book", books)
        
        # Check specific book content
        test_book = books["Test Book"]
        self.assertEqual(test_book["author"], "Test Author")
        self.assertEqual(len(test_book["clippings"]), 2)  # 1 highlight + 1 note
        
        another_book = books["Another Book"]
        self.assertEqual(another_book["author"], "Another Author")
        self.assertEqual(len(another_book["clippings"]), 2)  # 1 bookmark + 1 note
        
        third_book = books["Third Book"]
        self.assertEqual(third_book["author"], "Third Author")
        self.assertEqual(len(third_book["clippings"]), 1)  # 1 highlight
    
    def test_parse_empty_file(self):
        """Test parsing empty file"""
        test_file = self.temp_path / "empty.txt"
        test_file.write_text("", encoding='utf-8')
        
        parser = ClippingsParser(str(test_file))
        result = parser.parse()
        
        self.assertEqual(result["total_clippings"], 0)
        self.assertEqual(result["total_books"], 0)
    
    def test_parse_malformed_clipping(self):
        """Test parsing malformed clipping"""
        malformed = "Just a line without proper format\n=========="
        
        test_file = self.temp_path / "malformed.txt"
        test_file.write_text(malformed, encoding='utf-8')
        
        parser = ClippingsParser(str(test_file))
        result = parser.parse()
        
        # Should handle malformed input gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("clippings", result)
    
    def test_convenience_function(self):
        """Test convenience function"""
        test_file = self.temp_path / "MyClippings.txt"
        test_file.write_text(self.sample_clippings, encoding='utf-8')
        
        result = parse_clippings_file(str(test_file))
        self.assertIsInstance(result, dict)
        self.assertGreater(result["total_clippings"], 0)


class TestParserIntegration(unittest.TestCase):
    """Integration tests for parsers"""
    
    def test_all_parsers_return_dict(self):
        """Test that all parsers return dictionaries"""
        with tempfile.NamedTemporaryFile(suffix='.pds', delete=False) as f:
            f.write(b"test")
            pds_result = parse_pds_file(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f:
            f.write("test")
            f.flush()
            clippings_result = parse_clippings_file(f.name)
        
        self.assertIsInstance(pds_result, dict)
        self.assertIsInstance(clippings_result, dict)
        
        # Clean up
        os.unlink(f.name)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)