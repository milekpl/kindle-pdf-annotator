#!/usr/bin/env python3
"""
Moved debug script: parse KRDS file directly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.krds_parser import parse_krds_file

def main():
    pds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    print('Parsing KRDS file directly...')
    krds_annotations = parse_krds_file(pds_file)
    print(f'Total KRDS annotations: {len(krds_annotations)}')
    highlights = [ann for ann in krds_annotations if 'highlight' in ann.annotation_type]
    notes = [ann for ann in krds_annotations if 'note' in ann.annotation_type]
    bookmarks = [ann for ann in krds_annotations if 'bookmark' in ann.annotation_type]
    print(f'KRDS highlights: {len(highlights)}')
    print(f'KRDS notes: {len(notes)}')
    print(f'KRDS bookmarks: {len(bookmarks)}')
    print('\nBookmark details:')
    for i, bookmark in enumerate(bookmarks):
        print(f'\nBookmark {i+1}:')
        print(f'  Type: {bookmark.annotation_type}')
        print(f'  Has start_position: {hasattr(bookmark, "start_position")}')
        if hasattr(bookmark, 'start_position'):
            print(f'  Start position valid: {bookmark.start_position.valid}')
            if bookmark.start_position.valid:
                print(f'  Page: {bookmark.start_position.page}')
                print(f'  X: {bookmark.start_position.x}')
                print(f'  Y: {bookmark.start_position.y}')
                print(f'  Width: {bookmark.start_position.width}')
                print(f'  Height: {bookmark.start_position.height}')
            else:
                print(f'  Start position INVALID!')

if __name__ == '__main__':
    main()
