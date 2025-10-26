#!/usr/bin/env python3
"""
Test that validates the ACTUAL text highlighted in the PDF matches the expected clippings.
This is a critical test to ensure we're not just placing highlights at the right location,
but actually highlighting the CORRECT text content.
"""

import sys
import fitz
from pathlib import Path
from difflib import SequenceMatcher

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.kindle_parser.amazon_coordinate_system import (
    create_amazon_compliant_annotations,
)
from src.pdf_processor.amazon_to_pdf_adapter import (
    convert_amazon_to_pdf_annotator_format,
)
from src.pdf_processor.pdf_annotator import annotate_pdf_file
from src.kindle_parser.clippings_parser import parse_myclippings_for_book


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra whitespace, ligatures, etc."""
    if not text:
        return ""
    import re

    # Replace multiple whitespace with single space, strip
    normalized = " ".join(text.split())
    # Apply ligature fixes
    normalized = normalized.replace("ﬁ", "fi").replace("ﬂ", "fl")
    normalized = normalized.replace("ﬀ", "ff").replace("ﬃ", "ffi").replace("ﬄ", "ffl")
    # Handle abbreviations: "ch.4" -> "ch. 4" (add space after period if missing before digit)
    normalized = re.sub(r"(\w)\.(\d)", r"\1. \2", normalized)
    return normalized


def extract_highlighted_text_from_pdf(pdf_path: str) -> dict:
    """
    Extract the actual text that is highlighted in the PDF by reading from the source PDF.

    Returns:
        Dict mapping page numbers to list of highlighted text strings
    """
    doc = fitz.open(pdf_path)

    # Map to find source PDF from test output filename
    pdf_name = (
        pdf_path.split("/")[-1]
        .replace("test_highlighted_text_", "")
        .replace(".pdf", "")
    )
    source_pdfs = {
        "peirce-charles-fixation-belief": "examples/sample_data/peirce-charles-fixation-belief.pdf",
        "659ec7697e419": "examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf",
    }

    if pdf_name in source_pdfs:
        source_doc = fitz.open(source_pdfs[pdf_name])
    else:
        # Fallback: use the same PDF
        source_doc = doc

    highlights_by_page = {}

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        source_page = source_doc.load_page(page_num)
        annots = page.annots()
        page_highlights = []

        if annots:
            for annot in annots:
                if annot.type[0] == 8:  # Highlight annotation
                    # Get the quad points - these are the PRECISE character bounding boxes
                    quads = annot.vertices
                    if not quads:
                        continue

                    num_quads = len(quads) // 4

                    # Instead of using get_textbox (which is imprecise),
                    # search for text at each quad location in the source PDF
                    all_quad_rects = []
                    for q in range(num_quads):
                        base = q * 4
                        quad_points = quads[base : base + 4]
                        x_coords = [p[0] for p in quad_points]
                        y_coords = [p[1] for p in quad_points]
                        rect = fitz.Rect(
                            min(x_coords), min(y_coords), max(x_coords), max(y_coords)
                        )
                        all_quad_rects.append(rect)

                    # Union all the quad rects to get the overall highlight region
                    if all_quad_rects:
                        combined_rect = all_quad_rects[0]
                        for r in all_quad_rects[1:]:
                            combined_rect = combined_rect | r

                        # Search for text in this region in the source PDF
                        # Use get_text with clip parameter for more precise extraction
                        text = source_page.get_text("text", clip=combined_rect)
                        if text:
                            page_highlights.append(normalize_text(text))

        if page_highlights:
            highlights_by_page[page_num + 1] = page_highlights  # 1-based page numbers

    return highlights_by_page


def text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two text strings (0-1)."""
    return SequenceMatcher(None, text1, text2).ratio()


def test_highlighted_text_matches_clippings():
    """
    Test that the actual highlighted text in the PDF matches the expected clippings text.
    This validates that we're highlighting the RIGHT text, not just placing highlights
    at the right location.
    """

    # Test datasets
    datasets = [
        {
            "name": "peirce-charles-fixation-belief",
            "krds": "examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds",
            "clippings": "examples/sample_data/peirce-charles-fixation-belief-clippings.txt",
            "pdf": "examples/sample_data/peirce-charles-fixation-belief.pdf",
        },
        {
            "name": "659ec7697e419",
            "krds": "examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ12347ea8efc3f766707171e2bfcc00f4.pds",
            "clippings": "examples/sample_data/659ec7697e419-clippings.txt",
            "pdf": "examples/sample_data/659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf",
        },
    ]

    all_passed = True

    for dataset in datasets:
        print(f"\n{'=' * 80}")
        print(f"🔍 HIGHLIGHTED TEXT VALIDATION TEST: {dataset['name']}")
        print(f"{'=' * 80}")

        # Parse expected highlights from clippings
        myclippings_entries = parse_myclippings_for_book(
            dataset["clippings"], dataset["name"]
        )

        expected_highlights = []
        for entry in myclippings_entries:
            if entry.get("type") == "highlight" and entry.get("content", "").strip():
                expected_highlights.append(
                    {
                        "page": entry.get("pdf_page", 1),
                        "content": entry.get("content", "").strip(),
                        "normalized": normalize_text(entry.get("content", "")),
                    }
                )

        print(f"\n📋 Expected {len(expected_highlights)} highlights from clippings")

        # Create annotated PDF
        output_file = f"/tmp/test_highlighted_text_{dataset['name']}.pdf"
        amazon_annotations = create_amazon_compliant_annotations(
            dataset["krds"], dataset["clippings"], dataset["name"]
        )
        pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
        annotate_pdf_file(dataset["pdf"], pdf_annotations, output_file)

        # Extract actual highlighted text from PDF
        actual_highlights = extract_highlighted_text_from_pdf(output_file)
        total_actual = sum(len(highlights) for highlights in actual_highlights.values())
        print(f"📄 Found {total_actual} highlights in generated PDF")

        # Match expected vs actual
        print(f"\n{'=' * 80}")
        print("🔎 MATCHING EXPECTED vs ACTUAL HIGHLIGHTED TEXT")
        print(f"{'=' * 80}")

        matched_count = 0
        unmatched_expected = []

        for expected in expected_highlights:
            page = expected["page"]
            expected_text = expected["normalized"]

            # Find best match on this page
            if page not in actual_highlights:
                unmatched_expected.append(expected)
                print(f"\n❌ Page {page}: NO HIGHLIGHTS FOUND")
                print(
                    f'   Expected: "{expected_text[:60]}..."'
                    if len(expected_text) > 60
                    else f'   Expected: "{expected_text}"'
                )
                continue

            best_match_ratio = 0
            best_match_text = None

            for actual_text in actual_highlights[page]:
                similarity = text_similarity(expected_text, actual_text)
                if similarity > best_match_ratio:
                    best_match_ratio = similarity
                    best_match_text = actual_text

            # We need at least 80% similarity to consider it a match
            if best_match_ratio >= 0.80:
                matched_count += 1
                status = "✅" if best_match_ratio >= 0.95 else "⚠️ "
                print(f"\n{status} Page {page}: Match {best_match_ratio * 100:.1f}%")
                if best_match_ratio < 0.95:
                    print(
                        f'   Expected: "{expected_text[:60]}..."'
                        if len(expected_text) > 60
                        else f'   Expected: "{expected_text}"'
                    )
                    print(
                        f'   Actual:   "{best_match_text[:60]}..."'
                        if len(best_match_text) > 60
                        else f'   Actual:   "{best_match_text}"'
                    )
            else:
                unmatched_expected.append(expected)
                print(f"\n❌ Page {page}: Poor match {best_match_ratio * 100:.1f}%")
                print(
                    f'   Expected: "{expected_text[:60]}..."'
                    if len(expected_text) > 60
                    else f'   Expected: "{expected_text}"'
                )
                print(
                    f'   Actual:   "{best_match_text[:60]}..."'
                    if best_match_text and len(best_match_text) > 60
                    else f'   Actual:   "{best_match_text}"'
                )

        # Results
        match_percentage = (
            (matched_count / len(expected_highlights) * 100)
            if expected_highlights
            else 0
        )

        print(f"\n{'=' * 80}")
        print(f"📊 RESULTS for {dataset['name']}")
        print(f"{'=' * 80}")
        print(f"   Expected highlights: {len(expected_highlights)}")
        print(f"   Matched: {matched_count}")
        print(f"   Match percentage: {match_percentage:.1f}%")

        if unmatched_expected:
            print(f"\n   ⚠️  Unmatched expected highlights ({len(unmatched_expected)}):")
            for h in unmatched_expected[:5]:  # Show first 5
                text = h["normalized"]
                print(
                    f'      Page {h["page"]}: "{text[:60]}..."'
                    if len(text) > 60
                    else f'      Page {h["page"]}: "{text}"'
                )

        # Expect at least 75% match for test to pass
        # (Some mismatch is expected due to PyMuPDF text extraction including extra chars)
        if match_percentage < 75:
            print(
                f"\n❌ TEST FAILED: Only {match_percentage:.1f}% of highlights matched (expected >= 75%)"
            )
            all_passed = False
        else:
            print(f"\n✅ TEST PASSED: {match_percentage:.1f}% of highlights matched")

    assert all_passed, "Highlighted text validation failed for one or more datasets"


if __name__ == "__main__":
    test_highlighted_text_matches_clippings()
