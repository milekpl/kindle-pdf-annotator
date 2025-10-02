#!/usr/bin/env python3
"""
Moved debug script: inspect annotation generation and counts
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations

def main():
    # Process annotations
    pds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    pdt_file = None  # We're using KRDS only approach 
    book_name = 'Peirce'

    print('Getting annotations...')
    annotations = create_amazon_compliant_annotations(pds_file, pdt_file, book_name)

    # Count by type
    types = {}
    for ann in annotations:
        t = ann.get('type', 'unknown')
        types[t] = types.get(t, 0) + 1

    print(f'Annotation counts: {types}')
    
    # Show ALL annotations to see if bookmarks are there
    print(f'\nAll {len(annotations)} annotations:')
    for i, ann in enumerate(annotations):
        t = ann.get('type')
        page = ann.get('pdf_page_0based', 'None')
        content = ann.get('content', '')[:20]
        print(f'  {i+1}. {t} page {page}: {content}...')

    # Show first few annotations with coordinates  
    print('\nFirst 3 annotations:')
    for i, ann in enumerate(annotations[:3]):
        print(f'\nAnnotation {i+1}:')
        print(f'  Type: {ann.get("type")}')
        print(f'  All keys: {list(ann.keys())}')
        print(f'  Page number: {ann.get("page_number")}')
        print(f'  PDF page 0based: {ann.get("pdf_page_0based")}')
        print(f'  JSON page 0based: {ann.get("json_page_0based")}')
        content = ann.get("content", "")
        print(f'  Content: {content[:50]}...')
        if ann.get('start_position'):
            print(f'  Start: {ann["start_position"]}')
        if ann.get('end_position'):
            print(f'  End: {ann["end_position"]}')
        if 'pdf_x' in ann:
            print(f'  PDF XY: ({ann["pdf_x"]:.1f}, {ann["pdf_y"]:.1f})')

    # Show bookmarks specifically
    bookmarks = [ann for ann in annotations if ann.get('type') == 'bookmark']
    print(f'\nBookmarks found: {len(bookmarks)}')
    for i, bookmark in enumerate(bookmarks):
        print(f"\nBookmark {i+1}:")
        print(f"  All keys: {list(bookmark.keys())}")
        print(f"  Page: {bookmark.get('page_number')}")
        print(f"  PDF page 0based: {bookmark.get('pdf_page_0based')}")
        if bookmark.get('start_position'):
            print(f"  Start: {bookmark.get('start_position')}")
        if 'pdf_x' in bookmark:
            print(f"  PDF XY: ({bookmark.get('pdf_x'):.1f}, {bookmark.get('pdf_y'):.1f})")

if __name__ == '__main__':
    main()
