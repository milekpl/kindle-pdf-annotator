#!/usr/bin/env python3
"""
Quick inspection script to manually examine annotations in a PDF
and identify any that have multiple disconnected yellow highlight regions.
"""

import fitz  # PyMuPDF
import sys
from pathlib import Path

def inspect_pdf_annotations(pdf_path):
    """Open a PDF and analyze each annotation's quad structure."""
    
    print(f"\n{'='*80}")
    print(f"Inspecting: {Path(pdf_path).name}")
    print(f"{'='*80}\n")
    
    doc = fitz.open(pdf_path)
    
    total_annotations = 0
    problematic_annotations = 0
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        annotations = page.annots()
        
        if not annotations:
            continue
            
        page_annotations = list(annotations)
        if not page_annotations:
            continue
            
        print(f"📄 Page {page_num + 1}: {len(page_annotations)} annotations")
        
        for annot_idx, annot in enumerate(page_annotations):
            total_annotations += 1
            
            # Only look at highlight annotations
            if annot.type[0] != 8:  # 8 = highlight
                continue
            
            # Get the vertices (quads)
            vertices = annot.vertices
            
            if not vertices:
                continue
            
            # Parse quads
            quads = []
            for i in range(0, len(vertices), 4):
                quad_points = vertices[i:i+4]
                if len(quad_points) == 4:
                    quads.append(quad_points)
            
            if len(quads) == 0:
                continue
            
            # Cluster the quads to find disconnected regions
            clusters = cluster_quads(quads)
            
            if len(clusters) > 1:
                # Check if clusters are truly disconnected (>100 points apart)
                if are_clusters_disconnected(clusters):
                    problematic_annotations += 1
                    print(f"\n  ⚠️  ANNOTATION #{annot_idx + 1} (#{total_annotations} overall)")
                    print(f"      Total quads: {len(quads)}")
                    print(f"      Disconnected regions: {len(clusters)}")
                    
                    for cluster_idx, cluster in enumerate(clusters):
                        xs = []
                        ys = []
                        for quad in cluster:
                            for point in quad:
                                if hasattr(point, 'x'):
                                    xs.append(point.x)
                                    ys.append(point.y)
                                elif isinstance(point, (tuple, list)) and len(point) >= 2:
                                    xs.append(point[0])
                                    ys.append(point[1])
                        
                        if xs and ys:
                            min_x, max_x = min(xs), max(xs)
                            min_y, max_y = min(ys), max(ys)
                            center_x = (min_x + max_x) / 2
                            center_y = (min_y + max_y) / 2
                            
                            print(f"      Region {cluster_idx + 1}: {len(cluster)} quads")
                            print(f"        BBox: ({min_x:.1f}, {min_y:.1f}) -> ({max_x:.1f}, {max_y:.1f})")
                            print(f"        Center: ({center_x:.1f}, {center_y:.1f})")
    
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY:")
    print(f"   Total annotations: {total_annotations}")
    print(f"   Problematic annotations: {problematic_annotations}")
    if problematic_annotations > 0:
        print(f"   ⚠️  Found {problematic_annotations} annotation(s) with multiple disconnected regions!")
    else:
        print(f"   ✅ No issues detected - all annotations have single continuous regions")
    print(f"{'='*80}\n")
    
    doc.close()


def cluster_quads(quads):
    """Group quads into connected regions."""
    if not quads:
        return []
    
    clusters = [[quads[0]]]
    
    for quad in quads[1:]:
        added = False
        for cluster in clusters:
            if any(are_quads_connected(quad, q) for q in cluster):
                cluster.append(quad)
                added = True
                break
        
        if not added:
            clusters.append([quad])
    
    return clusters


def are_quads_connected(quad1, quad2, h_threshold=50, v_threshold=25):
    """Check if two quads are close enough to be part of same text flow."""
    
    # Extract coordinates
    def get_coords(quad):
        xs, ys = [], []
        for point in quad:
            if hasattr(point, 'x'):
                xs.append(point.x)
                ys.append(point.y)
            elif isinstance(point, (tuple, list)) and len(point) >= 2:
                xs.append(point[0])
                ys.append(point[1])
        return xs, ys
    
    xs1, ys1 = get_coords(quad1)
    xs2, ys2 = get_coords(quad2)
    
    if not xs1 or not xs2:
        return False
    
    min_x1, max_x1 = min(xs1), max(xs1)
    min_y1, max_y1 = min(ys1), max(ys1)
    min_x2, max_x2 = min(xs2), max(xs2)
    min_y2, max_y2 = min(ys2), max(ys2)
    
    # Check vertical overlap (same line)
    y_overlap = not (max_y1 < min_y2 or max_y2 < min_y1)
    
    # Check horizontal distance
    h_distance = min(abs(max_x1 - min_x2), abs(max_x2 - min_x1))
    
    # Same line: vertically overlapping and horizontally close
    if y_overlap and h_distance < h_threshold:
        return True
    
    # Adjacent lines: vertically close and horizontally overlapping
    v_distance = min(abs(max_y1 - min_y2), abs(max_y2 - min_y1))
    x_overlap = not (max_x1 < min_x2 or max_x2 < min_x1)
    
    if v_distance < v_threshold and x_overlap:
        return True
    
    return False


def are_clusters_disconnected(clusters, min_distance=100):
    """Check if clusters are far apart (truly disconnected)."""
    
    if len(clusters) <= 1:
        return False
    
    # Calculate center points of each cluster
    centers = []
    for cluster in clusters:
        all_xs, all_ys = [], []
        for quad in cluster:
            for point in quad:
                if hasattr(point, 'x'):
                    all_xs.append(point.x)
                    all_ys.append(point.y)
                elif isinstance(point, (tuple, list)) and len(point) >= 2:
                    all_xs.append(point[0])
                    all_ys.append(point[1])
        
        if all_xs and all_ys:
            centers.append((sum(all_xs)/len(all_xs), sum(all_ys)/len(all_ys)))
    
    # Check distance between all pairs of cluster centers
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            x1, y1 = centers[i]
            x2, y2 = centers[j]
            distance = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
            
            if distance > min_distance:
                return True
    
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_annotation_quads.py <pdf_file>")
        print("\nInspect a few example PDFs:")
        output_dir = Path(__file__).parent.parent / "learning_output" / "debug_highlights"
        if output_dir.exists():
            pdfs = list(output_dir.glob("*.pdf"))[:5]
            for pdf in pdfs:
                print(f"  python scripts/inspect_annotation_quads.py '{pdf}'")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    inspect_pdf_annotations(pdf_path)
