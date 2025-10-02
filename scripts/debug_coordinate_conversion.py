#!/usr/bin/env python3
"""
Moved debug script: trace coordinate conversion through the entire pipeline
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format


def debug_coordinate_conversion():
    """Debug the coordinate conversion pipeline"""
    
    print("🔍 DEBUGGING COORDINATE CONVERSION PIPELINE")
    
    # Files
    krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    book_name = 'peirce-charles-fixation-belief'
    
    # Step 1: Get Amazon annotations
    print("\n1. Getting Amazon annotations...")
    amazon_annotations = create_amazon_compliant_annotations(krds_file, clippings_file, book_name)
    
    title_highlights = [ann for ann in amazon_annotations if ann.get('page_number') == 0 and ann.get('type') == 'highlight']
    
    for i, ann in enumerate(title_highlights):
        print(f"\n   Title highlight {i+1} (Amazon format):")
        print(f"     Kindle coords: x={ann.get('kindle_x')}, y={ann.get('kindle_y')}, w={ann.get('kindle_width')}, h={ann.get('kindle_height')}")
        print(f"     PDF coords: x={ann.get('pdf_x'):.1f}, y={ann.get('pdf_y'):.1f}")
        print(f"     Start pos: {ann.get('start_position')}")
        print(f"     End pos: {ann.get('end_position')}")
    
    # Step 2: Convert to PDF annotator format
    print("\n2. Converting to PDF annotator format...")
    pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
    
    title_pdf_highlights = [ann for ann in pdf_annotations if ann.get('page_number') == 0 and ann.get('type') == 'highlight']
    
    for i, ann in enumerate(title_pdf_highlights):
        print(f"\n   Title highlight {i+1} (PDF annotator format):")
        print(f"     Coordinates: {ann.get('coordinates', [])}")
        if 'coordinates' in ann and len(ann['coordinates']) >= 4:
            coords = ann['coordinates']
            width = coords[2] - coords[0]
            height = coords[3] - coords[1]
            print(f"     Rectangle: ({coords[0]:.1f}, {coords[1]:.1f}, {coords[2]:.1f}, {coords[3]:.1f})")
            print(f"     Width: {width:.1f}, Height: {height:.1f}")


if __name__ == "__main__":
    debug_coordinate_conversion()
