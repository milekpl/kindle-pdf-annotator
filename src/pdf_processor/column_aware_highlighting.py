#!/usr/bin/env python3
"""
Column-aware highlighting module for two-column PDFs.
Detects column boundaries and constrains highlights within columns.
"""

import fitz
from typing import List, Dict, Tuple, Optional


class ColumnDetector:
    """Detects and manages column boundaries in PDFs"""
    
    def __init__(self, doc: fitz.Document):
        self.doc = doc
        self.column_cache = {}  # Cache columns per page
    
    def get_columns_for_page(self, page_num: int) -> List[Dict[str, float]]:
        """Get column definitions for a specific page"""
        if page_num not in self.column_cache:
            page = self.doc[page_num]
            self.column_cache[page_num] = self._detect_columns(page)
        return self.column_cache[page_num]
    
    def _detect_columns(self, page: fitz.Page) -> List[Dict[str, float]]:
        """Detect column boundaries by analyzing flowing two-column text layout"""
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [block for block in blocks if block.get("type") == 0]
        
        if not text_blocks:
            # No text blocks, assume single column
            return [{
                'left': 50,
                'right': page.rect.width - 50,
                'top': 50,
                'bottom': page.rect.height - 50
            }]
        
        # Collect all text lines for flowing column analysis
        all_lines = []
        for block in text_blocks:
            for line in block.get("lines", []):
                if line.get("spans"):
                    # Get line bounding box
                    line_bbox = line["bbox"]
                    all_lines.append({
                        'left': line_bbox[0],
                        'right': line_bbox[2], 
                        'top': line_bbox[1],
                        'bottom': line_bbox[3],
                        'width': line_bbox[2] - line_bbox[0]
                    })
        
        if len(all_lines) < 15:  # Need enough lines for reliable column detection
            # Fallback to single column
            min_left = min(line['left'] for line in all_lines) if all_lines else 50
            max_right = max(line['right'] for line in all_lines) if all_lines else page.rect.width - 50
            return [{
                'left': min_left,
                'right': max_right,
                'top': 50,
                'bottom': page.rect.height - 50
            }]
        
        # Analyze left margin positions to detect column starts
        left_positions = [line['left'] for line in all_lines]
        
        # Group similar left positions (within tolerance)
        from collections import defaultdict
        margin_groups = defaultdict(list)
        tolerance = 15  # Points
        
        for pos in left_positions:
            # Find the closest existing group or create new one
            found_group = None
            for group_pos in margin_groups.keys():
                if abs(pos - group_pos) <= tolerance:
                    found_group = group_pos
                    break
            
            if found_group is not None:
                margin_groups[found_group].append(pos)
            else:
                margin_groups[pos] = [pos]
        
        # Find the two most common margin positions
        margin_counts = [(pos, len(positions)) for pos, positions in margin_groups.items()]
        margin_counts.sort(key=lambda x: x[1], reverse=True)
        
        # Check if we have two significant margin groups (indicating two columns)
        if len(margin_counts) >= 2 and margin_counts[1][1] >= 10:  # Second group has at least 10 lines
            left_margin = margin_counts[0][0]
            right_margin = margin_counts[1][0]
            
            # Ensure proper left/right order
            if left_margin > right_margin:
                left_margin, right_margin = right_margin, left_margin
            
            # Check if the gap between margins is significant enough for two columns
            gap = right_margin - left_margin
            if gap > 50:  # Significant gap suggests two columns
                
                # Calculate column boundaries based on actual text
                left_column_lines = [line for line in all_lines if abs(line['left'] - left_margin) <= tolerance]
                right_column_lines = [line for line in all_lines if abs(line['left'] - right_margin) <= tolerance]
                
                columns = []
                
                if left_column_lines:
                    col_left = min(line['left'] for line in left_column_lines)
                    col_right = max(line['right'] for line in left_column_lines)
                    col_top = min(line['top'] for line in left_column_lines)
                    col_bottom = max(line['bottom'] for line in left_column_lines)
                    
                    # Ensure column doesn't extend into right column area
                    col_right = min(col_right, right_margin - 10)
                    
                    columns.append({
                        'left': col_left,
                        'right': col_right,
                        'top': col_top,
                        'bottom': col_bottom
                    })
                
                if right_column_lines:
                    col_left = min(line['left'] for line in right_column_lines)
                    col_right = max(line['right'] for line in right_column_lines)
                    col_top = min(line['top'] for line in right_column_lines)
                    col_bottom = max(line['bottom'] for line in right_column_lines)
                    
                    columns.append({
                        'left': col_left,
                        'right': col_right,
                        'top': col_top,
                        'bottom': col_bottom
                    })
                
                if len(columns) == 2:
                    return columns
        
        # Fallback: single column based on all text
        min_left = min(line['left'] for line in all_lines)
        max_right = max(line['right'] for line in all_lines)
        min_top = min(line['top'] for line in all_lines)
        max_bottom = max(line['bottom'] for line in all_lines)
        
        return [{
            'left': min_left,
            'right': max_right,
            'top': min_top,
            'bottom': max_bottom
        }]
    
    def _cluster_text_positions(self, lines: List[Dict], page_width: float) -> List[Dict[str, float]]:
        """Cluster text lines to detect columns using improved algorithm"""
        if len(lines) < 10:
            # Not enough data for reliable clustering
            min_left = min(line['left'] for line in lines)
            max_right = max(line['right'] for line in lines)
            min_top = min(line['top'] for line in lines)
            max_bottom = max(line['bottom'] for line in lines)
            
            return [{
                'left': min_left,
                'right': max_right,
                'top': min_top,
                'bottom': max_bottom
            }]
        
        # Analyze line start positions and widths to find column patterns
        left_positions = [line['left'] for line in lines]
        right_positions = [line['right'] for line in lines]
        widths = [line['width'] for line in lines]
        
        # Group lines by similar left positions (within tolerance)
        tolerance = 20  # Points
        left_clusters = []
        
        for pos in sorted(set(left_positions)):
            cluster_lines = [line for line in lines if abs(line['left'] - pos) <= tolerance]
            if len(cluster_lines) >= 3:  # Need significant number of lines
                left_clusters.append({
                    'left': pos,
                    'lines': cluster_lines,
                    'avg_width': sum(line['width'] for line in cluster_lines) / len(cluster_lines)
                })
        
        # If we have 2 significant left clusters, it's likely two columns
        if len(left_clusters) >= 2:
            # Sort by left position
            left_clusters.sort(key=lambda c: c['left'])
            
            # Find the gap between clusters
            cluster1 = left_clusters[0]
            cluster2 = left_clusters[1] if len(left_clusters) > 1 else None
            
            # Check if there's a significant gap between clusters
            if cluster2 and (cluster2['left'] - cluster1['left']) > 50:
                columns = []
                
                # First column
                col1_lines = cluster1['lines']
                col1_left = min(line['left'] for line in col1_lines)
                col1_right = max(line['right'] for line in col1_lines)
                col1_top = min(line['top'] for line in col1_lines)
                col1_bottom = max(line['bottom'] for line in col1_lines)
                
                columns.append({
                    'left': col1_left,
                    'right': col1_right,
                    'top': col1_top,
                    'bottom': col1_bottom
                })
                
                # Second column
                col2_lines = cluster2['lines']
                col2_left = min(line['left'] for line in col2_lines)
                col2_right = max(line['right'] for line in col2_lines)
                col2_top = min(line['top'] for line in col2_lines)
                col2_bottom = max(line['bottom'] for line in col2_lines)
                
                columns.append({
                    'left': col2_left,
                    'right': col2_right,
                    'top': col2_top,
                    'bottom': col2_bottom
                })
                
                return columns
        
        # Fallback: single column
        min_left = min(line['left'] for line in lines)
        max_right = max(line['right'] for line in lines)
        min_top = min(line['top'] for line in lines)
        max_bottom = max(line['bottom'] for line in lines)
        
        return [{
            'left': min_left,
            'right': max_right,
            'top': min_top,
            'bottom': max_bottom
        }]
    
    def get_column_for_position(self, page_num: int, x: float, y: float) -> Optional[Dict[str, float]]:
        """Determine which column a position belongs to, with fallback to nearest column"""
        columns = self.get_columns_for_page(page_num)
        
        # First, try exact match
        for column in columns:
            if (column['left'] <= x <= column['right'] and 
                column['top'] <= y <= column['bottom']):
                return column
        
        # If no exact match, find the nearest column by X position
        if columns:
            if len(columns) == 1:
                return columns[0]
            
            # For multi-column layout, assign to nearest column by X coordinate
            nearest_column = None
            min_distance = float('inf')
            
            for column in columns:
                # Calculate distance to column center
                col_center_x = (column['left'] + column['right']) / 2
                distance = abs(x - col_center_x)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_column = column
            
            return nearest_column
        
        return None
    
    def constrain_to_column(self, page_num: int, x: float, y: float, width: float) -> Tuple[float, float]:
        """Constrain a highlight width to stay within column boundaries"""
        column = self.get_column_for_position(page_num, x, y)
        if column:
            # Ensure highlight doesn't exceed column boundaries
            max_right = column['right']
            constrained_width = min(width, max_right - x)
            return x, max(constrained_width, 10)  # Minimum width of 10
        return x, width
    
    def create_column_aware_quads(self, page_num: int, rects: List[List[float]]) -> List[List[float]]:
        """Create quads that respect column boundaries for multi-line highlights"""
        if not rects:
            return []
        
        columns = self.get_columns_for_page(page_num)
        column_aware_quads = []
        
        for rect in rects:
            x0, y0, x1, y1 = rect
            
            # Find which column this rect belongs to
            center_x = (x0 + x1) / 2
            center_y = (y0 + y1) / 2
            column = self.get_column_for_position(page_num, center_x, center_y)
            
            if column:
                # Constrain rect to column boundaries
                constrained_x0 = max(x0, column['left'])
                constrained_x1 = min(x1, column['right'])
                
                # Only add rect if it has meaningful width after constraining
                if constrained_x1 - constrained_x0 > 5:
                    column_aware_quads.append([constrained_x0, y0, constrained_x1, y1])
            else:
                # No column found, use original rect
                column_aware_quads.append(rect)
        
        return column_aware_quads
    
    def is_multi_column_layout(self, page_num: int) -> bool:
        """Check if a page has a multi-column layout"""
        columns = self.get_columns_for_page(page_num)
        return len(columns) > 1
    
    def get_column_separation_width(self, page_num: int) -> float:
        """Get the width of the gap between columns"""
        columns = self.get_columns_for_page(page_num)
        if len(columns) > 1:
            return columns[1]['left'] - columns[0]['right']
        return 0.0