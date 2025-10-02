#!/usr/bin/env python3
"""
Moved debug script: debug title width calculation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations, convert_kindle_width_to_pdf
from pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format

def debug_title_width():
    print("🔍 DEBUGGING TITLE WIDTH CALCULATION")
    amazon_annotations = create_amazon_compliant_annotations(
        'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds',
        'examples/sample_data/peirce-charles-fixation-belief-clippings.txt',
        'peirce-charles-fixation-belief'
    )
    for ann in amazon_annotations:
        if ann.get('type') == 'highlight':
            content = ann.get('content', '')
            if 'Fixation' in content:
                print(f"\n📋 Title annotation found:")
                print(f"   Content: {content}")
                print(f"   Kindle width: {ann.get('kindle_width')}")
                kindle_width = float(ann.get('kindle_width', 0))
                pdf_width = convert_kindle_width_to_pdf(kindle_width)
                print(f"\n🧮 Direct width conversion:")
                print(f"   Input kindle_width: {kindle_width}")
                print(f"   Output pdf_width: {pdf_width:.1f}pt")
                print(f"   Expected: 184.2pt")
                break
    print(f"\n🔄 Converting to PDF annotator format...")
    pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
    for ann in pdf_annotations:
        if ann.get('text', '') and 'Fixation' in ann.get('text', ''):
            rect = ann.get('rect', [0, 0, 0, 0])
            width = rect[2] - rect[0] if len(rect) >= 4 else 0
            print(f"\n📐 PDF annotation result:")
            print(f"   Rect: {rect}")
            print(f"   Width: {width:.1f}pt")
            print(f"   Expected: 184.2pt")
            break

if __name__ == "__main__":
    debug_title_width()
