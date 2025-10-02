#!/usr/bin/env python3
"""
Moved debug script: inspect the Peirce test PDF annotations
"""

import fitz

pdf_file = 'tests/peirce_text_coverage_test.pdf'
doc = fitz.open(pdf_file)

print("=" * 80)
print("INSPECTING PEIRCE TEST PDF ANNOTATIONS")
print("=" * 80)

for page_num in range(min(3, len(doc))):
    page = doc.load_page(page_num)
    annotations = page.annots()
    print(f"\n Page {page_num + 1}:")
    print(f"   Page size: {page.rect.width}x{page.rect.height}")
    if annotations:
        annot_count = 0
        for annot in annotations:
            if annot.type[1] == 'Highlight':
                annot_count += 1
                rect = annot.rect
                text = page.get_textbox(rect).strip()
                text_preview = text[:40] + '...' if len(text) > 40 else text
                print(f"\n   Highlight #{annot_count}:")
                print(f"      Rect: ({rect.x0:.1f}, {rect.y0:.1f}) -> ({rect.x1:.1f}, {rect.y1:.1f})")
                print(f"      Width: {rect.width:.1f}pt, Height: {rect.height:.1f}pt")
                print(f"      Text: \"{text_preview}\"")
                if "Fixation of Belief" in text:
                    print(f"      >>> THIS IS THE TITLE HIGHLIGHT <<<")
                    print(f"      >>> Expected width: 184.2pt")
                    print(f"      >>> Actual width: {rect.width:.1f}pt")
                    print(f"      >>> Ratio: {rect.width/184.2:.2f}x")
    else:
        print("   No annotations found")

doc.close()
print("\n" + "=" * 80)
