#!/usr/bin/env python3
"""Debug script to find the page 10 issue in Alfredo PDF."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations

sdr_dir = project_root / "learn/documents/Alfredo, Scientific Understanding.pdf-cdeKey_JMX5RBNPCPLVH6QLQX55THDZIJD7BM35.sdr"
pds_files = list(sdr_dir.glob("*.pds"))
clippings_file = str(project_root / "learn/documents/My Clippings.txt")

print("Processing Alfredo PDF...")
print(f"PDS files: {len(pds_files)}")
print()

for pds_file in pds_files:
    annotations = create_amazon_compliant_annotations(
        str(pds_file),
        clippings_file,
        "Alfredo, Scientific Understanding"
    )
    
    print(f"\n{'='*80}")
    print(f"FOUND {len(annotations)} ANNOTATIONS")
    print(f"{'='*80}\n")
    
    # Find page 10 highlights
    page_10_annots = [a for a in annotations if a.get('page') == 10]
    
    print(f"Page 10 annotations: {len(page_10_annots)}")
    print()
    
    for i, ann in enumerate(page_10_annots):
        print(f"=== Annotation {i+1} on Page 10 ===")
        print(f"Position: x={ann.get('x'):.1f}, y={ann.get('y'):.1f}")
        print(f"Size: width={ann.get('pdf_width'):.1f}, height={ann.get('pdf_height'):.1f}")
        
        text = ann.get('text', '')
        print(f"Text ({len(text)} chars): \"{text[:100]}{'...' if len(text) > 100 else ''}\"")
        
        if 'quads' in ann:
            quads = ann['quads']
            print(f"Quads: {len(quads)} quad(s)")
            
            for j, quad in enumerate(quads):
                xs = [p[0] for p in quad]
                ys = [p[1] for p in quad]
                print(f"  Quad {j+1}: x=[{min(xs):.1f}-{max(xs):.1f}], y=[{min(ys):.1f}-{max(ys):.1f}]")
                
                # Check distance between quads
                if j > 0:
                    prev_quad = quads[j-1]
                    prev_xs = [p[0] for p in prev_quad]
                    gap = min(xs) - max(prev_xs)
                    print(f"    ⚠️  Gap from previous quad: {gap:.1f} points")
        print()
