#!/usr/bin/env python3
"""
Empirical analysis: Do PDT files contain annotations?

This script scans a dataset of Kindle files to check whether .pdt files
ever contain any annotations, compared to .pds files.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from kindle_parser.krds_parser import KindleReaderDataStore


def analyze_pdt_vs_pds_annotations(dataset_path: str):
    """
    Test whether PDT files contain annotations by scanning a dataset.
    
    Args:
        dataset_path: Path to the dataset directory (e.g., 'learn/documents')
    """
    dataset = Path(dataset_path)
    
    if not dataset.exists():
        print(f"❌ Dataset not found: {dataset}")
        return
    
    print("=" * 80)
    print("📊 TESTING: Do PDT files contain annotations?")
    print("=" * 80)
    print(f"Dataset: {dataset}")
    print()
    
    # Find all PDS and PDT files
    pds_files = list(dataset.rglob("*.pds"))
    pdt_files = list(dataset.rglob("*.pdt"))
    
    print(f"Found {len(pds_files)} PDS files")
    print(f"Found {len(pdt_files)} PDT files")
    print()
    
    # Test PDS files
    print("=" * 80)
    print("🔍 TESTING PDS FILES (baseline)")
    print("=" * 80)
    
    pds_with_annotations = 0
    pds_total_annotations = 0
    pds_sample_results = []
    
    for i, pds_file in enumerate(pds_files[:20]):  # Test first 20
        try:
            krds = KindleReaderDataStore(str(pds_file))
            annotations = krds.extract_annotations()
            
            if len(annotations) > 0:
                pds_with_annotations += 1
                pds_total_annotations += len(annotations)
                pds_sample_results.append((pds_file.name, len(annotations)))
        except Exception as e:
            print(f"   ⚠️  Error parsing {pds_file.name}: {e}")
    
    print(f"\nPDS Results (first 20):")
    print(f"  Files with annotations: {pds_with_annotations}/20")
    print(f"  Total annotations: {pds_total_annotations}")
    print(f"  Average: {pds_total_annotations / 20 if pds_with_annotations > 0 else 0:.1f} per file")
    
    if pds_sample_results:
        print(f"\n  Sample files with annotations:")
        for filename, count in pds_sample_results[:5]:
            print(f"    - {filename}: {count} annotations")
    
    # Test PDT files
    print("\n" + "=" * 80)
    print("🔍 TESTING PDT FILES (hypothesis: no annotations)")
    print("=" * 80)
    
    pdt_with_annotations = 0
    pdt_total_annotations = 0
    pdt_sample_results = []
    
    for i, pdt_file in enumerate(pdt_files[:20]):  # Test first 20
        try:
            krds = KindleReaderDataStore(str(pdt_file))
            annotations = krds.extract_annotations()
            
            if len(annotations) > 0:
                pdt_with_annotations += 1
                pdt_total_annotations += len(annotations)
                pdt_sample_results.append((pdt_file.name, len(annotations)))
                print(f"   🚨 FOUND ANNOTATIONS in {pdt_file.name}: {len(annotations)} annotations")
        except Exception as e:
            print(f"   ⚠️  Error parsing {pdt_file.name}: {e}")
    
    print(f"\nPDT Results (first 20):")
    print(f"  Files with annotations: {pdt_with_annotations}/20")
    print(f"  Total annotations: {pdt_total_annotations}")
    print(f"  Average: {pdt_total_annotations / 20 if pdt_with_annotations > 0 else 0:.1f} per file")
    
    if pdt_sample_results:
        print(f"\n  🚨 PDT files with annotations (UNEXPECTED!):")
        for filename, count in pdt_sample_results:
            print(f"    - {filename}: {count} annotations")
    else:
        print(f"\n  ✅ NO PDT files had annotations (hypothesis confirmed!)")
    
    # Test ALL PDT files if dataset is small
    print("\n" + "=" * 80)
    print("🔍 TESTING ALL PDT FILES")
    print("=" * 80)
    
    if len(pdt_files) <= 100:
        print(f"Testing all {len(pdt_files)} PDT files...")
        
        pdt_all_with_annotations = 0
        pdt_all_total_annotations = 0
        
        for pdt_file in pdt_files:
            try:
                krds = KindleReaderDataStore(str(pdt_file))
                annotations = krds.extract_annotations()
                
                if len(annotations) > 0:
                    pdt_all_with_annotations += 1
                    pdt_all_total_annotations += len(annotations)
                    print(f"   🚨 {pdt_file.name}: {len(annotations)} annotations")
            except Exception as e:
                pass  # Silent failures
        
        print(f"\nAll PDT Results:")
        print(f"  Files with annotations: {pdt_all_with_annotations}/{len(pdt_files)}")
        print(f"  Total annotations: {pdt_all_total_annotations}")
        
        if pdt_all_with_annotations == 0:
            print(f"\n✅✅✅ HYPOTHESIS CONFIRMED: NO PDT files contain annotations!")
        else:
            print(f"\n❌❌❌ HYPOTHESIS REJECTED: {pdt_all_with_annotations} PDT files have annotations")
    else:
        print(f"Dataset too large ({len(pdt_files)} files), skipping exhaustive test")
    
    # Final conclusion
    print("\n" + "=" * 80)
    print("📋 CONCLUSION")
    print("=" * 80)
    
    if pdt_with_annotations == 0:
        print("✅ PDT files appear to contain NO annotations")
        print("   → Recommendation: Skip processing PDT files to avoid duplicates")
        print("   → Only process PDS files for annotations")
    else:
        print("⚠️  Some PDT files DO contain annotations")
        print("   → Need to investigate what PDT files actually store")
        print(f"   → {pdt_with_annotations} out of {min(20, len(pdt_files))} tested PDT files had annotations")


if __name__ == "__main__":
    import sys
    
    # Default to learn/documents if no argument provided
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else "learn/documents"
    
    analyze_pdt_vs_pds_annotations(dataset_path)
