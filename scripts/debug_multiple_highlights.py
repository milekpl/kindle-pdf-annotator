#!/usr/bin/env python3
"""
Debug script to systematically detect multiple disconnected yellow markers
within single annotations across all PDF files.

This script:
1. Processes all PDFs in learn/documents
2. Creates annotated PDFs in learning_output/debug_highlights/
3. Analyzes each annotation to detect if it contains multiple disconnected
   yellow highlight regions (which indicates a bug)
4. Generates a detailed bug report with:
   - Files with issues
   - Number of problematic annotations per file
   - Visual analysis of highlight quad patterns
   - Coordinates and text content for debugging

The key insight: A SINGLE annotation entry from KRDS should create ONE
contiguous highlighted region, not multiple scattered yellow boxes.
"""

import os
import sys
import json
import fitz  # PyMuPDF
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add src to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from pdf_processor.pdf_annotator import annotate_pdf_file


class HighlightAnalyzer:
    """Analyzes highlight annotations for multiple disconnected regions."""
    
    def __init__(self):
        self.issues = []
        self.statistics = {
            'total_files': 0,
            'files_with_highlights': 0,
            'files_with_issues': 0,
            'total_annotations': 0,
            'problematic_annotations': 0
        }
    
    def analyze_annotation_quads(self, page, annot):
        """
        Analyze a single annotation to detect multiple disconnected regions.
        
        Returns dict with:
        - has_issue: bool
        - num_quads: int
        - num_clusters: int (disconnected regions)
        - cluster_info: list of cluster details
        """
        if annot.type[0] != 8:  # Not a highlight
            return None
        
        # Get all quads for this annotation
        try:
            vertices = annot.vertices
            if not vertices or len(vertices) < 4:
                return None
            
            # Convert vertices (flat list or list of points) to quad rectangles
            quad_rects = []
            
            # Check if vertices is a list of Point objects or tuples
            if len(vertices) >= 4:
                # Handle both Point objects and tuples (x, y)
                for i in range(0, len(vertices), 4):
                    if i + 3 < len(vertices):
                        points = vertices[i:i+4]
                        # Convert to coordinates
                        xs = []
                        ys = []
                        for p in points:
                            if hasattr(p, 'x'):  # Point object
                                xs.append(p.x)
                                ys.append(p.y)
                            elif isinstance(p, (tuple, list)) and len(p) >= 2:  # Tuple/list
                                xs.append(p[0])
                                ys.append(p[1])
                            else:
                                # Skip malformed point
                                continue
                        
                        if len(xs) == 4 and len(ys) == 4:
                            rect = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
                            quad_rects.append(rect)
        except Exception:
            return None
        
        if not quad_rects:
            return None
        
        # Cluster quads into disconnected regions
        clusters = self._cluster_quads(quad_rects)
        
        # Consider it an issue if there are multiple disconnected clusters
        # with significant distance between them
        has_issue = False
        if len(clusters) > 1:
            # Check if clusters are truly disconnected (not just multi-line)
            has_issue = self._are_clusters_disconnected(clusters)
        
        result = {
            'has_issue': has_issue,
            'num_quads': len(quad_rects),
            'num_clusters': len(clusters),
            'cluster_info': []
        }
        
        # Add cluster details
        for i, cluster in enumerate(clusters):
            bbox = self._get_cluster_bbox(cluster)
            # Extract text from this region
            try:
                text = page.get_text("text", clip=bbox).strip()
            except:
                text = "[unable to extract]"
            
            result['cluster_info'].append({
                'cluster_id': i,
                'num_quads': len(cluster),
                'bbox': (bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                'text': text[:100]  # First 100 chars
            })
        
        return result
    
    def _cluster_quads(self, quads):
        """Cluster quads into disconnected regions based on proximity."""
        if not quads:
            return []
        
        clusters = [[quads[0]]]
        
        for quad in quads[1:]:
            # Try to add to existing cluster
            added = False
            for cluster in clusters:
                # Check if quad is close to any quad in this cluster
                for existing_quad in cluster:
                    if self._are_quads_connected(quad, existing_quad):
                        cluster.append(quad)
                        added = True
                        break
                if added:
                    break
            
            # Start new cluster if not added
            if not added:
                clusters.append([quad])
        
        return clusters
    
    def _are_quads_connected(self, q1, q2, max_gap=50):
        """Check if two quads are connected (part of same text flow)."""
        # Check horizontal overlap (same line)
        if not (q1.y1 < q2.y0 or q1.y0 > q2.y1):  # Y overlap
            # On same line, check horizontal distance
            if abs(q1.x1 - q2.x0) < max_gap or abs(q2.x1 - q1.x0) < max_gap:
                return True
        
        # Check vertical proximity (adjacent lines)
        y_gap = min(abs(q1.y0 - q2.y1), abs(q2.y0 - q1.y1))
        if y_gap < 25:  # Adjacent lines
            # Check horizontal overlap
            if not (q1.x1 < q2.x0 or q1.x0 > q2.x1):
                return True
        
        return False
    
    def _are_clusters_disconnected(self, clusters):
        """Check if clusters are truly disconnected (not just multi-line)."""
        if len(clusters) <= 1:
            return False
        
        # Get bounding box for each cluster
        bboxes = [self._get_cluster_bbox(c) for c in clusters]
        
        # Check distances between cluster centers
        min_distance = float('inf')
        for i in range(len(bboxes)):
            for j in range(i+1, len(bboxes)):
                b1, b2 = bboxes[i], bboxes[j]
                # Calculate distance between cluster centers
                c1_x = (b1.x0 + b1.x1) / 2
                c1_y = (b1.y0 + b1.y1) / 2
                c2_x = (b2.x0 + b2.x1) / 2
                c2_y = (b2.y0 + b2.y1) / 2
                
                distance = ((c1_x - c2_x)**2 + (c1_y - c2_y)**2)**0.5
                min_distance = min(min_distance, distance)
        
        # If minimum distance between clusters is large, they're disconnected
        return min_distance > 100  # More than 100 points apart
    
    def _get_cluster_bbox(self, cluster):
        """Get bounding box for a cluster of quads."""
        if not cluster:
            return fitz.Rect()
        
        x0 = min(q.x0 for q in cluster)
        y0 = min(q.y0 for q in cluster)
        x1 = max(q.x1 for q in cluster)
        y1 = max(q.y1 for q in cluster)
        
        return fitz.Rect(x0, y0, x1, y1)
    
    def analyze_pdf(self, pdf_path):
        """Analyze all annotations in a PDF for issues."""
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            return {
                'error': f"Failed to open: {e}",
                'issues': []
            }
        
        file_issues = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            annots = page.annots()
            
            if not annots:
                continue
            
            for annot in annots:
                result = self.analyze_annotation_quads(page, annot)
                if result and result['has_issue']:
                    self.statistics['problematic_annotations'] += 1
                    file_issues.append({
                        'page': page_num + 1,
                        'annotation_data': result
                    })
                
                if result:
                    self.statistics['total_annotations'] += 1
        
        doc.close()
        
        return {
            'issues': file_issues,
            'total_annotations': self.statistics['total_annotations']
        }


def process_all_pdfs(source_dir, output_dir):
    """
    Process all PDFs with highlights, create annotated versions,
    and analyze for issues.
    """
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(source_path.glob("**/*.pdf"))
    pdf_files = [f for f in pdf_files if not f.name.startswith('.')]
    
    print(f"Found {len(pdf_files)} PDF files to analyze")
    
    analyzer = HighlightAnalyzer()
    results = {}
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        
        analyzer.statistics['total_files'] += 1
        
        # Look for corresponding .sdr directory with KRDS files
        sdr_dir = pdf_file.parent / f"{pdf_file.stem}.sdr"
        
        if not sdr_dir.exists():
            print(f"  ⏭️  No .sdr directory found, skipping")
            continue
        
        # Look for KRDS files
        pds_files = list(sdr_dir.glob("*.pds"))
        pdt_files = list(sdr_dir.glob("*.pdt"))
        
        if not pds_files:
            print(f"  ⏭️  No .pds files found, skipping")
            continue
        
        print(f"  📄 Found {len(pds_files)} .pds files")
        
        # Parse KRDS annotations using the Amazon coordinate system
        try:
            book_name = pdf_file.stem
            
            # Look for MyClippings.txt in the .sdr directory or parent
            clippings_file = ""
            
            # Check .sdr directory for clippings
            possible_clippings = [
                sdr_dir / "My Clippings.txt",
                sdr_dir / "MyClippings.txt", 
                sdr_dir / "my clippings.txt",
                sdr_dir.parent / "My Clippings.txt",
                sdr_dir.parent / "MyClippings.txt"
            ]
            
            for clipping_path in possible_clippings:
                if clipping_path.exists():
                    clippings_file = str(clipping_path)
                    print(f"  📋 Found clippings: {clipping_path.name}")
                    break
            
            if not clippings_file:
                print(f"  ⚠️  No clippings file found - using coordinate-only mode")
            
            # For each .pds file, process with clippings if available
            highlights = []
            for pds_file in pds_files:
                annotations = create_amazon_compliant_annotations(
                    str(pds_file),
                    clippings_file,
                    book_name
                )
                
                if annotations:
                    highlights.extend(annotations)
            
            if not highlights:
                print(f"  ⏭️  No highlights extracted")
                continue
            
            print(f"  ✅ Extracted {len(highlights)} highlights")
            analyzer.statistics['files_with_highlights'] += 1
            
        except Exception as e:
            print(f"  ❌ Error processing KRDS: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Create annotated PDF using the Amazon system
        output_pdf = output_path / pdf_file.name
        try:
            # Convert Amazon annotations to PDF annotator format
            pdf_annotations = convert_amazon_to_pdf_annotator_format(highlights)
            
            # Create annotated PDF
            annotate_pdf_file(
                str(pdf_file),
                pdf_annotations,
                str(output_pdf)
            )
            print(f"  ✅ Created annotated PDF: {output_pdf.name}")
        except Exception as e:
            print(f"  ❌ Error creating annotated PDF: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Analyze the annotated PDF
        print(f"  🔍 Analyzing annotations for issues...")
        analysis = analyzer.analyze_pdf(str(output_pdf))
        
        if analysis.get('error'):
            print(f"  ❌ Analysis error: {analysis['error']}")
            continue
        
        if analysis['issues']:
            analyzer.statistics['files_with_issues'] += 1
            print(f"  ⚠️  FOUND {len(analysis['issues'])} PROBLEMATIC ANNOTATIONS!")
            results[pdf_file.name] = {
                'file': str(pdf_file),
                'output': str(output_pdf),
                'total_highlights': len(highlights),
                'issues': analysis['issues']
            }
        else:
            print(f"  ✅ No issues detected")
    
    return results, analyzer.statistics


def generate_report(results, statistics, output_file):
    """Generate detailed bug report."""
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': statistics,
        'files_with_issues': []
    }
    
    for filename, data in results.items():
        file_info = {
            'filename': filename,
            'source_path': data['file'],
            'annotated_path': data['output'],
            'total_highlights': data['total_highlights'],
            'num_issues': len(data['issues']),
            'issues': data['issues']
        }
        report['files_with_issues'].append(file_info)
    
    # Write JSON report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n{'='*80}")
    print("BUG REPORT GENERATED")
    print(f"{'='*80}")
    print(f"\n📊 STATISTICS:")
    print(f"  Total PDFs scanned: {statistics['total_files']}")
    print(f"  Files with highlights: {statistics['files_with_highlights']}")
    print(f"  Files with issues: {statistics['files_with_issues']}")
    print(f"  Total annotations analyzed: {statistics['total_annotations']}")
    print(f"  Problematic annotations: {statistics['problematic_annotations']}")
    
    if statistics['problematic_annotations'] > 0:
        error_rate = (statistics['problematic_annotations'] / 
                     statistics['total_annotations'] * 100)
        print(f"  Error rate: {error_rate:.1f}%")
    
    print(f"\n📝 Detailed report saved to: {output_file}")
    
    if results:
        print(f"\n⚠️  FILES WITH ISSUES:")
        for filename, data in sorted(results.items()):
            print(f"\n  {filename}:")
            print(f"    Total highlights: {data['total_highlights']}")
            print(f"    Issues found: {len(data['issues'])}")
            for issue in data['issues'][:3]:  # Show first 3
                print(f"      - Page {issue['page']}: "
                      f"{issue['annotation_data']['num_clusters']} disconnected regions")
            if len(data['issues']) > 3:
                print(f"      ... and {len(data['issues']) - 3} more")
    else:
        print(f"\n✅ No issues detected across all files!")
    
    print(f"\n{'='*80}\n")


def main():
    """Main execution."""
    print("="*80)
    print("KINDLE PDF ANNOTATOR - MULTIPLE HIGHLIGHT DEBUG SCRIPT")
    print("="*80)
    print("\nThis script will:")
    print("1. Process all PDFs in learn/documents")
    print("2. Extract KRDS highlights and create annotated PDFs")
    print("3. Analyze annotations for multiple disconnected yellow markers")
    print("4. Generate a comprehensive bug report")
    print()
    
    # Set up paths
    project_root = Path(__file__).parent.parent
    source_dir = project_root / "learn" / "documents"
    output_dir = project_root / "learning_output" / "debug_highlights"
    report_file = project_root / "learning_output" / "highlight_bug_report.json"
    
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return 1
    
    print(f"📁 Source directory: {source_dir}")
    print(f"📁 Output directory: {output_dir}")
    print(f"📄 Report file: {report_file}")
    print()
    
    # Process all PDFs
    results, statistics = process_all_pdfs(source_dir, output_dir)
    
    # Generate report
    generate_report(results, statistics, report_file)
    
    return 0 if not results else 1  # Exit code 1 if issues found


if __name__ == "__main__":
    sys.exit(main())
