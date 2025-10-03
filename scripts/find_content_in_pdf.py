#!/usr/bin/env python3
"""
Normalize a PDF page's text and search for a given content string.
Helps diagnose why matching fails under hyphenation or punctuation.

Usage:
  .\.venv\Scripts\python.exe scripts\find_content_in_pdf.py tests\snake_test.pdf 0 "A concept is ..."
"""
from __future__ import annotations

import sys
import re
from pathlib import Path
import fitz

def normalize_text(s: str) -> str:
    # Collapse whitespace and lowercase only
    return re.sub(r"\s+", " ", s).strip().lower()

def page_text_simple(page: fitz.Page) -> str:
    # Build a simple space-joined text from words, merging cross-line hyphens
    words = page.get_text("words")
    out = []
    i = 0
    while i < len(words):
        w = words[i][4]
        # merge hyphen if next word is on a different line
        if w.endswith('-') and i + 1 < len(words) and words[i][6] != words[i+1][6]:
            merged = w[:-1] + words[i+1][4]
            out.append(merged)
            i += 2
        else:
            out.append(w)
            i += 1
    return " ".join(out)

def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: find_content_in_pdf.py <pdf_path> <page_number> <content>")
        return 2

    pdf_path = Path(sys.argv[1])
    page_number = int(sys.argv[2])
    content = sys.argv[3]

    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return 2

    doc = fitz.open(str(pdf_path))
    if page_number < 0 or page_number >= len(doc):
        print(f"Invalid page number: {page_number}")
        return 2

    page = doc[page_number]
    page_txt = page_text_simple(page)
    doc.close()

    page_norm = normalize_text(page_txt)
    content_norm = normalize_text(content)

    idx = page_norm.find(content_norm)
    print(f"Page text (norm) length: {len(page_norm)}")
    print(f"Content (norm) length:   {len(content_norm)}")
    print(f"Match index: {idx}")
    if idx >= 0:
        start = max(0, idx - 40)
        end = min(len(page_norm), idx + len(content_norm) + 40)
        print("Context before:", page_norm[start:idx])
        print("Matched:", page_norm[idx:idx+len(content_norm)])
        print("Context after:", page_norm[idx+len(content_norm):end])
    else:
        print("No match found.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
