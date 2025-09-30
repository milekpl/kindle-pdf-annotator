#!/usr/bin/env python3
"""
Dump words and blocks from a PDF page to help debug matching/highlighting.

Usage (PowerShell-friendly):
  .\.venv\Scripts\python.exe scripts\dump_pdf_tokens.py tests\snake_test.pdf 0

Args:
  pdf_path: Path to the PDF file
  page_number: 0-based page index (default: 0)
"""
from __future__ import annotations

import sys
from pathlib import Path
import fitz

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: dump_pdf_tokens.py <pdf_path> [page_number]")
        return 2

    pdf_path = Path(sys.argv[1])
    page_number = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return 2

    doc = fitz.open(str(pdf_path))
    if page_number < 0 or page_number >= len(doc):
        print(f"Invalid page number: {page_number}")
        return 2

    page = doc[page_number]
    words = page.get_text("words")
    print(f"WORDS COUNT {len(words)}")
    for i, w in enumerate(words):
        # word tuple: x0, y0, x1, y1, text, block_no, line_no, word_no
        print(f"{i:3d}: {w[4]} (block={w[5]}, line={w[6]}, word={w[7]})")

    print("\nBLOCKS:")
    for bi, b in enumerate(page.get_text("blocks")):
        r = fitz.Rect(b[:4])
        print(f"{bi}: {r}")

    doc.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
