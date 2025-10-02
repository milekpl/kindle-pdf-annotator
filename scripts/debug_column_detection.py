#!/usr/bin/env python3
"""
Moved debug script: analyze column detection and highlighting issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import fitz
from pdf_processor.column_aware_highlighting import ColumnDetector
from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations

def analyze_pdf_structure(pdf_path: str):
    """Analyze PDF structure and column detection"""
    print(f"📖 Analyzing: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    detector = ColumnDetector(doc)
    
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        print(f"\n📄 Page {page_num}:")
        print(f"   Page size: {page.rect.width:.1f} x {page.rect.height:.1f}")
        columns = detector.get_columns_for_page(page_num)
        print(f"   Detected {len(columns)} columns:")
        for i, col in enumerate(columns):
            print(f"     Column {i+1}: left={col['left']:.1f}, right={col['right']:.1f}, width={col['right']-col['left']:.1f}")

        blocks = page.get_text("dict")["blocks"]
        text_blocks = [block for block in blocks if block.get("type") == 0]
        print(f"   Text blocks: {len(text_blocks)}")

        if text_blocks:
            x_positions = []
            for block in text_blocks:
                bbox = block["bbox"]
                x_positions.append(bbox[0])
                x_positions.append(bbox[2])
            x_positions.sort()
            print(f"   X range: {min(x_positions):.1f} to {max(x_positions):.1f}")

        words = page.get_text("words")
        if words:
            print(f"   Sample words (first 5):")
            for i, word in enumerate(words[:5]):
                x0, y0, x1, y1, text = word[:5]
                print(f"     '{text}' at ({x0:.1f}, {y0:.1f})")

def analyze_annotations(krds_file: str, pdf_path: str):
    print(f"\n🎯 Analyzing annotations from: {krds_file}")
    annotations = create_amazon_compliant_annotations(krds_file, None, "peirce-charles-fixation-belief")
    doc = fitz.open(pdf_path)
    detector = ColumnDetector(doc)
    print(f"   Found {len(annotations)} annotations")
    for i, ann in enumerate(annotations[:5]):
        page_num = ann['pdf_page_0based']
        x = ann['pdf_x']
        y = ann['pdf_y']
        print(f"\n   Annotation {i+1}:")
        print(f"     Page: {page_num}, Position: ({x:.1f}, {y:.1f})")
        if page_num < len(doc):
            columns = detector.get_columns_for_page(page_num)
            column = detector.get_column_for_position(page_num, x, y)
            if column:
                col_idx = columns.index(column)
                print(f"     In column {col_idx+1}: left={column['left']:.1f}, right={column['right']:.1f}")
            else:
                print(f"     ⚠️  Not in any detected column!")

def analyze_text_around_annotation(pdf_path: str, page_num: int, x: float, y: float, radius: float = 50):
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    words = page.get_text("words")
    nearby_words = []
    for word in words:
        word_x0, word_y0, word_x1, word_y1, text = word[:5]
        word_center_x = (word_x0 + word_x1) / 2
        word_center_y = (word_y0 + word_y1) / 2
        distance = ((word_center_x - x) ** 2 + (word_center_y - y) ** 2) ** 0.5
        if distance <= radius:
            nearby_words.append((distance, text, word_x0, word_y0, word_x1, word_y1))
    nearby_words.sort()
    print(f"\n🔍 Text near annotation at ({x:.1f}, {y:.1f}) on page {page_num}:")
    for distance, text, x0, y0, x1, y1 in nearby_words[:10]:
        print(f"   '{text}' at ({x0:.1f}, {y0:.1f}) - distance: {distance:.1f}")

if __name__ == "__main__":
    sample_pdf = "examples/sample_data/peirce-charles-fixation-belief.pdf"
    krds_file = "examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds"
    if Path(sample_pdf).exists():
        analyze_pdf_structure(sample_pdf)
        if Path(krds_file).exists():
            analyze_annotations(krds_file, sample_pdf)
            annotations = create_amazon_compliant_annotations(krds_file, None, "peirce-charles-fixation-belief")
            if annotations:
                first_ann = annotations[0]
                analyze_text_around_annotation(sample_pdf, first_ann['pdf_page_0based'], first_ann['pdf_x'], first_ann['pdf_y'])
    else:
        print(f"❌ PDF file not found: {sample_pdf}")
