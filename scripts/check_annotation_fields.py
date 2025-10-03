#!/usr/bin/env python3
"""
Check Amazon annotation fields
"""

import sys
sys.path.append('src')

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations

def check_annotation_fields():
    # Get Amazon annotations to check the pdf_width field
    annotations = create_amazon_compliant_annotations(
        'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds',
        'examples/sample_data/peirce-charles-fixation-belief-clippings.txt', 
        'peirce-charles-fixation-belief'
    )

    print(f'\nFound {len(annotations)} annotations')

    # Check first few highlights
    for i, ann in enumerate(annotations):
        if ann.get('type') == 'highlight':
            print(f'\nHighlight {i+1}:')
            print(f'   content: {repr(ann.get("content", ""))}')
            print(f'   kindle_width: {ann.get("kindle_width")}')
            print(f'   pdf_width: {ann.get("pdf_width")}')
            print(f'   pdf_x: {ann.get("pdf_x")}')
            if i >= 2:  # Only show first 3 highlights
                break

if __name__ == "__main__":
    check_annotation_fields()