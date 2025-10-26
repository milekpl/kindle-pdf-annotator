#!/usr/bin/env python3
"""
Unit tests for the PDF annotator to check that highlights are found in proper locations and have appropriate sizes.
Tests all example PDFs in the examples/sample_data directory.
"""
import fitz
from pathlib import Path
import sys
import unittest
import os

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.pdf_annotator import annotate_pdf_file


class TestHighlightLocationsAndSizes(unittest.TestCase):
    """Test class for validating highlight locations and sizes across all example PDFs"""
    
    def setUp(self):
        """Set up the test cases with all example PDFs"""
        self.samples_dir = Path("examples/sample_data")
        self.created_files = []  # Track files created during tests for cleanup
        
        self.test_cases = [
            {
                "name": "Peirce - The Fixation of Belief",
                "pdf_path": self.samples_dir / "peirce-charles-fixation-belief.pdf",
                "sdr_path": self.samples_dir / "peirce-charles-fixation-belief.sdr",
                "clippings_path": self.samples_dir / "peirce-charles-fixation-belief-clippings.txt",
                "book_name": "peirce-charles-fixation-belief",
            },
            {
                "name": "Theatre Hunger Paper",
                "pdf_path": self.samples_dir / "Downey_2024_Theatre_Hunger_Scaling_Up_Paper.pdf",
                "sdr_path": self.samples_dir / "Downey_2024_Theatre_Hunger_Scaling_Up_Paper.sdr",
                "clippings_path": self.samples_dir / "Downey_2024_Theatre_Hunger_Scaling_Up_Paper-clippings.txt",
                "book_name": "Downey_2024_Theatre_Hunger_Scaling_Up_Paper",
            },
            {
                "name": "659ec7697e419",
                "pdf_path": self.samples_dir / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf",
                "sdr_path": self.samples_dir / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr",
                "clippings_path": self.samples_dir / "659ec7697e419-clippings.txt",
                "book_name": "659ec7697e419",
            },
            {
                "name": "Shea Page 136 (CropBox Example)",
                "pdf_path": self.samples_dir / "page_136_shea.pdf",
                "sdr_path": self.samples_dir / "page_136_shea.sdr",
                "clippings_path": self.samples_dir / "page_136_shea-clippings.txt",
                "book_name": "page_136_shea",
            },
            {
                "name": "Page 2 Paper (Greedy Matching Bug Test)",
                "pdf_path": self.samples_dir / "page_2_paper.pdf",
                "sdr_path": self.samples_dir / "page_2_paper.sdr",
                "clippings_path": self.samples_dir / "page_2_paper-clippings.txt",
                "book_name": "page_2_paper",
                "expected_highlight_count": 2,  # Should be exactly 2, not dozens
                "expected_highlight_contents": ["the", "a"],  # Must match actual highlighted text
            }
        ]
    
    def tearDown(self):
        """Clean up any PDF files created during tests"""
        for file_path in self.created_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🧹 Cleaned up: {file_path}")
            except Exception as e:
                print(f"⚠️  Failed to clean up {file_path}: {e}")

    def test_annotations_across_all_pdfs(self):
        """Test that all example PDFs have properly located and sized highlights"""
        for test_case in self.test_cases:
            with self.subTest(pdf_name=test_case['name']):
                pdf_path = test_case['pdf_path']
                sdr_path = test_case['sdr_path']
                clippings_path = test_case['clippings_path']
                book_name = test_case['book_name']

                # Verify that required files exist
                self.assertTrue(pdf_path.exists(), f"PDF file does not exist: {pdf_path}")
                self.assertTrue(sdr_path.exists(), f"SDR folder does not exist: {sdr_path}")
                
                # Check that clippings file exists
                if clippings_path.exists():
                    print(f"✅ Clippings file exists for {test_case['name']}")
                else:
                    print(f"⚠️  Clippings file does not exist for {test_case['name']}")
                
                # Find KRDS files (.pds only - .pdt files contain no annotations)
                krds_files = list(sdr_path.glob("*.pds"))
                self.assertGreater(len(krds_files), 0, f"No KRDS files found in {sdr_path}")
                
                print(f"📖 Found {len(krds_files)} KRDS files for {test_case['name']}")
                
                # Try to process the first KRDS file
                krds_file_path = str(krds_files[0])
                clippings_file_path = str(clippings_path) if clippings_path.exists() else ""
                
                # Process annotations
                annotations = create_amazon_compliant_annotations(
                    krds_file_path, 
                    clippings_file_path, 
                    book_name
                )
                
                # Verify that annotations were found
                self.assertGreater(len(annotations), 0, f"No annotations found in {krds_file_path}")
                
                # Extract highlights
                highlights = [a for a in annotations if a['type'] == 'highlight']
                
                # Check that highlights exist
                self.assertGreater(len(highlights), 0, f"No highlights found for {test_case['name']}")
                
                # Check expected highlight count if specified (for greedy matching bug test)
                if 'expected_highlight_count' in test_case:
                    expected_count = test_case['expected_highlight_count']
                    self.assertEqual(len(highlights), expected_count,
                                   f"Expected exactly {expected_count} highlights for {test_case['name']}, but found {len(highlights)}. "
                                   f"This likely indicates a greedy matching bug where single-letter highlights match throughout the page.")
                
                # Check expected highlight contents if specified (validates correct matching)
                if 'expected_highlight_contents' in test_case:
                    expected_contents = test_case['expected_highlight_contents']
                    actual_contents = [h.get('content', '').strip() for h in highlights]
                    self.assertEqual(sorted(actual_contents), sorted(expected_contents),
                                   f"Highlight contents don't match for {test_case['name']}. "
                                   f"Expected: {expected_contents}, Got: {actual_contents}. "
                                   f"This indicates highlights are being matched to wrong text locations.")
                
                # Check that highlights have appropriate locations and sizes
                for highlight in highlights:
                    # Check that coordinates are reasonable (positive and within page bounds)
                    self.assertGreaterEqual(highlight['pdf_page_0based'], 0, 
                                          f"Invalid page number for highlight in {test_case['name']}")
                    self.assertGreaterEqual(highlight['pdf_x'], 0, 
                                          f"Invalid X coordinate for highlight in {test_case['name']}")
                    self.assertGreaterEqual(highlight['pdf_y'], 0, 
                                          f"Invalid Y coordinate for highlight in {test_case['name']}")
                    
                    # Check that size dimensions are positive
                    self.assertGreater(highlight['pdf_width'], 0, 
                                     f"Width should be positive for highlight in {test_case['name']}")
                    self.assertGreater(highlight['pdf_height'], 0, 
                                     f"Height should be positive for highlight in {test_case['name']}")
                    
                    # Check that size dimensions are not too large (these should be reasonable values for highlights)
                    self.assertLess(highlight['pdf_width'], 1000, 
                                  f"Width seems too large for highlight in {test_case['name']}")
                    self.assertLess(highlight['pdf_height'], 300, 
                                  f"Height seems too large for highlight in {test_case['name']}")

                print(f"✅ {len(highlights)} valid highlights found in {test_case['name']}")
                
                # Verify that we can create an annotated PDF with these annotations
                output_path = f"test_output_{test_case['book_name'].replace(' ', '_')[:20]}.pdf"
                self.created_files.append(output_path)  # Track for cleanup
                success = annotate_pdf_file(str(pdf_path), annotations, output_path)
                self.assertTrue(success, f"Failed to create annotated PDF for {test_case['name']}")
                print(f"✅ Annotated PDF created successfully for {test_case['name']}")

    def test_peirce_note_unification_correctness(self):
        """
        Test that notes in the Peirce PDF are unified with the correct highlights.
        
        This is a regression test for the bug where notes were being unified with the wrong
        highlights due to incorrect ordering in the PRE-STEP clippings-to-KRDS matching.
        """
        test_case = {
            "name": "Peirce - The Fixation of Belief",
            "pdf_path": self.samples_dir / "peirce-charles-fixation-belief.pdf",
            "sdr_path": self.samples_dir / "peirce-charles-fixation-belief.sdr",
            "clippings_path": self.samples_dir / "peirce-charles-fixation-belief-clippings.txt",
            "book_name": "peirce-charles-fixation-belief",
        }
        
        sdr_path = test_case["sdr_path"]
        krds_file_path = None
        
        # Find KRDS file
        if sdr_path.exists():
            pds_files = list(sdr_path.glob("*.pds"))
            if pds_files:
                krds_file_path = str(pds_files[0])
        
        self.assertIsNotNone(krds_file_path, "Could not find KRDS file for Peirce test")
        
        # Create annotations
        annotations = create_amazon_compliant_annotations(
            krds_file_path,
            str(test_case["clippings_path"]),
            test_case["book_name"]
        )
        
        # Find notes on page 3 (0-based) / page 4 (1-based)
        notes_on_page_3 = [a for a in annotations if a['type'] == 'note' and a['pdf_page_0based'] == 3]
        
        # Should have exactly 1 note on page 3 (the second note "Note for a paragraph...")
        self.assertEqual(len(notes_on_page_3), 1, 
                        "Expected exactly 1 note on page 4 of Peirce PDF")
        
        note = notes_on_page_3[0]
        
        # The note should have highlight_content field (indicating it was unified)
        self.assertIn('highlight_content', note,
                     "Note should have highlight_content field (unified with highlight)")
        
        # The highlight_content should be "We generally know..." NOT "The Assassins..."
        highlight_content = note.get('highlight_content', '')
        self.assertIn('We generally know', highlight_content,
                     f"Note should be unified with 'We generally know...' highlight, but got: {highlight_content[:50]}")
        self.assertNotIn('Assassins', highlight_content,
                        f"Note should NOT be unified with 'The Assassins' highlight, but got: {highlight_content[:50]}")
        
        # The note content should be "Note for a paragraph and one word more"
        note_content = note.get('content', '')
        self.assertIn('Note for a paragraph', note_content,
                     f"Note content should be 'Note for a paragraph...', but got: {note_content[:50]}")
        
        print("✅ Peirce note unified with correct highlight based on Y-position ordering")


if __name__ == "__main__":
    unittest.main()
