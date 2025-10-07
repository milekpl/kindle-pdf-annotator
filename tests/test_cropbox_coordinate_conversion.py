"""
Unit tests for CropBox-aware coordinate conversion.

Tests the validated H1 formula with CropBox offset correction.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import fitz
from kindle_parser.amazon_coordinate_system import convert_kindle_to_pdf_coordinates


class TestCropBoxCoordinateConversion(unittest.TestCase):
    """Test coordinate conversion with CropBox handling"""
    
    def test_no_cropbox_offset(self):
        """Test conversion without CropBox offset (normal PDF)"""
        krds_x, krds_y = 100, 200
        pdf_rect = fitz.Rect(0, 0, 612, 792)
        cropbox = fitz.Rect(0, 0, 612, 792)
        
        pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
            krds_x, krds_y,
            pdf_rect=pdf_rect,
            cropbox=cropbox
        )
        
        # H1 formula: (krds / 100) * 72
        expected_x = (krds_x / 100.0) * 72.0
        expected_y = (krds_y / 100.0) * 72.0
        
        self.assertAlmostEqual(pdf_x, expected_x, places=2)
        self.assertAlmostEqual(pdf_y, expected_y, places=2)
    
    def test_with_cropbox_offset(self):
        """Test conversion with CropBox offset (cropped PDF)"""
        krds_x, krds_y = 500, 300
        cropbox_offset_x, cropbox_offset_y = 40.1, 10.0
        
        pdf_rect = fitz.Rect(cropbox_offset_x, cropbox_offset_y, 612, 792)
        cropbox = fitz.Rect(cropbox_offset_x, cropbox_offset_y, 612, 792)
        
        pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
            krds_x, krds_y,
            pdf_rect=pdf_rect,
            cropbox=cropbox
        )
        
        # H1 formula with CropBox correction
        expected_x = (krds_x / 100.0) * 72.0 - cropbox_offset_x
        expected_y = (krds_y / 100.0) * 72.0 - cropbox_offset_y
        
        self.assertAlmostEqual(pdf_x, expected_x, places=2)
        self.assertAlmostEqual(pdf_y, expected_y, places=2)
    
    def test_shea_cropbox_example(self):
        """Test with real Shea PDF CropBox offset (40.1 pts)"""
        # Use realistic KRDS values that would be within page bounds
        krds_x, krds_y = 500, 300  # Realistic values
        cropbox_offset = 40.1
        
        cropbox = fitz.Rect(cropbox_offset, 0, 612, 792)
        
        pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
            krds_x, krds_y,
            cropbox=cropbox
        )
        
        expected_x = (krds_x / 100.0) * 72.0 - cropbox_offset
        expected_y = (krds_y / 100.0) * 72.0
        
        self.assertAlmostEqual(pdf_x, expected_x, places=2)
        self.assertAlmostEqual(pdf_y, expected_y, places=2)
        
        # Verify the CropBox correction is applied
        uncropped_x = (krds_x / 100.0) * 72.0
        difference = uncropped_x - pdf_x
        self.assertAlmostEqual(difference, cropbox_offset, places=2)
    
    def test_bounds_clamping_with_cropbox(self):
        """Test that coordinates are clamped to visible page bounds"""
        # Large KRDS values that would exceed page bounds
        krds_x, krds_y = 10000, 12000
        cropbox = fitz.Rect(40.1, 0, 612, 792)
        
        pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
            krds_x, krds_y,
            cropbox=cropbox
        )
        
        # Should be clamped to CropBox dimensions
        cropbox_width = cropbox.width
        cropbox_height = cropbox.height
        
        self.assertLessEqual(pdf_x, cropbox_width)
        self.assertLessEqual(pdf_y, cropbox_height)
        self.assertGreaterEqual(pdf_x, 0)
        self.assertGreaterEqual(pdf_y, 0)
    
    def test_multiple_coordinates_with_cropbox(self):
        """Test multiple coordinate pairs with CropBox offset"""
        cropbox = fitz.Rect(40.1, 0, 612, 792)
        
        test_cases = [
            (100, 100, 31.9, 72.0),   # Small values - within bounds
            (400, 500, 247.9, 360.0),  # Mid-range - within bounds
            (700, 800, 463.9, 576.0),  # Higher - within bounds
        ]
        
        for krds_x, krds_y, expected_x, expected_y in test_cases:
            with self.subTest(krds_x=krds_x, krds_y=krds_y):
                pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
                    krds_x, krds_y,
                    cropbox=cropbox
                )
                self.assertAlmostEqual(pdf_x, expected_x, places=1)
                self.assertAlmostEqual(pdf_y, expected_y, places=1)
    
    def test_none_cropbox(self):
        """Test that None CropBox is handled gracefully"""
        krds_x, krds_y = 200, 300
        
        pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
            krds_x, krds_y,
            cropbox=None
        )
        
        # Should use H1 formula without offset
        expected_x = (krds_x / 100.0) * 72.0
        expected_y = (krds_y / 100.0) * 72.0
        
        self.assertAlmostEqual(pdf_x, expected_x, places=2)
        self.assertAlmostEqual(pdf_y, expected_y, places=2)
    
    def test_zero_coordinates(self):
        """Test conversion of zero coordinates"""
        krds_x, krds_y = 0, 0
        cropbox = fitz.Rect(40.1, 20.0, 612, 792)
        
        pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(
            krds_x, krds_y,
            cropbox=cropbox
        )
        
        # Should be 0 - cropbox_offset, but clamped to 0
        self.assertEqual(pdf_x, 0.0)
        self.assertEqual(pdf_y, 0.0)


if __name__ == '__main__':
    unittest.main()
