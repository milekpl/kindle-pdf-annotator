#!/usr/bin/env python3
"""Utility for calibrating Kindle (KRDS) coordinates against PDF text positions.

This script collects paired coordinate samples from the bundled open-access
examples, matches each Kindle highlight to the corresponding text in the PDF,
records the observed rectangles, and then performs simple linear regression to
suggest updated conversion parameters.

Run from the repository root:

    PYTHONPATH=src python scripts/calibrate_kindle_pdf_coordinates.py

The script outputs:
    • A JSON file with every collected sample (for manual inspection).
    • Suggested linear coefficients for X / Y positions and width / height.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import fitz  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SAMPLE_DATA = ROOT / "examples" / "sample_data"
OUTPUT_DIR = ROOT / "scripts"
OUTPUT_JSON = OUTPUT_DIR / "calibration_samples.json"

from src.kindle_parser.fixed_clippings_parser import parse_myclippings_for_book
from src.kindle_parser.krds_parser import parse_krds_file


@dataclass
class DatasetConfig:
    """Description of a calibration dataset."""

    name: str
    book_name: str
    pdf: Path
    krds: Path
    clippings: Path


DATASETS: List[DatasetConfig] = [
    DatasetConfig(
        name="peirce-charles-fixation-belief",
        book_name="peirce-charles-fixation-belief",
        pdf=SAMPLE_DATA / "peirce-charles-fixation-belief.pdf",
        krds=SAMPLE_DATA
        / "peirce-charles-fixation-belief.sdr"
        / "peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds",
        clippings=SAMPLE_DATA / "peirce-charles-fixation-belief-clippings.txt",
    ),
    DatasetConfig(
        name="scaling-up-theatre-hunger",
        book_name="Downey - 2024 - Theatre Hunger An Underestimated ‘Scaling Up’ Pro",
        pdf=SAMPLE_DATA
        / "Downey - 2024 - Theatre Hunger An Underestimated ‘Scaling Up’ Pro.pdf-cdeKey_WAY5I3SIILOP6F4ROJNHQ5YIIEUBUDRT.pdf",
        krds=SAMPLE_DATA
        / "Downey - 2024 - Theatre Hunger An Underestimated ‘Scaling Up’ Pro.pdf-cdeKey_WAY5I3SIILOP6F4ROJNHQ5YIIEUBUDRT.sdr"
        / "Downey - 2024 - Theatre Hunger An Underestimated ‘Scaling Up’ Pro.pdf-cdeKey_WAY5I3SIILOP6F4ROJNHQ5YIIEUBUDRT12347ea8efc3f766707171e2bfcc00f4.pds",
        clippings=SAMPLE_DATA
        / "Downey - 2024 - Theatre Hunger An Underestimated ‘Scaling Up’ Pro-clippings.txt",
    ),
    DatasetConfig(
        name="659ec7697e419",
        book_name="659ec7697e419",
        pdf=SAMPLE_DATA
        / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf",
        krds=SAMPLE_DATA
        / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr"
        / "659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ12347ea8efc3f766707171e2bfcc00f4.pds",
        clippings=SAMPLE_DATA / "659ec7697e419-clippings.txt",
    ),
]

# Normalisation helpers ------------------------------------------------------

TOKEN_PATTERN = re.compile(r"[\w']+", re.UNICODE)


def _normalize_apostrophes(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2014", "-")
    )


def normalize_text(text: str) -> str:
    """Collapse whitespace and harmonise apostrophes."""
    text = _normalize_apostrophes(text or "")
    return " ".join(text.split())


def tokenize(text: str) -> List[str]:
    normalized = normalize_text(text).lower()
    return TOKEN_PATTERN.findall(normalized)


@dataclass
class HighlightSample:
    dataset: str
    content: str
    pdf_page: int
    kindle_page: int
    kindle_x: float
    kindle_y: float
    kindle_width: float
    kindle_height: float
    pdf_x: float
    pdf_y: float
    pdf_width: float
    pdf_height: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "dataset": self.dataset,
            "content": self.content,
            "pdf_page": self.pdf_page,
            "kindle_page": self.kindle_page,
            "kindle_x": self.kindle_x,
            "kindle_y": self.kindle_y,
            "kindle_width": self.kindle_width,
            "kindle_height": self.kindle_height,
            "pdf_x": self.pdf_x,
            "pdf_y": self.pdf_y,
            "pdf_width": self.pdf_width,
            "pdf_height": self.pdf_height,
        }


# PDF text search ------------------------------------------------------------


def _load_page_tokens(page: Any) -> List[Tuple[str, Any]]:
    """Return a list of (normalized_token, rect) for the given page."""
    tokens: List[Tuple[str, Any]] = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        rect = fitz.Rect(x0, y0, x1, y1)
        word_tokens = tokenize(word)
        for token in word_tokens:
            tokens.append((token, rect))
    return tokens


def _union_rects(rects: Sequence[Any]) -> Any:
    x0 = min(r.x0 for r in rects)
    y0 = min(r.y0 for r in rects)
    x1 = max(r.x1 for r in rects)
    y1 = max(r.y1 for r in rects)
    return fitz.Rect(x0, y0, x1, y1)


def _find_candidate_rects(
    page_tokens: Sequence[Tuple[str, Any]],
    target_tokens: Sequence[str],
) -> List[Any]:
    if not target_tokens:
        return []

    matches: List[fitz.Rect] = []
    tlen = len(target_tokens)
    max_index = len(page_tokens) - tlen + 1
    for start in range(max_index):
        for offset in range(tlen):
            if page_tokens[start + offset][0] != target_tokens[offset]:
                break
        else:
            rects = [page_tokens[start + i][1] for i in range(tlen)]
            matches.append(_union_rects(rects))
    return matches


def _select_best_rect(
    rects: Sequence[Any],
    approximate_y: float,
    min_y: Optional[float],
) -> Optional[Any]:
    if not rects:
        return None

    ordered = sorted(rects, key=lambda r: r.y0)
    if min_y is not None:
        viable = [r for r in ordered if r.y0 + 1 >= min_y]
        if viable:
            ordered = viable
    return min(ordered, key=lambda r: abs(r.y0 - approximate_y))


# Regression helpers ---------------------------------------------------------


def _linear_regression(xs: Sequence[float], ys: Sequence[float]) -> Tuple[float, float, float]:
    n = len(xs)
    if n == 0:
        raise ValueError("Cannot regress with zero samples")

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        return 0.0, mean_y, 0.0

    slope = cov / var_x
    intercept = mean_y - slope * mean_x

    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot else 1.0
    return slope, intercept, r2


def _scale_through_origin(xs: Sequence[float], ys: Sequence[float]) -> float:
    numerator = sum(x * y for x, y in zip(xs, ys))
    denominator = sum(x * x for x in xs)
    if denominator == 0:
        return 0.0
    return numerator / denominator


# Main calibration logic -----------------------------------------------------


def gather_samples(dataset: DatasetConfig) -> List[HighlightSample]:
    if not dataset.pdf.exists():
        raise FileNotFoundError(dataset.pdf)
    if not dataset.krds.exists():
        raise FileNotFoundError(dataset.krds)
    if not dataset.clippings.exists():
        raise FileNotFoundError(dataset.clippings)

    print(f"\n📚 Dataset: {dataset.name}")
    pdf_doc = fitz.open(dataset.pdf)

    krds_annotations = [
        annot
        for annot in parse_krds_file(str(dataset.krds))
        if annot.category == "highlight" and annot.start_position.valid
    ]
    print(f"   • KRDS highlights: {len(krds_annotations)}")

    clippings_entries = [
        entry
        for entry in parse_myclippings_for_book(str(dataset.clippings), dataset.book_name)
        if entry.get("type") == "highlight" and entry.get("content", "").strip()
    ]
    print(f"   • Clipping highlights: {len(clippings_entries)}")

    if len(clippings_entries) != len(krds_annotations):
        print(
            f"   ⚠️  Count mismatch (clippings={len(clippings_entries)}, KRDS={len(krds_annotations)})."
            " Proceeding with min count."
        )

    # Sort by page then Kindle Y to maintain order.
    krds_annotations.sort(key=lambda ann: (ann.start_position.page, ann.start_position.y))
    clippings_entries.sort(key=lambda entry: (entry.get("pdf_page", 0), entry.get("content", "")))

    samples: List[HighlightSample] = []
    page_tokens_cache: Dict[int, List[Tuple[str, fitz.Rect]]] = {}
    last_y_by_page: Dict[int, float] = {}

    pair_count = min(len(krds_annotations), len(clippings_entries))
    for index in range(pair_count):
        annot = krds_annotations[index]
        entry = clippings_entries[index]

        kindle_page = annot.start_position.page
        pdf_page = entry.get("pdf_page", kindle_page + 1) - 1  # convert to 0-based
        if not (0 <= pdf_page < len(pdf_doc)):
            print(f"   ⚠️  Skipping highlight with out-of-range page {pdf_page + 1}")
            continue

        page = cast(Any, pdf_doc[pdf_page])
        if pdf_page not in page_tokens_cache:
            page_tokens_cache[pdf_page] = _load_page_tokens(page)
        page_tokens = page_tokens_cache[pdf_page]

        target_text = entry.get("content", "").strip()
        target_tokens = tokenize(target_text)
        candidate_rects = _find_candidate_rects(page_tokens, target_tokens)

        approx_scale = float(page.rect.height) / 1024.0
        approx_y = annot.start_position.y * approx_scale
        previous_y = last_y_by_page.get(pdf_page)
        selected_rect = _select_best_rect(candidate_rects, approx_y, previous_y)

        if selected_rect is None:
            print(f"   ⚠️  Could not locate text for highlight: '{target_text[:60]}…'")
            continue

        last_y_by_page[pdf_page] = selected_rect.y0
        samples.append(
            HighlightSample(
                dataset=dataset.name,
                content=normalize_text(target_text),
                pdf_page=pdf_page,
                kindle_page=kindle_page,
                kindle_x=float(annot.start_position.x),
                kindle_y=float(annot.start_position.y),
                kindle_width=float(annot.start_position.width),
                kindle_height=float(annot.start_position.height),
                pdf_x=float(selected_rect.x0),
                pdf_y=float(selected_rect.y0),
                pdf_width=float(selected_rect.width),
                pdf_height=float(selected_rect.height),
            )
        )

    pdf_doc.close()
    print(f"   • Recorded samples: {len(samples)}")
    return samples


def summarise_regression(samples: Sequence[HighlightSample]) -> None:
    if not samples:
        print("No samples gathered; cannot perform regression.")
        return

    kindle_xs = [s.kindle_x for s in samples]
    kindle_ys = [s.kindle_y for s in samples]
    kindle_widths = [s.kindle_width for s in samples]
    kindle_heights = [s.kindle_height for s in samples]

    pdf_xs = [s.pdf_x for s in samples]
    pdf_ys = [s.pdf_y for s in samples]
    pdf_widths = [s.pdf_width for s in samples]
    pdf_heights = [s.pdf_height for s in samples]

    slope_x, offset_x, r2_x = _linear_regression(kindle_xs, pdf_xs)
    slope_y, offset_y, r2_y = _linear_regression(kindle_ys, pdf_ys)
    slope_width, offset_width, r2_width = _linear_regression(kindle_widths, pdf_widths)
    slope_height, offset_height, r2_height = _linear_regression(kindle_heights, pdf_heights)
    scale_width = _scale_through_origin(kindle_widths, pdf_widths)
    scale_height = _scale_through_origin(kindle_heights, pdf_heights)

    print("\n📈 Suggested regression coefficients")
    print(f"   X: pdf_x = {slope_x:.6f} * kindle_x + {offset_x:.3f}  (R^2={r2_x:.4f})")
    print(f"   Y: pdf_y = {slope_y:.6f} * kindle_y + {offset_y:.3f}  (R^2={r2_y:.4f})")
    print(
        "   Width: pdf_width ≈ {:.6f} * kindle_width + {:.3f}  (R^2={:.4f}, through-origin {:.6f})".format(
            slope_width, offset_width, r2_width, scale_width
        )
    )
    print(
        "   Height: pdf_height ≈ {:.6f} * kindle_height + {:.3f}  (R^2={:.4f}, through-origin {:.6f})".format(
            slope_height, offset_height, r2_height, scale_height
        )
    )

    print("\n💾 Saving raw samples to", OUTPUT_JSON)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = [sample.to_dict() for sample in samples]
    OUTPUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    all_samples: List[HighlightSample] = []
    for dataset in DATASETS:
        samples = gather_samples(dataset)
        all_samples.extend(samples)

    print(f"\n✅ Total samples gathered: {len(all_samples)}")
    summarise_regression(all_samples)


if __name__ == "__main__":
    main()
