#!/usr/bin/env python3
"""
Diagnose import issues for this repo.
Run from the repository root:
  python scripts/diagnose_imports.py
"""

import sys
import traceback
from pathlib import Path

print("Python:", sys.version.splitlines()[0])
repo_root = Path(__file__).resolve().parent.parent
print("Repository root:", repo_root)
src_path = repo_root / "src"
print("src path:", src_path)
print()

# Ensure src is on sys.path the same way main.py does
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print("Effective sys.path (head):")
for p in sys.path[:6]:
    print("  ", p)
print()

print("Listing top-level src contents:")
for p in sorted(src_path.iterdir()):
    print("  ", p.name)
print()

def try_import(modname):
    print(f"Trying import: {modname}")
    try:
        m = __import__(modname, fromlist=['*'])
        print(f"  OK: {modname}")
        attrs = sorted([a for a in dir(m) if not a.startswith('_')])
        print("  Public attrs:", attrs[:12], "..." if len(attrs) > 12 else "")
        return m
    except Exception:
        print(f"  FAILED import {modname}:")
        traceback.print_exc()
        return None

# Try GUI import
try_import("gui.main_window")

# Try pdf annotator and compatibility symbol
m = try_import("pdf_processor.pdf_annotator")
if m is not None:
    for symbol in ("annotate_pdf_file", "PDFAnnotator", "_build_highlight_quads"):
        print(f"Has symbol {symbol}:", hasattr(m, symbol))
print()

print("If imports failed, please copy/paste the above full traceback here.")