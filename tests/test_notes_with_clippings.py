#!/usr/bin/env python3
"""
Test to verify that notes with content are properly processed when MyClippings.txt is provided.
This test specifically checks that note content from MyClippings.txt is not lost.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations


def test_notes_with_clippings_file():
    """
    Test that notes are properly processed when MyClippings.txt is provided.
    
    According to the clippings file, there are two notes:
    1. Page 3: "A note attached to a single word" (attached to highlight "reasoning")
    2. Page 4: "Note for a paragraph and one word more" (attached to highlight "The Assassins...")
    """
    print("=" * 80)
    print("🧪 TESTING NOTES WITH MYCLIPPINGS.TXT")
    print("=" * 80)
    
    # Test files
    krds_file = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    clippings_file = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    book_name = 'peirce-charles-fixation-belief'
    
    # Create annotations WITH clippings file
    annotations = create_amazon_compliant_annotations(
        krds_file,
        clippings_file,
        book_name
    )
    
    print(f"\n📊 ANNOTATION SUMMARY:")
    print(f"   Total annotations: {len(annotations)}")
    
    # Separate by type
    highlights = [ann for ann in annotations if ann.get('type') == 'highlight']
    notes = [ann for ann in annotations if ann.get('type') == 'note']
    bookmarks = [ann for ann in annotations if ann.get('type') == 'bookmark']
    
    print(f"   Highlights: {len(highlights)}")
    print(f"   Notes: {len(notes)}")
    print(f"   Bookmarks: {len(bookmarks)}")
    
    # Check notes have content
    print(f"\n📝 NOTES DETAILS:")
    for i, note in enumerate(notes):
        page = note.get('pdf_page_0based', -1)
        content = note.get('content', '')
        print(f"   Note {i+1}:")
        print(f"     Page: {page + 1}")
        print(f"     Content: '{content}'")
        print(f"     Source: {note.get('source', 'unknown')}")
    
    # ASSERTIONS
    assert len(notes) >= 2, f"Expected at least 2 notes, found {len(notes)}"
    
    # Check note contents match what's in MyClippings.txt
    note_contents = [note.get('content', '').strip() for note in notes]
    
    expected_note_1 = "A note attached to a single word"
    expected_note_2 = "Note for a paragraph and one word more"
    
    print(f"\n✅ VERIFICATION:")
    
    # Check if expected note contents are present
    found_note_1 = any(expected_note_1 in content for content in note_contents)
    found_note_2 = any(expected_note_2 in content for content in note_contents)
    
    if found_note_1:
        print(f"   ✓ Found note 1: '{expected_note_1}'")
    else:
        print(f"   ✗ MISSING note 1: '{expected_note_1}'")
        print(f"     Actual note contents: {note_contents}")
    
    if found_note_2:
        print(f"   ✓ Found note 2: '{expected_note_2}'")
    else:
        print(f"   ✗ MISSING note 2: '{expected_note_2}'")
        print(f"     Actual note contents: {note_contents}")
    
    assert found_note_1, f"Note 1 content not found. Expected: '{expected_note_1}', Got: {note_contents}"
    assert found_note_2, f"Note 2 content not found. Expected: '{expected_note_2}', Got: {note_contents}"
    
    print(f"\n{'='*80}")
    print("✅ TEST PASSED: All notes have correct content from MyClippings.txt")
    print("="*80)


if __name__ == '__main__':
    try:
        test_notes_with_clippings_file()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
