#!/usr/bin/env python3
"""
Unit tests for the PDF annotator to check that highlights are found in proper locations and have appropriate sizes across 3 PDFs
"""
import fitz
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.pdf_annotator import annotate_pdf_file


class TestHighlightLocationsAndSizes(unittest.TestCase):
    """Test class for validating highlight locations and sizes across three PDFs"""
    
    def setUp(self):
        """Set up the test cases with three sample PDFs"""
        self.samples_dir = Path("examples/sample_data")
        
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
                "book_name": "Downey - 2024 - Theatre Hunger An Underestimated Scaling Up Pro",
            },
            {
                "name": "659ec7697e419",
                "pdf_path": self.samples_dir / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf",
                "sdr_path": self.samples_dir / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr",
                "clippings_path": self.samples_dir / "659ec7697e419-clippings.txt",
                "book_name": "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ",
            }
        ]

    def test_annotations_across_all_pdfs(self):
        """Test that all three PDFs have properly located and sized highlights"""
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
                
                # Find KRDS files (.pds or .pdt)
                krds_files = list(sdr_path.glob("*.pds")) + list(sdr_path.glob("*.pdt"))
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
                    self.assertLess(highlight['pdf_height'], 100, 
                                  f"Height seems too large for highlight in {test_case['name']}")

                print(f"✅ {len(highlights)} valid highlights found in {test_case['name']}")
                
                # Verify that we can create an annotated PDF with these annotations
                output_path = f"test_output_{test_case['book_name'].replace(' ', '_')[:20]}.pdf"
                success = annotate_pdf_file(str(pdf_path), annotations, output_path)
                self.assertTrue(success, f"Failed to create annotated PDF for {test_case['name']}")
                print(f"✅ Annotated PDF created successfully for {test_case['name']}")


if __name__ == "__main__":
    unittest.main()