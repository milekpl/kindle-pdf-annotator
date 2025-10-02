#!/usr/bin/env python3
"""
Moved debug script: examine annotation structure and page number fields
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations

sample_data = Path("examples/sample_data")
krds_file = sample_data / "peirce-charles-fixation-belief.sdr" / "peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds"

print("🔍 DEBUGGING ANNOTATION STRUCTURE")
print("=" * 50)

annotations = create_amazon_compliant_annotations(
    str(krds_file),
    None,
    "peirce-charles-fixation-belief"
)

print(f"Found {len(annotations)} annotations")
print("\n📋 FIRST ANNOTATION STRUCTURE:")
if annotations:
    first_ann = annotations[0]
    for key, value in first_ann.items():
        print(f"  {key}: {value}")
    print(f"\n📄 PAGE NUMBERS IN ALL ANNOTATIONS:")
    for i, ann in enumerate(annotations):
        page_fields = {}
        for key, value in ann.items():
            if 'page' in key.lower():
                page_fields[key] = value
        print(f"  Annotation {i}: {page_fields}")
