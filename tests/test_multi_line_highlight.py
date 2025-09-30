import fitz
import pytest
from pathlib import Path

from src.pdf_processor.pdf_annotator import annotate_pdf_file


def _create_sample_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)
    text = "First line highlight text\nSecond line highlight text"
    textbox_rect = fitz.Rect(50, 80, 350, 200)
    page.insert_textbox(textbox_rect, text, fontsize=12, lineheight=1.2)
    doc.save(pdf_path)
    doc.close()


def _build_annotation() -> dict:
    return {
        "type": "highlight",
        "page_number": 0,
        "content": "First line highlight text Second line highlight text",
        "coordinates": [60, 90, 320, 160],
        "segment_rects": [
            [60, 95, 320, 110],
            [60, 125, 320, 140],
        ],
        "kindle_coordinates": {
            "pdf_x": 60,
            "pdf_y": 95,
        },
    }


@pytest.mark.parametrize("line_count", [2])
def test_multi_line_highlight_creates_multiple_quads(tmp_path, line_count):
    pdf_path = tmp_path / "multi_line.pdf"
    output_path = tmp_path / "annotated.pdf"

    _create_sample_pdf(pdf_path)
    annotations = [_build_annotation()]

    success = annotate_pdf_file(str(pdf_path), annotations, str(output_path))
    assert success, "Annotation pipeline should succeed"

    doc = fitz.open(str(output_path))
    page = doc[0]
    highlight_annots = [annot for annot in page.annots() if annot.type[1] == "Highlight"]

    assert highlight_annots, "Expected at least one highlight annotation"
    highlight = highlight_annots[0]

    quad_count = len(highlight.vertices) // 4
    assert quad_count >= line_count, f"Expected >= {line_count} quads, got {quad_count}"

    doc.close()
