#!/usr/bin/env python3
"""
End-to-End Integration Test
Tests the complete pipeline from KRDS files to annotated PDFs for all sample datasets.
"""

import sys
import fitz
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from src.pdf_processor.pdf_annotator import annotate_pdf_file


def check_pdf_quality(pdf_path: str, expected_highlights: int, book_name: str) -> dict:
    """
    Check the quality of an annotated PDF
    
    Returns:
        dict with 'success', 'highlights_count', 'issues' keys
    """
    issues = []
    
    try:
        doc = fitz.open(pdf_path)
        
        total_highlights = 0
        outside_bounds = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_rect = page.rect
            annots = page.annots()
            
            if annots:
                for annot in annots:
                    if annot.type[0] == 8:  # Highlight annotation
                        total_highlights += 1
                        rect = annot.rect
                        
                        # Check if within page bounds
                        if (rect.x0 < page_rect.x0 or rect.x1 > page_rect.x1 or 
                            rect.y0 < page_rect.y0 or rect.y1 > page_rect.y1):
                            outside_bounds += 1
                            issues.append(f"Page {page_num + 1}: Highlight extends beyond page bounds")
        
        doc.close()
        
        # Check if we got the expected number of highlights
        if total_highlights != expected_highlights:
            issues.append(f"Expected {expected_highlights} highlights, found {total_highlights}")
        
        if outside_bounds > 0:
            issues.append(f"{outside_bounds} highlights extend beyond page bounds")
        
        return {
            'success': len(issues) == 0,
            'highlights_count': total_highlights,
            'outside_bounds': outside_bounds,
            'issues': issues
        }
        
    except Exception as e:
        return {
            'success': False,
            'highlights_count': 0,
            'outside_bounds': 0,
            'issues': [f"Error opening PDF: {e}"]
        }


def run_dataset_test(dataset_info: dict) -> bool:
    """
    Test a single dataset through the complete pipeline
    
    Returns:
        True if successful, False otherwise
    """
    name = dataset_info['name']
    krds = dataset_info['krds']
    clippings = dataset_info['clippings']
    source_pdf = dataset_info['pdf']
    expected_highlights = dataset_info['expected_highlights']
    
    print(f"\n{'='*70}")
    print(f"📚 Testing: {name}")
    print(f"{'='*70}")
    
    output_pdf = f"tests/output/{name}_integrated.pdf"
    
    # Step 1: Create Amazon annotations
    print(f"1️⃣ Creating Amazon annotations from KRDS...")
    try:
        amazon_annotations = create_amazon_compliant_annotations(krds, clippings, name)
        print(f"   ✓ Created {len(amazon_annotations)} annotations")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Step 2: Convert to PDF annotator format
    print(f"2️⃣ Converting to PDF annotator format...")
    try:
        pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
        print(f"   ✓ Converted {len(pdf_annotations)} annotations")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Step 3: Annotate PDF
    print(f"3️⃣ Creating annotated PDF...")
    try:
        success = annotate_pdf_file(source_pdf, pdf_annotations, output_path=output_pdf)
        if success:
            print(f"   ✓ Created: {output_pdf}")
        else:
            print(f"   ✗ Failed to create PDF")
            return False
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Step 4: Verify quality
    print(f"4️⃣ Verifying PDF quality...")
    quality = check_pdf_quality(output_pdf, expected_highlights, name)
    
    if quality['success']:
        print(f"   ✅ Quality check PASSED")
        print(f"      - {quality['highlights_count']} highlights correctly positioned")
    else:
        print(f"   ❌ Quality check FAILED")
        for issue in quality['issues']:
            print(f"      - {issue}")
        return False
    
    return True


def test_end_to_end_integration():
    """
    Run end-to-end integration test for all sample datasets
    """
    print("🎯 END-TO-END INTEGRATION TEST")
    print("="*70)
    print("Testing complete pipeline: KRDS → Annotations → Annotated PDF")
    print("="*70)
    
    # Ensure output directory exists
    output_dir = Path("tests/output")
    output_dir.mkdir(exist_ok=True)
    
    # Define all test datasets
    datasets = [
        {
            'name': 'peirce-charles-fixation-belief',
            'krds': 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds',
            'clippings': 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt',
            'pdf': 'examples/sample_data/peirce-charles-fixation-belief.pdf',
            'expected_highlights': 8
        },
        {
            'name': 'Downey_2024_Theatre_Hunger_Scaling_Up_Paper',
            'krds': "examples/sample_data/Downey_2024_Theatre_Hunger_Scaling_Up_Paper.sdr/Downey - 2024 - Theatre Hunger An Underestimated 'Scaling Up' Pro.pdf-cdeKey_WAY5I3SIILOP6F4ROJNHQ5YIIEUBUDRT12347ea8efc3f766707171e2bfcc00f4.pds",
            'clippings': 'examples/sample_data/Downey_2024_Theatre_Hunger_Scaling_Up_Paper-clippings.txt',
            'pdf': 'examples/sample_data/Downey_2024_Theatre_Hunger_Scaling_Up_Paper.pdf',
            'expected_highlights': 7
        },
        {
            'name': '659ec7697e419',
            'krds': 'examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ12347ea8efc3f766707171e2bfcc00f4.pds',
            'clippings': 'examples/sample_data/659ec7697e419-clippings.txt',
            'pdf': 'examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf',
            'expected_highlights': 4
        }
    ]
    
    # Run tests
    results = {}
    for dataset in datasets:
        results[dataset['name']] = run_dataset_test(dataset)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 INTEGRATION TEST SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{'='*70}")
    if passed == total:
        print(f"✅ SUCCESS: All {total} datasets passed!")
        print(f"\n📁 Output PDFs:")
        for dataset in datasets:
            pdf_path = f"tests/output/{dataset['name']}_integrated.pdf"
            print(f"   - {pdf_path}")
        return True
    else:
        print(f"❌ FAILURE: {passed}/{total} datasets passed")
        return False


if __name__ == '__main__':
    success = test_end_to_end_integration()
    sys.exit(0 if success else 1)
