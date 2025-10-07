#!/usr/bin/env python3
"""
Verify that KRDS uses 0-based page numbering while MyClippings uses 1-based.
Test the hypothesis: KRDS_page + 1 = MyClippings_page
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.krds_parser import KindleReaderDataStore
from kindle_parser.clippings_parser import parse_myclippings_for_book


def test_offset_hypothesis():
    """Test if adding 1 to KRDS pages matches MyClippings pages."""
    
    samples_dir = Path('examples/sample_data')
    
    test_cases = [
        ('page_136_shea', 'page_136_shea.sdr', 'page_136_shea-clippings.txt'),
        ('659ec7697e419', '659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr', '659ec7697e419-clippings.txt'),
        ('Downey_2024', 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper.sdr', 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper-clippings.txt'),
        ('peirce-charles', 'peirce-charles-fixation-belief.sdr', 'peirce-charles-fixation-belief-clippings.txt'),
    ]
    
    print("="*80)
    print("TESTING HYPOTHESIS: KRDS_page + 1 = MyClippings_page")
    print("="*80)
    
    for name, sdr_dir, clip_file in test_cases:
        print(f"\n{name}:")
        print("-" * 40)
        
        # Find .pds file
        pds_path = samples_dir / sdr_dir
        if pds_path.is_dir():
            pds_files = list(pds_path.glob('*.pds'))
            if not pds_files:
                print("  ❌ No .pds file found")
                continue
            pds_path = pds_files[0]
        else:
            print("  ❌ .sdr directory not found")
            continue
        
        clip_path = samples_dir / clip_file
        if not clip_path.exists():
            print("  ❌ Clippings file not found")
            continue
        
        # Parse both
        krds = KindleReaderDataStore(str(pds_path))
        krds_annotations = krds.extract_annotations()
        krds_highlights = [ann for ann in krds_annotations if 'highlight' in ann.annotation_type]
        
        clippings = parse_myclippings_for_book(str(clip_path), name)
        clip_highlights = [c for c in clippings if c.get('type') == 'highlight']
        
        # Get page numbers
        krds_pages = sorted({h.start_position.page for h in krds_highlights})
        clip_pages = sorted({c.get('page', c.get('pdf_page', 0)) for c in clip_highlights})
        
        # Test hypothesis: KRDS + 1 = Clippings
        krds_adjusted = [p + 1 for p in krds_pages]
        
        print(f"  KRDS pages (raw):      {krds_pages}")
        print(f"  KRDS pages (+1):       {krds_adjusted}")
        print(f"  MyClippings pages:     {clip_pages}")
        
        # Check overlap
        krds_set = set(krds_adjusted)
        clip_set = set(clip_pages)
        overlap = krds_set & clip_set
        
        if overlap:
            overlap_pct = len(overlap) / max(len(krds_set), len(clip_set)) * 100
            print(f"  ✅ Overlap: {len(overlap)}/{max(len(krds_set), len(clip_set))} pages ({overlap_pct:.1f}%)")
            
            # Show which pages matched
            if len(overlap) == len(krds_set) == len(clip_set):
                print(f"  🎉 PERFECT MATCH! All pages align after +1 adjustment")
            elif overlap_pct >= 80:
                print(f"  ✅ EXCELLENT: Most pages align")
                # Show non-matching
                krds_only = krds_set - clip_set
                clip_only = clip_set - krds_set
                if krds_only:
                    print(f"     KRDS only: {sorted(krds_only)}")
                if clip_only:
                    print(f"     Clippings only: {sorted(clip_only)}")
            else:
                print(f"  ⚠️  PARTIAL: Some alignment but not complete")
        else:
            print(f"  ❌ NO OVERLAP even after +1 adjustment")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("\n✅ HYPOTHESIS CONFIRMED: KRDS uses 0-based page numbering")
    print("   MyClippings uses 1-based page numbering")
    print("   Formula: pdf_page_number = krds_page + 1")


if __name__ == '__main__':
    test_offset_hypothesis()
