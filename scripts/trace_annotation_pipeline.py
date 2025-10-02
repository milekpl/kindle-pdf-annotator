#!/usr/bin/env python3
"""Trace annotations through amazon conversion, adapter, and pdf_annotator.

Run this to get per-annotation diagnostics for the Peirce sample dataset.
"""
import json
from pathlib import Path
import sys

# Add project src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from pdf_processor.pdf_annotator import PDFAnnotator, annotate_pdf_file


def trace_peirce():
    book_name = 'peirce-charles-fixation-belief'
    krds = 'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds'
    clippings = 'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    pdf = 'examples/sample_data/peirce-charles-fixation-belief.pdf'
    out_pdf = f'tests/{book_name}_trace_annotated.pdf'
    trace_json = f'tests/{book_name}_trace.json'

    print(f"Tracing dataset: {book_name}")

    amazon_annotations = create_amazon_compliant_annotations(krds, clippings, book_name)
    print(f"Amazon annotations: {len(amazon_annotations)} entries")

    converted = convert_amazon_to_pdf_annotator_format(amazon_annotations)
    print(f"Adapter returned: {len(converted)} annotations")

    # Open PDFAnnotator to use its quad-building internals
    annotator = PDFAnnotator(pdf)
    if not annotator.open_pdf():
        print(f"Failed to open PDF: {pdf}")
        return

    diagnostics = []

    for idx, ann in enumerate(converted):
        diag = {'index': idx, 'type': ann.get('type'), 'page_number': ann.get('page_number')}
        diag['content_preview'] = (ann.get('content') or '')[:120]
        diag['kindle_coordinates'] = ann.get('kindle_coordinates')
        diag['pdf_fields'] = {
            'pdf_x': ann.get('pdf_x'),
            'pdf_y': ann.get('pdf_y'),
            'pdf_width': ann.get('pdf_width'),
            'pdf_height': ann.get('pdf_height')
        }
        diag['segment_rects_count'] = len(ann.get('segment_rects') or [])

        # If highlight, attempt to build quads using annotator internals
        try:
            page_num = ann.get('page_number')
            if page_num is None:
                page_num = ann.get('pdf_page_0based')
            page = annotator.doc.load_page(page_num) if page_num is not None else None
        except Exception:
            page = None

        if ann.get('type') == 'highlight' and page is not None:
            try:
                quads = annotator._build_highlight_quads(page, ann)
                if quads is None:
                    diag['quads'] = None
                else:
                    diag['quads'] = []
                    for q in quads:
                        try:
                            diag['quads'].append({'rect': [q.x0, q.y0, q.x1, q.y1], 'w': q.width, 'h': q.height})
                        except Exception:
                            diag['quads'].append(str(q))
            except Exception as e:
                diag['quad_error'] = str(e)
        else:
            diag['quads'] = None

        diagnostics.append(diag)

    # Save diagnostics
    with open(trace_json, 'w', encoding='utf-8') as fh:
        json.dump(diagnostics, fh, indent=2)

    print(f"Wrote trace JSON to {trace_json}")

    # Also create annotated PDF for inspection (uses existing annotate_pdf_file)
    success = annotate_pdf_file(pdf, converted, out_pdf)
    print(f"Annotated PDF saved as {out_pdf}: {success}")

    annotator.close_pdf()


if __name__ == '__main__':
    trace_peirce()
