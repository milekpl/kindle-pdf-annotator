#!/usr/bin/env python3
"""
Advanced PDF layout analysis to understand the column structure
"""

import sys
import fitz
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def analyze_page_layout_detailed(pdf_path: str, page_num: int = 0):
    """Analyze page layout in detail"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    print(f"📖 Detailed analysis of page {page_num}:")
    print(f"   Page size: {page.rect.width:.1f} x {page.rect.height:.1f}")
    
    # Get text lines with detailed positioning
    blocks = page.get_text("dict")["blocks"]
    text_blocks = [block for block in blocks if block.get("type") == 0]
    
    all_lines = []
    for block_idx, block in enumerate(text_blocks):
        for line_idx, line in enumerate(block.get("lines", [])):
            if line.get("spans"):
                bbox = line["bbox"]
                text = " ".join(span.get("text", "") for span in line["spans"])
                all_lines.append({
                    'block': block_idx,
                    'line': line_idx,
                    'left': bbox[0],
                    'top': bbox[1], 
                    'right': bbox[2],
                    'bottom': bbox[3],
                    'width': bbox[2] - bbox[0],
                    'height': bbox[3] - bbox[1],
                    'text': text.strip()
                })
    
    print(f"   Total text lines: {len(all_lines)}")
    
    # Group lines by Y position (horizontal alignment)
    y_groups = defaultdict(list)
    y_tolerance = 5  # Points
    
    for line in all_lines:
        y_key = round(line['top'] / y_tolerance) * y_tolerance
        y_groups[y_key].append(line)
    
    # Look for lines that have multiple text segments (potential two-column indicators)
    multi_segment_lines = []
    for y_pos, lines in y_groups.items():
        if len(lines) > 1:
            # Sort by X position
            lines.sort(key=lambda l: l['left'])
            
            # Check for significant gaps between text segments
            for i in range(1, len(lines)):
                gap = lines[i]['left'] - lines[i-1]['right']
                if gap > 30:  # Significant gap suggests column separation
                    multi_segment_lines.append({
                        'y': y_pos,
                        'left_text': lines[i-1]['text'][:30],
                        'right_text': lines[i]['text'][:30],
                        'gap': gap,
                        'left_x': lines[i-1]['left'],
                        'right_x': lines[i]['left']
                    })
    
    print(f"   Lines with potential column separation: {len(multi_segment_lines)}")
    if multi_segment_lines:
        print("   Examples:")
        for i, seg in enumerate(multi_segment_lines[:5]):
            print(f"     Line {i+1} (y={seg['y']:.1f}): '{seg['left_text']}' ... gap={seg['gap']:.1f}pt ... '{seg['right_text']}'")
            print(f"       Left at x={seg['left_x']:.1f}, Right at x={seg['right_x']:.1f}")
    
    # Analyze text distribution across page width
    left_positions = [line['left'] for line in all_lines]
    right_positions = [line['right'] for line in all_lines]
    
    print(f"   Text X range: {min(left_positions):.1f} to {max(right_positions):.1f}")
    
    # Look for consistent left margins that might indicate columns
    left_margin_groups = defaultdict(int)
    margin_tolerance = 10
    
    for pos in left_positions:
        margin_key = round(pos / margin_tolerance) * margin_tolerance
        left_margin_groups[margin_key] += 1
    
    # Find the most common left margins
    common_margins = sorted(left_margin_groups.items(), key=lambda x: x[1], reverse=True)
    print(f"   Most common left margins:")
    for margin, count in common_margins[:5]:
        print(f"     x={margin:.1f}: {count} lines")
    
    # Show some sample text lines with their positions
    print("   Sample text lines:")
    for i, line in enumerate(all_lines[:10]):
        print(f"     {i+1}. '{line['text'][:40]}...' at ({line['left']:.1f}, {line['top']:.1f})")

if __name__ == "__main__":
    sample_pdf = "examples/sample_data/peirce-charles-fixation-belief.pdf"
    
    if Path(sample_pdf).exists():
        # Analyze first few pages
        for page_num in range(min(3, 4)):  # Check first 3 pages
            analyze_page_layout_detailed(sample_pdf, page_num)
            print()
    else:
        print(f"❌ PDF file not found: {sample_pdf}")