#!/usr/bin/env python3
"""
Analyze the actual content area boundaries in the PDF
"""

import fitz

def analyze_pdf_content_area():
    doc = fitz.open('examples/sample_data/peirce-charles-fixation-belief.pdf')
    page = doc.load_page(0)  # First page
    
    print(f'📏 PDF page dimensions: {page.rect}')
    print(f'   Width: {page.rect.width}, Height: {page.rect.height}')
    
    # Get all text on the page to find actual content boundaries
    text_dict = page.get_text('dict')
    
    all_x_coords = []
    all_y_coords = []
    
    print('\n📍 Analyzing text positions...')
    
    for block in text_dict['blocks']:
        if 'lines' in block:
            for line in block['lines']:
                for span in line['spans']:
                    bbox = span['bbox']
                    all_x_coords.extend([bbox[0], bbox[2]])  # left, right
                    all_y_coords.extend([bbox[1], bbox[3]])  # top, bottom
                    
                    # Print first few spans to see the layout
                    if len(all_x_coords) <= 20:
                        text = span['text'][:30]
                        print(f'   Text "{text}" at x={bbox[0]:.1f}-{bbox[2]:.1f}, y={bbox[1]:.1f}-{bbox[3]:.1f}')
    
    if all_x_coords and all_y_coords:
        content_left = min(all_x_coords)
        content_right = max(all_x_coords)
        content_top = min(all_y_coords)
        content_bottom = max(all_y_coords)
        
        print(f'\n📊 Actual content boundaries:')
        print(f'   X range: {content_left:.1f} to {content_right:.1f} (width: {content_right - content_left:.1f}pt)')
        print(f'   Y range: {content_top:.1f} to {content_bottom:.1f} (height: {content_bottom - content_top:.1f}pt)')
        print(f'   Left margin: {content_left:.1f}pt')
        print(f'   Right margin: {page.rect.width - content_right:.1f}pt')
        print(f'   Top margin: {content_top:.1f}pt')
        print(f'   Bottom margin: {page.rect.height - content_bottom:.1f}pt')
        
        # Search for title specifically
        print(f'\n🔍 Searching for title "The Fixation of Belief":')
        title_rects = page.search_for("The Fixation of Belief")
        for i, rect in enumerate(title_rects):
            print(f'   Title rect {i}: x={rect.x0:.1f}-{rect.x1:.1f}, y={rect.y0:.1f}-{rect.y1:.1f}')
            print(f'   Title width: {rect.width:.1f}pt, height: {rect.height:.1f}pt')
    
    doc.close()

if __name__ == "__main__":
    analyze_pdf_content_area()