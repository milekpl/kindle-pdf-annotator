#!/usr/bin/env python3
"""Compute linear transform (least squares) from Kindle coordinates to PDF points.

Usage: python3 scripts/compute_linear_transform.py
"""
from pathlib import Path
import sys
import math

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations


def linear_fit(xs, ys):
    """Return slope, intercept, rmse, r2 for linear fit y = a*x + b"""
    n = len(xs)
    if n == 0:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0:
        a = 0.0
    else:
        a = ss_xy / ss_xx
    b = mean_y - a * mean_x
    # predictions
    preds = [a * x + b for x in xs]
    mse = sum((y - p) ** 2 for y, p in zip(ys, preds)) / n
    rmse = math.sqrt(mse)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, preds))
    r2 = 1.0 - ss_res / ss_tot if ss_tot != 0 else 0.0
    return a, b, rmse, r2


def analyze(dataset_name, krds_path, clippings_path=None):
    print(f"Analyzing dataset: {dataset_name}")
    anns = create_amazon_compliant_annotations(krds_path, clippings_path, dataset_name)
    xs = []
    px = []
    kw = []
    pw = []
    for ann in anns:
        if ann.get('type') != 'highlight':
            continue
        kx = ann.get('kindle_x')
        ky = ann.get('kindle_y')
        pw_x = ann.get('pdf_x')
        pw_y = ann.get('pdf_y')
        kwidth = ann.get('kindle_width')
        pwidth = ann.get('pdf_width')
        if kx is None or pw_x is None:
            continue
        try:
            kx_f = float(kx)
            pw_x_f = float(pw_x)
        except Exception:
            continue
        xs.append(kx_f)
        px.append(pw_x_f)
        try:
            kw_f = float(kwidth)
            pw_f = float(pwidth)
            kw.append(kw_f)
            pw.append(pw_f)
        except Exception:
            pass

    print(f"  Collected {len(xs)} (kindle_x -> pdf_x) pairs and {len(kw)} (kindle_width -> pdf_width) pairs")

    if xs:
        res = linear_fit(xs, px)
        if res:
            a, b, rmse, r2 = res
            print(f"  X mapping: pdf_x = {a:.6f} * kindle_x + {b:.3f}")
            print(f"    RMSE: {rmse:.3f} pts, R^2: {r2:.4f}")
    if kw:
        resw = linear_fit(kw, pw)
        if resw:
            aw, bw, rmse_w, r2_w = resw
            print(f"  Width mapping: pdf_width = {aw:.6f} * kindle_width + {bw:.3f}")
            print(f"    RMSE: {rmse_w:.3f} pts, R^2: {r2_w:.4f}")


if __name__ == '__main__':
    # Peirce dataset paths
    analyze(
        'peirce-charles-fixation-belief',
        'examples/sample_data/peirce-charles-fixation-belief.sdr/peirce-charles-fixation-belief12347ea8efc3f766707171e2bfcc00f4.pds',
        'examples/sample_data/peirce-charles-fixation-belief-clippings.txt'
    )
