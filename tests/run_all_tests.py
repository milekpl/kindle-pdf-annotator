#!/usr/bin/env python3
"""
Run all tests in the tests directory
"""

import sys
import subprocess
from pathlib import Path

def run_test(test_file: Path) -> bool:
    """Run a single test file"""
    print(f"\n{'='*70}")
    print(f"Running: {test_file.name}")
    print('='*70)
    
    result = subprocess.run(
        [sys.executable, str(test_file)],
        cwd=test_file.parent.parent,
        capture_output=False
    )
    
    return result.returncode == 0


def main():
    """Run all tests"""
    tests_dir = Path(__file__).parent
    
    # List of test files to run (in order)
    test_files = [
        'test_short_text_filtering.py',     # Unit tests for short text filtering
        'test_integration_end_to_end.py',  # Main integration test
        'test_peirce_text_coverage.py',    # Text coverage validation
        'test_highlight_positions.py',      # Position verification
        'test_highlight_width_coverage.py', # Width coverage validation
    ]
    
    results = {}
    
    print("🧪 RUNNING ALL TESTS")
    print("="*70)
    
    for test_name in test_files:
        test_path = tests_dir / test_name
        if test_path.exists():
            results[test_name] = run_test(test_path)
        else:
            print(f"⚠️  Test file not found: {test_name}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print('='*70)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n{'='*70}")
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
