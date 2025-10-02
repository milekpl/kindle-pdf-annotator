#!/usr/bin/env python3
"""
Get Kindle coordinates for the title highlight
"""

import sys
sys.path.append('src')
from kindle_parser.krds_parser import parse_krds_file

def get_title_coordinates():
    # Parse the KRDS file
    annotations = parse_krds_file('examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds')

    # Find the title highlight
    for ann in annotations:
        if ann.type == 'annotation.personal.highlight':
            content = ann.content or ''
            if 'Fixation' in content:
                pos = ann.start_position
                print(f'Title highlight: "{content}"')
                print(f'Position raw: {pos.raw}')
                print(f'Kindle coordinates: x={pos.x}, y={pos.y}, width={pos.width}, height={pos.height}')
                
                # Calculate what the current conversion gives us
                kindle_x = float(pos.x)
                kindle_width = float(pos.width)
                
                print(f'\nKindle title position analysis:')
                print(f'   Start X: {kindle_x}')
                print(f'   Width: {kindle_width}')
                print(f'   End X: {kindle_x + kindle_width}')
                
                print(f'\nPDF title position (actual):')
                print(f'   Start X: 205.0pt')
                print(f'   Width: 184.2pt') 
                print(f'   End X: 389.3pt')
                
                # Calculate the correct scaling
                pdf_width = 184.2
                correct_scaling = pdf_width / kindle_width
                print(f'\nCorrect width scaling: {pdf_width} / {kindle_width} = {correct_scaling:.6f}')
                
                # For X position, we need to map 284 -> 205.0
                pdf_start = 205.0
                x_offset = pdf_start - (kindle_x * correct_scaling)
                print(f'X position mapping: {kindle_x} * {correct_scaling:.6f} + {x_offset:.1f} = {kindle_x * correct_scaling + x_offset:.1f}')
                
                break

if __name__ == "__main__":
    get_title_coordinates()