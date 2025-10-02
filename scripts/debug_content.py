#!/usr/bin/env python3
"""
Moved debug script: inspect KRDS content fields
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.krds_parser import parse_krds_file

def main():
    pds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    print('Examining content fields in KRDS data...')
    krds_annotations = parse_krds_file(pds_file)
    highlights = [ann for ann in krds_annotations if 'highlight' in ann.annotation_type]
    notes = [ann for ann in krds_annotations if 'note' in ann.annotation_type]
    print(f'First highlight fields:')
    if highlights:
        h = highlights[0]
        print(f'  All attributes: {dir(h)}')
        print(f'  Has text: {hasattr(h, "text")}')
        print(f'  Has content: {hasattr(h, "content")}')
        print(f'  Has value: {hasattr(h, "value")}')
        print(f'  Has selected_text: {hasattr(h, "selected_text")}')
        if hasattr(h, 'text'):
            print(f'  Text: {h.text}')
        if hasattr(h, 'content'):
            print(f'  Content: {repr(h.content)}')
        if hasattr(h, 'note_text'):
            print(f'  Note text: {repr(h.note_text)}')
        if hasattr(h, 'value'):
            print(f'  Value: {h.value}')
        if hasattr(h, 'selected_text'):
            print(f'  Selected text: {h.selected_text}')

    print(f'\nFirst note fields:')
    if notes:
        n = notes[0]
        print(f'  All attributes: {dir(n)}')
        print(f'  Has text: {hasattr(n, "text")}')
        print(f'  Has content: {hasattr(n, "content")}')
        print(f'  Has value: {hasattr(n, "value")}')
        if hasattr(n, 'text'):
            print(f'  Text: {n.text}')
        if hasattr(n, 'content'):
            print(f'  Content: {repr(n.content)}')
        if hasattr(n, 'note_text'):
            print(f'  Note text: {repr(n.note_text)}')
        if hasattr(n, 'value'):
            print(f'  Value: {n.value}')

if __name__ == '__main__':
    main()
