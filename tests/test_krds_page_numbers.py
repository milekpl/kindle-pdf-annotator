#!/usr/bin/env python3
"""
Test to verify KRDS parser correctly reads page numbers by comparing
with MyClippings data for the same highlights.

This test uses the 4 sample PDFs in examples/sample_data/ which have both:
1. .pds files (KRDS data)
2. -clippings.txt files (MyClippings data)

We'll check if page numbers match between the two sources.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.krds_parser import KindleReaderDataStore
from kindle_parser.clippings_parser import parse_myclippings_for_book


class PageNumberValidator:
    """Validate KRDS page numbers against MyClippings."""
    
    def __init__(self):
        self.results = []
    
    def test_sample(self, pdf_name: str, pdf_path: Path, pds_path: Path, clippings_path: Path):
        """Test one sample PDF."""
        print(f"\n{'='*80}")
        print(f"Testing: {pdf_name}")
        print(f"{'='*80}")
        
        # Parse KRDS
        try:
            krds = KindleReaderDataStore(str(pds_path))
            krds_annotations = krds.extract_annotations()
            krds_highlights = [ann for ann in krds_annotations if 'highlight' in ann.annotation_type]
        except Exception as e:
            print(f"❌ Failed to parse KRDS: {e}")
            return
        
        # Parse MyClippings
        try:
            clippings = parse_myclippings_for_book(str(clippings_path), pdf_name)
            clip_highlights = [c for c in clippings if c.get('type') == 'highlight']
        except Exception as e:
            print(f"❌ Failed to parse MyClippings: {e}")
            return
        
        print(f"\nKRDS highlights: {len(krds_highlights)}")
        print(f"MyClippings highlights: {len(clip_highlights)}")
        
        if len(krds_highlights) == 0 or len(clip_highlights) == 0:
            print("⚠️  No highlights to compare")
            return
        
        # Show KRDS page numbers
        krds_pages = sorted(set(h.start_position.page for h in krds_highlights))
        print(f"\nKRDS pages: {krds_pages[:20]}")
        
        # Show MyClippings page numbers
        clip_pages = sorted(set(c.get('page', c.get('pdf_page', 0)) for c in clip_highlights))
        print(f"MyClippings pages: {clip_pages[:20]}")
        
        # Check if they overlap
        krds_set = set(krds_pages)
        clip_set = set(clip_pages)
        overlap = krds_set & clip_set
        
        print(f"\nPage number overlap: {len(overlap)} common pages")
        if overlap:
            print(f"Common pages: {sorted(overlap)[:10]}")
        
        # Show first few highlights with text from both sources
        print(f"\n{'='*80}")
        print("Detailed comparison:")
        print(f"{'='*80}")
        
        for i, krds_hl in enumerate(krds_highlights[:5]):
            print(f"\nKRDS Highlight #{i+1}:")
            print(f"  Page: {krds_hl.start_position.page}")
            print(f"  Position: ({krds_hl.start_position.x}, {krds_hl.start_position.y})")
            print(f"  Size: {krds_hl.start_position.width} x {krds_hl.start_position.height}")
            
            # Try to find matching clipping on same page
            matching_clips = [c for c in clip_highlights 
                            if c.get('page', c.get('pdf_page', 0)) == krds_hl.start_position.page]
            
            if matching_clips:
                print(f"  ✅ Found {len(matching_clips)} MyClippings highlight(s) on same page")
                for clip in matching_clips[:1]:
                    text = clip.get('content', '')[:60]
                    print(f"     Text: \"{text}...\"")
            else:
                print(f"  ❌ No MyClippings highlight on page {krds_hl.start_position.page}")
        
        # Store results
        self.results.append({
            'pdf': pdf_name,
            'krds_count': len(krds_highlights),
            'clip_count': len(clip_highlights),
            'krds_pages': krds_pages,
            'clip_pages': clip_pages,
            'overlap': len(overlap),
            'overlap_pages': sorted(overlap)
        })
    
    def run_all_tests(self):
        """Run tests on all sample PDFs."""
        samples_dir = Path('examples/sample_data')
        
        # Define test cases
        test_cases = [
            {
                'name': '659ec7697e419',
                'pdf': samples_dir / '659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf',
                'pds': samples_dir / '659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr',
                'clippings': samples_dir / '659ec7697e419-clippings.txt'
            },
            {
                'name': 'Downey_2024',
                'pdf': samples_dir / 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper.pdf',
                'pds': samples_dir / 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper.sdr',
                'clippings': samples_dir / 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper-clippings.txt'
            },
            {
                'name': 'page_136_shea',
                'pdf': samples_dir / 'page_136_shea.pdf',
                'pds': samples_dir / 'page_136_shea.sdr',
                'clippings': samples_dir / 'page_136_shea-clippings.txt'
            },
            {
                'name': 'peirce-charles',
                'pdf': samples_dir / 'peirce-charles-fixation-belief.pdf',
                'pds': samples_dir / 'peirce-charles-fixation-belief.sdr',
                'clippings': samples_dir / 'peirce-charles-fixation-belief-clippings.txt'
            }
        ]
        
        for test_case in test_cases:
            # Find .pds file in .sdr directory
            if test_case['pds'].is_dir():
                pds_files = list(test_case['pds'].glob('*.pds'))
                if pds_files:
                    pds_path = pds_files[0]
                else:
                    print(f"\n❌ No .pds file found for {test_case['name']}")
                    continue
            else:
                print(f"\n❌ .sdr directory not found for {test_case['name']}")
                continue
            
            if not test_case['clippings'].exists():
                print(f"\n❌ Clippings file not found for {test_case['name']}")
                continue
            
            self.test_sample(
                test_case['name'],
                test_case['pdf'],
                pds_path,
                test_case['clippings']
            )
        
        # Print summary
        print(f"\n\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        
        for result in self.results:
            print(f"\n{result['pdf']}:")
            print(f"  KRDS highlights: {result['krds_count']}")
            print(f"  MyClippings highlights: {result['clip_count']}")
            print(f"  Page overlap: {result['overlap']} pages")
            
            if result['overlap'] > 0:
                overlap_pct = (result['overlap'] / min(len(result['krds_pages']), len(result['clip_pages'])) * 100)
                print(f"  Overlap percentage: {overlap_pct:.1f}%")
                
                if overlap_pct > 80:
                    print(f"  ✅ GOOD: High page number agreement")
                elif overlap_pct > 50:
                    print(f"  ⚠️  PARTIAL: Some page number agreement")
                else:
                    print(f"  ❌ BAD: Low page number agreement")
            else:
                print(f"  ❌ CRITICAL: NO page number overlap!")
        
        # Check if there's a pattern in page number differences
        print(f"\n\n{'='*80}")
        print("PAGE NUMBER OFFSET ANALYSIS")
        print(f"{'='*80}")
        
        for result in self.results:
            if result['krds_pages'] and result['clip_pages']:
                krds_min = min(result['krds_pages'])
                clip_min = min(result['clip_pages'])
                offset = krds_min - clip_min
                
                print(f"\n{result['pdf']}:")
                print(f"  KRDS min page: {krds_min}")
                print(f"  MyClippings min page: {clip_min}")
                print(f"  Offset: {offset}")
                
                if offset == 0:
                    print(f"  ✅ No offset")
                elif offset == 1:
                    print(f"  ⚠️  Possible 1-based vs 0-based indexing difference")
                else:
                    print(f"  ❌ Significant offset - different numbering schemes")


if __name__ == '__main__':
    validator = PageNumberValidator()
    validator.run_all_tests()
