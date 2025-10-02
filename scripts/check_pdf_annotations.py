#!/usr/bin/env python3

import sys
sys.path.append('.')

import fitz  # PyMuPDF

def check_pdf_annotations(pdf_path):
    """Check what annotations are actually stored in a PDF"""
    print(f"🔍 Examining annotations in: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    
    total_annotations = 0
    by_type = {}
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        annotations = list(page.annots())
        
        if annotations:
            print(f"\nPage {page_num + 1}: {len(annotations)} annotations")
            
        for annot in annotations:
            total_annotations += 1
            annot_type = annot.type[1]  # Get annotation type name
            by_type[annot_type] = by_type.get(annot_type, 0) + 1
            
            # Get annotation details
            info = annot.info
            rect = annot.rect
            
            print(f"  {total_annotations}. Type: {annot_type}")
            print(f"     Position: ({rect.x0:.1f}, {rect.y0:.1f}) to ({rect.x1:.1f}, {rect.y1:.1f})")
            print(f"     Title: {info.get('title', 'N/A')}")
            print(f"     Content: {info.get('content', 'N/A')}")
            
            # Special handling for different annotation types
            if annot_type == 'Text':
                try:
                    print(f"     Icon: {annot.icon if hasattr(annot, 'icon') else 'N/A'}")
                    print(f"     Is Open: {annot.is_open if hasattr(annot, 'is_open') else 'N/A'}")
                except AttributeError:
                    print(f"     Text annotation properties not accessible")
    
    doc.close()
    
    print(f"\n📊 Summary:")
    print(f"   Total annotations: {total_annotations}")
    print(f"   By type: {by_type}")
    
    return total_annotations, by_type

if __name__ == '__main__':
    # Check the fixed CLI-generated file
    check_pdf_annotations('bookmark_test_cli_fixed.pdf')