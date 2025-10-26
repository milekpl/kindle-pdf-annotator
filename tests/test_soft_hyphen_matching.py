"""
Test soft hyphen and mixed hyphenation matching strategies.

This test file experiments with the complex page 136 case from Shea PDF:
- Regular hyphen + newline: con-\n
- Soft hyphens: plug-\xadand-\xadplay  
- Combined: special-\xad\npurpose

Goal: Find the most robust way to match clippings with such complexity.
"""

from difflib import SequenceMatcher
from typing import Optional, List, Tuple


# Real data from Shea PDF page 136
PDF_TEXT_RAW = "A con-\ncept is a plug-\xadand-\xadplay device with plugs at both ends. It provides an interface between the informational models and content-\xadspecific computations of special-\xad\npurpose systems, at one end, and the general-\xadpurpose compositionality and content-\xadgeneral reasoning of deliberate thought, at the other."

# What Kindle's My Clippings.txt shows (correct extraction)
CLIPPING_CORRECT = "A concept is a plug-and-play device with plugs at both ends. It provides an interface between the informational models and content-specific computations of special-purpose systems, at one end, and the general-purpose compositionality and content-general reasoning of deliberate thought, at the other."

# What Kindle actually extracted (with errors)
CLIPPING_WITH_ERRORS = "A concept is a plug-and-play device with plugs at both ends. It provides an interface between the informational models and content-specifc computations of specialpurpose systems, at one end, and the general-purpose compositionality and content-general reasoning of deliberate thought, at the other."


def normalize_pdf_text(text: str) -> str:
    """
    Normalize PDF text to match what Kindle would extract.
    
    Removes:
    - Soft hyphens (U+00AD: \xad)
    - Hyphen + newline combinations
    - Normalizes whitespace
    """
    # Handle combined patterns first (most specific to least specific)
    text = text.replace('-\u00ad\n', '-')  # hyphen + soft hyphen + newline → hyphen
    text = text.replace('-\xad\n', '-')     # Same, different escape notation
    
    # Remove remaining soft hyphens
    text = text.replace('\u00ad', '')
    text = text.replace('\xad', '')
    
    # Remove hyphen + newline (hyphenated words at line break)
    text = text.replace('-\n', '')
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text


def normalize_clipping_text(text: str) -> str:
    """
    Normalize clipping text for matching.
    Just normalize whitespace - clipping should already be clean.
    """
    return ' '.join(text.split())


def test_basic_normalization():
    """Test that normalization produces expected results."""
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping = normalize_clipping_text(CLIPPING_CORRECT)
    
    print("=" * 80)
    print("TEST: Basic Normalization")
    print("=" * 80)
    print(f"Raw PDF text (first 100 chars):\n{PDF_TEXT_RAW[:100]!r}\n")
    print(f"Normalized PDF text (first 100 chars):\n{normalized_pdf[:100]!r}\n")
    print(f"Normalized clipping (first 100 chars):\n{normalized_clipping[:100]!r}\n")
    
    # They should match exactly if clipping is correct
    assert normalized_pdf == normalized_clipping, "Normalized texts should match exactly"
    print("✓ PERFECT MATCH after normalization!")


def test_clipping_with_errors():
    """Test matching when clipping has extraction errors."""
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping_err = normalize_clipping_text(CLIPPING_WITH_ERRORS)
    
    print("\n" + "=" * 80)
    print("TEST: Clipping with Extraction Errors")
    print("=" * 80)
    print(f"Clipping with errors: ...{CLIPPING_WITH_ERRORS[100:150]}...")
    print("  - 'content-specifc' (missing 'i')")
    print("  - 'specialpurpose' (no space/hyphen)")
    print()
    
    # Verify that normalized clipping does NOT match PDF (due to errors)
    assert normalized_clipping_err not in normalized_pdf, "Clipping with errors should not match PDF exactly"
    print("✓ Confirmed: No exact match due to Kindle extraction errors")
    
    # Verify specific error patterns exist in clipping
    assert 'content-specifc' in normalized_clipping_err, "Expected misspelling 'content-specifc' in clipping"
    assert 'specialpurpose' in normalized_clipping_err, "Expected 'specialpurpose' without hyphen in clipping"
    
    # Verify correct forms exist in PDF
    assert 'content-specific' in normalized_pdf, "Expected correct 'content-specific' in PDF"
    assert 'special-purpose' in normalized_pdf, "Expected 'special-purpose' with hyphen in PDF"
    print("✓ Error patterns verified")


def test_anchor_based_matching():
    """
    Test anchor-based matching strategy:
    1. Find beginning anchor (first N words) in PDF
    2. Find ending anchor (last N words) in PDF
    3. Extract text between anchors
    4. Verify character count matches
    """
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping = normalize_clipping_text(CLIPPING_CORRECT)
    
    print("\n" + "=" * 80)
    print("TEST: Anchor-Based Matching")
    print("=" * 80)
    
    # Try with 5-word anchors (should work)
    anchor_size = 5
    print(f"\nTrying anchor size: {anchor_size} words")
    
    # Extract anchors from clipping
    begin_anchor = extract_anchor_words(normalized_clipping, anchor_size, from_end=False)
    end_anchor = extract_anchor_words(normalized_clipping, anchor_size, from_end=True)
    
    print(f"  Begin anchor: '{begin_anchor}'")
    print(f"  End anchor: '{end_anchor}'")
    
    # Find anchors in PDF
    begin_pos = normalized_pdf.find(begin_anchor)
    end_pos = normalized_pdf.find(end_anchor)
    
    assert begin_pos != -1, f"Beginning anchor not found: {begin_anchor}"
    assert end_pos != -1, f"Ending anchor not found: {end_anchor}"
    
    print(f"  ✓ Begin anchor found at position {begin_pos}")
    print(f"  ✓ End anchor found at position {end_pos}")
    
    # Calculate end position (end of last word)
    end_pos_complete = end_pos + len(end_anchor)
    
    # Extract text between anchors
    extracted = normalized_pdf[begin_pos:end_pos_complete]
    
    print(f"  Extracted length: {len(extracted)} chars")
    print(f"  Expected length: {len(normalized_clipping)} chars")
    
    # Compare
    assert extracted == normalized_clipping, "Extracted text should match clipping exactly"
    print(f"  ✓✓✓ PERFECT MATCH with {anchor_size}-word anchors!")


def test_fuzzy_anchor_matching():
    """
    Test fuzzy anchor matching when exact anchors fail.
    Uses edit distance or character-by-character matching.
    """
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping_err = normalize_clipping_text(CLIPPING_WITH_ERRORS)
    
    print("\n" + "=" * 80)
    print("TEST: Fuzzy Anchor Matching (for extraction errors)")
    print("=" * 80)
    
    # Strategy: Find beginning with fuzzy match, then extract clipping length
    anchor_size = 5
    begin_anchor = extract_anchor_words(normalized_clipping_err, anchor_size, from_end=False)
    
    print(f"Begin anchor from error clipping: '{begin_anchor}'")
    
    # Try to find it in PDF
    begin_pos = normalized_pdf.find(begin_anchor)
    
    assert begin_pos != -1, "Beginning anchor should be found despite errors"
    print(f"✓ Found beginning at position {begin_pos}")
    
    # Extract clipping length from that position
    clipping_len = len(normalized_clipping_err)
    extracted = normalized_pdf[begin_pos:begin_pos + clipping_len]
    
    # Calculate similarity
    matching_chars = sum(1 for c1, c2 in zip(extracted, normalized_clipping_err) if c1 == c2)
    similarity = matching_chars / max(len(extracted), len(normalized_clipping_err))
    
    print(f"\nSimilarity: {similarity:.1%} ({matching_chars}/{max(len(extracted), len(normalized_clipping_err))} chars match)")
    
    # Should have reasonably high similarity despite errors
    assert similarity > 0.40, f"Similarity should be >40%, got {similarity:.1%}"
    print(f"✓ Similarity check passed: {similarity:.1%}")


def test_position_based_extraction():
    """
    Test fuzzy anchor matching when exact anchors fail.
    Uses edit distance or character-by-character matching.
    """
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping_err = normalize_clipping_text(CLIPPING_WITH_ERRORS)
    
    print("\n" + "=" * 80)
    print("TEST: Fuzzy Anchor Matching (for extraction errors)")
    print("=" * 80)
    
    # Strategy: Find beginning with fuzzy match, then extract clipping length
    anchor_size = 5
    begin_anchor = extract_anchor_words(normalized_clipping_err, anchor_size, from_end=False)
    
    print(f"Begin anchor from error clipping: '{begin_anchor}'")
    
    # Try to find it in PDF
    begin_pos = normalized_pdf.find(begin_anchor)
    
    if begin_pos != -1:
        print(f"✓ Found beginning at position {begin_pos}")
        
        # Extract clipping length from that position
        clipping_len = len(normalized_clipping_err)
        extracted = normalized_pdf[begin_pos:begin_pos + clipping_len]
        
        print(f"Extracted {len(extracted)} chars: '{extracted[:80]}...'")
        print(f"Expected {clipping_len} chars: '{normalized_clipping_err[:80]}...'")
        
        # Calculate similarity
        matching_chars = sum(1 for c1, c2 in zip(extracted, normalized_clipping_err) if c1 == c2)
        similarity = matching_chars / max(len(extracted), len(normalized_clipping_err))
        
        print(f"\nSimilarity: {similarity:.1%} ({matching_chars}/{max(len(extracted), len(normalized_clipping_err))} chars match)")
        
        if similarity > 0.95:
            print("✓ HIGH SIMILARITY - Would accept this match!")
            return True
        else:
            print("✗ Low similarity - would reject")
            # Show some differences
            print("\nFirst few differences:")
            diff_count = 0
            for i, (c1, c2) in enumerate(zip(extracted, normalized_clipping_err)):
                if c1 != c2:
                    print(f"  Position {i}: PDF='{c1}' vs Clipping='{c2}'")
                    print(f"    PDF context: ...{extracted[max(0,i-15):i+15]}...")
                    print(f"    Clipping: ...{normalized_clipping_err[max(0,i-15):i+15]}...")
                    diff_count += 1
                    if diff_count >= 3:
                        break
    else:
        print("✗ Beginning anchor not found")
    
    return False


def position_based_extraction():
    """
    Test position-based extraction strategy:
    1. Find first character of clipping in PDF (match first few words)
    2. Extract exactly N characters where N = len(clipping)
    3. Verify last few words match
    
    This avoids searching for the full text with all its hyphenation variants.
    """
    print("\n" + "=" * 80)
    print("TEST: Position-Based Extraction")
    print("=" * 80)
    print("Strategy: Find start position, extract clipping length, verify end")
    print()
    
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping = normalize_clipping_text(CLIPPING_CORRECT)
    
    # Find beginning (first 5 words)
    begin_words = 5
    begin_anchor = extract_anchor_words(normalized_clipping, begin_words, from_end=False)
    begin_pos = normalized_pdf.find(begin_anchor)
    
    if begin_pos == -1:
        print(f"✗ Cannot find beginning: '{begin_anchor}'")
        return False
    
    print(f"✓ Found beginning at position {begin_pos}")
    print(f"  Searching for: '{begin_anchor}'")
    
    # Extract exact clipping length
    clipping_len = len(normalized_clipping)
    extracted = normalized_pdf[begin_pos:begin_pos + clipping_len]
    
    print(f"\n✓ Extracted {len(extracted)} characters (expected {clipping_len})")
    
    # Verify ending matches
    end_words = 5
    extracted_end = extract_anchor_words(extracted, end_words, from_end=True)
    expected_end = extract_anchor_words(normalized_clipping, end_words, from_end=True)
    
    print(f"\nVerifying end:")
    print(f"  Extracted end: '{extracted_end}'")
    print(f"  Expected end: '{expected_end}'")
    
    if extracted_end == expected_end:
        print("  ✓ End matches!")
        
        # Final check: exact match?
        if extracted == normalized_clipping:
            print("\n✓✓✓ PERFECT MATCH!")
            print("This strategy works for clean clippings!")
            return True
        else:
            print("\n⚠ Ends match but full text differs slightly")
            # Show first difference
            for i, (c1, c2) in enumerate(zip(extracted, normalized_clipping)):
                if c1 != c2:
                    print(f"  First diff at position {i}: '{c1}' vs '{c2}'")
                    break
            return False
    else:
        print("  ✗ End doesn't match - extraction boundaries wrong")
        return False


def position_based_with_errors():
    """Test position-based extraction with Kindle errors."""
    print("\n" + "=" * 80)
    print("TEST: Position-Based Extraction with Kindle Errors (SIMPLE)")
    print("=" * 80)
    
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping_err = normalize_clipping_text(CLIPPING_WITH_ERRORS)
    
    # The beginning should match even with errors (errors are later)
    begin_words = 5
    begin_anchor = extract_anchor_words(normalized_clipping_err, begin_words, from_end=False)
    begin_pos = normalized_pdf.find(begin_anchor)
    
    if begin_pos == -1:
        print(f"✗ Cannot find beginning: '{begin_anchor}'")
        return False
    
    print(f"✓ Found beginning at position {begin_pos}")
    
    # Extract clipping length
    clipping_len = len(normalized_clipping_err)
    extracted = normalized_pdf[begin_pos:begin_pos + clipping_len]
    
    print(f"✓ Extracted {len(extracted)} characters")
    
    # Check similarity instead of exact match
    matching_chars = sum(1 for c1, c2 in zip(extracted, normalized_clipping_err) if c1 == c2)
    similarity = matching_chars / max(len(extracted), len(normalized_clipping_err))
    
    print(f"\nSimilarity: {similarity:.1%}")
    
    # Verify end words with fuzzy matching
    end_words = 5
    extracted_end = extract_anchor_words(extracted, end_words, from_end=True)
    expected_end = extract_anchor_words(normalized_clipping_err, end_words, from_end=True)
    
    print("\nEnd verification:")
    print(f"  Extracted: '{extracted_end}'")
    print(f"  Expected: '{expected_end}'")
    
    if extracted_end == expected_end:
        print("  ✓ Ends match exactly!")
    else:
        # Calculate end similarity
        end_matching = sum(1 for c1, c2 in zip(extracted_end, expected_end) if c1 == c2)
        end_similarity = end_matching / max(len(extracted_end), len(expected_end))
        print(f"  End similarity: {end_similarity:.1%}")
    
    # Decision threshold
    if similarity > 0.95:
        print(f"\n✓✓ ACCEPT: {similarity:.1%} similarity is sufficient!")
        print("This strategy works even with extraction errors!")
        return True
    else:
        print(f"\n✗ REJECT: {similarity:.1%} similarity too low")
        return False


def position_based_with_flexible_length():
    """
    Test position-based extraction with flexible length adjustment.
    
    Strategy:
    1. Find beginning anchor
    2. Find ending anchor in a sliding window
    3. Extract text between anchors (handles length differences)
    """
    print("\n" + "=" * 80)
    print("TEST: Position-Based with Flexible Length (SMART)")
    print("=" * 80)
    print("Strategy: Find both anchors in PDF, extract between them")
    print()
    
    normalized_pdf = normalize_pdf_text(PDF_TEXT_RAW)
    normalized_clipping_err = normalize_clipping_text(CLIPPING_WITH_ERRORS)
    
    # Find beginning
    begin_words = 5
    begin_anchor = extract_anchor_words(normalized_clipping_err, begin_words, from_end=False)
    begin_pos = normalized_pdf.find(begin_anchor)
    
    if begin_pos == -1:
        print(f"✗ Cannot find beginning: '{begin_anchor}'")
        return False
    
    print(f"✓ Found beginning at position {begin_pos}")
    print(f"  Anchor: '{begin_anchor}'")
    
    # Find ending - search in a LARGE window to handle length differences
    end_words = 5
    end_anchor = extract_anchor_words(normalized_clipping_err, end_words, from_end=True)
    
    # Use a LARGE window because Kindle text length differs from PDF
    # The window should cover at least ±10% of expected text length
    clipping_len = len(normalized_clipping_err)
    window_margin = max(50, int(clipping_len * 0.1))  # At least 50 chars or 10%
    
    search_start = max(0, begin_pos + clipping_len - window_margin)
    search_end = min(len(normalized_pdf), begin_pos + clipping_len + window_margin)
    search_window = normalized_pdf[search_start:search_end]
    
    print(f"\n✓ Searching for ending anchor in window")
    print(f"  Anchor: '{end_anchor}'")
    print(f"  Window: positions {search_start} to {search_end} ({len(search_window)} chars)")
    
    end_pos_in_window = search_window.find(end_anchor)
    
    if end_pos_in_window == -1:
        print("  ✗ Ending anchor not found in window")
        # Try searching in full text as fallback
        print("  Trying full text search...")
        end_pos_actual = normalized_pdf.find(end_anchor, begin_pos)
        if end_pos_actual == -1:
            print("  ✗ Ending anchor not found in full text either")
            return False
        print(f"  ✓ Found in full text at position {end_pos_actual}")
    else:
        # Calculate actual end position in full text
        end_pos_actual = search_start + end_pos_in_window
        print(f"  ✓ Found ending at position {end_pos_actual}")
    
    end_pos_complete = end_pos_actual + len(end_anchor)
    
    # Extract text between anchors
    extracted = normalized_pdf[begin_pos:end_pos_complete]
    
    print(f"\n✓ Extracted {len(extracted)} characters (clipping was {clipping_len})")
    print(f"  Length difference: {len(extracted) - clipping_len} chars")
    
    # Use SequenceMatcher for similarity (handles insertions/deletions)
    matcher = SequenceMatcher(None, extracted, normalized_clipping_err)
    similarity = matcher.ratio()
    
    print("\nSimilarity check (using SequenceMatcher):")
    print(f"  Similarity: {similarity:.1%}")
    
    # Also check word-level similarity
    extracted_words = extracted.split()
    clipping_words = normalized_clipping_err.split()
    word_matches = sum(1 for w1, w2 in zip(extracted_words, clipping_words) if w1 == w2)
    word_similarity = word_matches / max(len(extracted_words), len(clipping_words))
    print(f"  Word-level similarity: {word_similarity:.1%} ({word_matches}/{max(len(extracted_words), len(clipping_words))} words)")
    
    # More lenient threshold since we expect some differences
    if similarity > 0.90:
        print(f"\n✓✓ ACCEPT: {similarity:.1%} similarity is sufficient!")
        print("This strategy handles length differences from extraction errors!")
        return True
    else:
        print(f"\n✗ REJECT: {similarity:.1%} similarity too low (need >90%)")
        # Show word-level differences
        print("\nWord differences:")
        diff_count = 0
        for i, (w1, w2) in enumerate(zip(extracted_words, clipping_words)):
            if w1 != w2:
                print(f"  Word {i}: PDF='{w1}' vs Kindle='{w2}'")
                diff_count += 1
                if diff_count >= 3:
                    break
        return False


def extract_anchor_words(text: str, num_words: int, from_end: bool = False) -> str:
    """Extract first or last N words from text."""
    words = text.split()
    if from_end:
        return ' '.join(words[-num_words:]) if len(words) >= num_words else text
    else:
        return ' '.join(words[:num_words]) if len(words) >= num_words else text


def run_all_tests():
    """Run all tests and summarize results."""
    print("\n" + "=" * 80)
    print("SOFT HYPHEN & MIXED HYPHENATION MATCHING TESTS")
    print("=" * 80)
    print()
    print("Testing complex case from Shea PDF page 136:")
    print("  - Regular hyphen + newline: con-\\n")
    print("  - Soft hyphens: plug-\\xadand-\\xadplay")
    print("  - Combined: special-\\xad\\npurpose")
    print()
    
    results = {}
    
    # Test 1: Basic normalization
    basic_normalization()
    
    # Test 2: Clipping with errors
    clipping_with_errors()
    
    # Test 3: Anchor-based matching
    results['anchor_based'] = anchor_based_matching()
    
    # Test 4: Fuzzy anchor matching
    results['fuzzy_anchor'] = fuzzy_anchor_matching()
    
    # Test 5: Position-based extraction
    results['position_based'] = position_based_extraction()
    
    # Test 6: Position-based with errors (simple)
    results['position_based_errors_simple'] = position_based_with_errors()
    
    # Test 7: Position-based with flexible length (smart)
    results['position_based_flexible'] = position_based_with_flexible_length()
    
    # Summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    for strategy, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {strategy}")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    if results.get('position_based') and results.get('position_based_flexible'):
        print("✓ FLEXIBLE POSITION-BASED EXTRACTION is MOST ROBUST")
        print("  - Works with clean clippings")
        print("  - Handles Kindle extraction errors")
        print("  - Avoids combinatorial explosion of hyphen variants")
        print("  - Strategy:")
        print("    1. Find beginning anchor (first N words) in PDF")
        print("    2. Find ending anchor (last N words) in search window")
        print("    3. Extract text between anchors")
        print("    4. Verify with similarity check (>90%)")
    else:
        print("⚠ Need to investigate further")


if __name__ == "__main__":
    run_all_tests()
