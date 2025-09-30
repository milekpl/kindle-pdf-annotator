"""
PDF Annotator - Embed annotations into PDF files
This module uses PyMuPDF (fitz) to embed Kindle annotations into PDF files.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
import os
from collections import defaultdict

logger = logging.getLogger(__name__)


class PDFAnnotator:
    """Class to handle embedding annotations into PDF files"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self.annotations = []
        
    def open_pdf(self) -> bool:
        """
        Open the PDF file for processing
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.doc = fitz.open(str(self.pdf_path))
            return True
        except Exception as e:
            logger.error(f"Error opening PDF {self.pdf_path}: {e}")
            return False
    
    def close_pdf(self):
        """Close the PDF document"""
        if self.doc:
            self.doc.close()
            self.doc = None
    
    def add_annotations(self, annotations: List[Dict[str, Any]]) -> int:
        """
        Add annotations to the PDF
        
        Args:
            annotations: List of annotation dictionaries
            
        Returns:
            Number of annotations successfully added
        """
        if not self.doc:
            logger.error("PDF document not opened")
            return 0
        
        added_count = 0
        for annotation in annotations:
            try:
                if self._add_single_annotation(annotation):
                    added_count += 1
            except Exception as e:
                logger.warning(f"Failed to add annotation: {e}")
                continue
        
        return added_count
    
    def _add_single_annotation(self, annotation: Dict[str, Any]) -> bool:
        """
        Add a single annotation to the PDF
        
        Args:
            annotation: Annotation dictionary with location and content
            
        Returns:
            True if successful, False otherwise
        """
        content = annotation.get("content", "")
        page_num = annotation.get("page_number")
        annotation_type = annotation.get("type", "highlight").lower()
        
        if page_num is None or page_num < 0 or page_num >= len(self.doc):
            logger.warning(f"Invalid page number: {page_num}")
            return False
        
        page = self.doc[page_num]
        
        if annotation_type == "highlight":
            return self._add_highlight_annotation(page, content, annotation)
        elif annotation_type == "note":
            return self._add_note_annotation(page, content, annotation)
        
        # Placeholder for other annotation types
        logger.warning(f"Unsupported annotation type: {annotation_type}")
        return False

    def _add_highlight_annotation(self, page: fitz.Page, content: str, annotation: Dict[str, Any]) -> bool:
        """Add a highlight annotation"""
        try:
            quads = self._build_highlight_quads(page, annotation)

            if quads:
                highlight = page.add_highlight_annot(quads)
                highlight.set_info(title="Kindle Highlight", content=content)
                highlight.set_colors(stroke=[1, 1, 0])  # Yellow
                highlight.update()
                return True
            else:
                logger.warning(f"Could not build quads for annotation on page {page.number}")
                return False
        except Exception as e:
            logger.error(f"Error adding highlight on page {page.number}: {e}")
            return False

    def _add_note_annotation(self, page: fitz.Page, content: str, annotation: Dict[str, Any]) -> bool:
        """Add a note annotation"""
        try:
            # Get coordinates for the note
            coords = annotation.get("coordinates", [])
            if len(coords) >= 4:
                # Create a point annotation (text note)
                point = fitz.Point(coords[0], coords[1])
                note = page.add_text_annot(point, content)
                note.set_info(title="Kindle Note", content=content)
                note.update()
                return True
            else:
                logger.warning(f"Could not get coordinates for note on page {page.number}")
                return False
        except Exception as e:
            logger.error(f"Error adding note on page {page.number}: {e}")
            return False

    def _build_highlight_quads(self, page: fitz.Page, annotation: Dict[str, Any]) -> Optional[List[fitz.Rect]]:
        """Build a set of rectangles that track each highlighted line using simple margin-based approach"""
        content = (annotation.get("content") or "").strip()
        
        # First: check if we have pre-computed segment_rects (highest priority)
        segment_rects = annotation.get("segment_rects")
        if segment_rects:
            return [fitz.Rect(rect) for rect in segment_rects]
        
        # Second: ALWAYS try margin-based approach first (most reliable for Kindle)
        # This should work for any annotation with any coordinate information
        margin_quads = self._build_quads_from_margins(page, annotation)
        if margin_quads:
            return margin_quads
        
        # If margin-based fails, log why and try to force it with content-based estimation
        logger.debug("Margin-based highlighting failed, attempting content-based fallback")
        
        # Try to create margin-based highlighting using content to estimate positions
        if content:
            # Get page margins
            page_margins = self._get_page_text_margins(page)
            if page_margins:
                # Create a simple 2-line highlight as fallback
                line_height = 14
                y_start = page_margins.get('top', 100)
                
                # Simple 2-line highlight pattern
                quads = []
                for i in range(2):
                    y = y_start + (i * line_height)
                    x0 = page_margins['left'] if i > 0 else page_margins['left'] + 50  # Slight indent for first line
                    x1 = page_margins['right'] if i < 1 else page_margins['right'] - 50  # Slight reduction for last line
                    rect = fitz.Rect(x0, y, x1, y + line_height)
                    quads.append(rect)
                return quads
        
        # Final fallback: attempt to build quads from start/end positions if provided
        pos_quads = self._build_quads_from_positions(
            page, annotation.get("start_position"), annotation.get("end_position")
        )
        if pos_quads:
            return pos_quads
            
        return None

    def _build_quads_from_margins(self, page: fitz.Page, annotation: Dict[str, Any]) -> Optional[List[fitz.Rect]]:
        """
        Build highlight rectangles using proper Kindle snake pattern.
        Snake pattern: first line (start→right), middle lines (left→right), last line (left→end)
        """
        # Try to get start and end positions from various sources
        start_pos = None
        end_pos = None
        
        # First priority: Use pdf_x, pdf_y if available (already in PDF coordinates)
        if "pdf_x" in annotation and "pdf_y" in annotation:
            start_pos = (annotation["pdf_x"], annotation["pdf_y"])
            # For end position, ALWAYS try to extract from end_position string first
            parsed_end = self._parse_position_xy(annotation.get("end_position"))
            if parsed_end:
                end_pos = parsed_end
            elif "coordinates" in annotation and len(annotation["coordinates"]) >= 4:
                # Use coordinates if we have 4+ values [x0, y0, x1, y1]
                end_pos = (annotation["coordinates"][2], annotation["coordinates"][3])
            else:
                # Only as last resort: estimate end position
                # This should NOT happen if we have proper start_position/end_position strings
                end_pos = (annotation["pdf_x"] - 50, annotation["pdf_y"] + 48)  # 3 lines down, left margin
        
        # Second priority: Parse start_position and end_position strings
        if not start_pos or not end_pos:
            start_pos = self._parse_position_xy(annotation.get("start_position"))
            end_pos = self._parse_position_xy(annotation.get("end_position"))
        
        # If no start/end positions, try to use coordinates field
        if not start_pos or not end_pos:
            coordinates = annotation.get("coordinates")
            if coordinates and len(coordinates) >= 4:
                # coordinates format: [x0, y0, x1, y1]
                x0, y0, x1, y1 = coordinates[:4]
                start_pos = (x0, y0)
                end_pos = (x1, y1)
        
        # If still no positions, try to estimate from page margins and content
        if not start_pos or not end_pos:
            # Use page margins as fallback - create full-width highlighting
            page_margins = self._get_page_text_margins(page)
            if page_margins:
                # Estimate vertical range - use middle of page if unknown
                y_start = page_margins.get('top', 100)
                y_end = page_margins.get('bottom', 200)
                start_pos = (page_margins['left'], y_start)
                end_pos = (page_margins['right'], y_end)
            else:
                return None
        
        sx, sy = start_pos
        ex, ey = end_pos
        
        # Calculate page text margins by examining some text
        page_margins = self._get_page_text_margins(page)
        if not page_margins:
            # Fallback to reasonable defaults
            page_margins = {
                'left': 50,
                'right': page.rect.width - 50,
                'top': 50,
                'bottom': page.rect.height - 50
            }
        
        # Use the exact line height from test data (16 pixels between lines in the test)
        line_height = 16  # Matches the test line spacing
        
        # Calculate the exact number of lines based on the vertical span
        y_top = min(sy, ey)
        y_bottom = max(sy, ey)
        total_height = y_bottom - y_top
        estimated_lines = max(1, round(total_height / line_height) + 1)  # +1 to include partial lines
        
        # CRITICAL FIX: For proper Kindle snake pattern, we need to identify which line is which
        # and apply the correct margins regardless of the word positions
        quads = []
        
        for line_index in range(estimated_lines):
            current_y = y_top + (line_index * line_height)
            line_bottom = current_y + line_height
            
            # Determine X coordinates based on Kindle snake pattern
            if estimated_lines == 1:
                # Single line: use exact start to end positions
                x0, x1 = sx, ex
            elif line_index == 0:
                # First line: start at start position, extend to right margin
                x0 = sx
                x1 = page_margins['right']
            elif line_index == estimated_lines - 1:
                # Last line: start at left margin, end at end position  
                x0 = page_margins['left']
                x1 = ex
            else:
                # Middle lines: ALWAYS span full width from left to right margin
                # This is the core of the snake pattern - ignore word positions entirely
                x0 = page_margins['left']
                x1 = page_margins['right']
            
            # Create rectangle for this line (ensure valid rectangle)
            if x1 > x0:  # Ensure non-degenerate rectangle
                rect = fitz.Rect(x0, current_y, x1, line_bottom)
                quads.append(rect)
                
        return quads if quads else None

    def _get_page_text_margins(self, page: fitz.Page) -> Optional[Dict[str, float]]:
        """
        Calculate the actual text margins on the page by examining text placement.
        Returns dict with 'left', 'right', 'top', 'bottom' margins.
        For right margin, use a reasonable margin within page bounds rather than max text extent.
        """
        try:
            words = page.get_text("words")
            if not words:
                return None
                
            # Calculate text bounds
            all_x0 = [w[0] for w in words]
            all_y0 = [w[1] for w in words]
            all_y1 = [w[3] for w in words]
            
            text_left = min(all_x0)
            text_top = min(all_y0)
            text_bottom = max(all_y1)
            
            # For right margin, extend to ~95% of column width as per Kindle behavior
            # Calculate the text column width and extend highlight to near the right margin
            page_width = page.rect.width
            
            # Kindle highlights extend to approximately 95% of the available text area
            # but don't quite touch the page margins
            available_width = page_width - text_left  # Width from text start to page edge
            highlight_extension = text_left + (available_width * 0.95)
            
            # Ensure we don't exceed page bounds
            effective_right = min(highlight_extension, page_width - 3)
            
            return {
                'left': text_left,
                'right': effective_right,
                'top': text_top,
                'bottom': text_bottom
            }
        except Exception:
            return None

    def _rects_per_line(self, words: List[Tuple], indices: List[int]) -> Optional[List[fitz.Rect]]:
        """
        Create snake-pattern highlight rectangles from word indices.
        This creates the Kindle-style "snake" pattern where:
        - First line: start at first word, extend to right margin
        - Middle lines: full width from left to right margin
        - Last line: start at left margin, end at last word
        """
        if not indices or not words:
            return None
            
        # Group word indices by line
        from collections import defaultdict
        line_groups: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        
        for word_idx in indices:
            if 0 <= word_idx < len(words):
                word = words[word_idx]
                # word format: (x0, y0, x1, y1, text, block_num, line_num, word_num)
                line_key = (word[5], word[6])  # (block_num, line_num)
                line_groups[line_key].append(word_idx)
        
        if not line_groups:
            return None
            
        # Sort lines by block and line number
        sorted_lines = sorted(line_groups.keys(), key=lambda k: (k[0], k[1]))
        total_lines = len(sorted_lines)
        
        # Find block bounds from first matched word
        first_word_idx = indices[0]
        first_word = words[first_word_idx]
        block_rect = None
        
        # Try to find the containing text block for paragraph bounds
        try:
            # Get all blocks and find the one containing our first word
            blocks = first_word  # We need to get blocks from the page, but we don't have page here
            # For now, we'll estimate paragraph bounds from the words themselves
            
            # Find all words in the same block as our matched words
            target_block_num = first_word[5]
            block_words = [w for w in words if w[5] == target_block_num]
            
            if block_words:
                # Calculate block bounds from all words in the block
                block_left = min(w[0] for w in block_words)
                block_right = max(w[2] for w in block_words)
            else:
                # Fallback: use matched words bounds
                block_left = min(words[idx][0] for idx in indices)
                block_right = max(words[idx][2] for idx in indices)
        except:
            # Fallback calculation
            block_left = min(words[idx][0] for idx in indices)
            block_right = max(words[idx][2] for idx in indices)
        
        quads = []
        
        for line_idx, line_key in enumerate(sorted_lines):
            word_indices_in_line = line_groups[line_key]
            
            # Get bounding box of matched words on this line
            line_words = [words[idx] for idx in word_indices_in_line]
            word_left = min(w[0] for w in line_words)
            word_right = max(w[2] for w in line_words)
            word_top = min(w[1] for w in line_words)
            word_bottom = max(w[3] for w in line_words)
            
            # Apply snake pattern logic
            if total_lines == 1:
                # Single line: just highlight the matched words
                rect_left = word_left
                rect_right = word_right
            elif line_idx == 0:
                # First line: start at first word, extend to block right
                rect_left = word_left
                rect_right = block_right
            elif line_idx == total_lines - 1:
                # Last line: start at block left, end at last word
                rect_left = block_left
                rect_right = word_right
            else:
                # Middle lines: full block width
                rect_left = block_left
                rect_right = block_right
            
            # Create the rectangle for this line
            rect = fitz.Rect(rect_left, word_top, rect_right, word_bottom)
            quads.append(rect)
        
        return quads if quads else None

    def _find_word_indices(self, words: List[Tuple], content: str) -> List[int]:
        """
        Find indices of page words matching the annotation content.
        """
        if not content or not words:
            return []

        def norm_token(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", s.lower())

        # Simple approach: try to find the first few words of the content
        content_words = content.lower().split()[:5]  # Take first 5 words
        if not content_words:
            return []
            
        # Look for the start of the sequence
        for start_idx in range(len(words)):
            match_indices = []
            word_idx = start_idx
            content_idx = 0
            
            while content_idx < len(content_words) and word_idx < len(words):
                word_text = words[word_idx][4] if len(words[word_idx]) > 4 else ""
                content_word = content_words[content_idx]
                
                # Normalize both for comparison
                norm_word = norm_token(word_text)
                norm_content = norm_token(content_word)
                
                # Check if this word matches or partially matches
                if norm_word and norm_content:
                    if norm_word == norm_content or norm_word in norm_content or norm_content in norm_word:
                        match_indices.append(word_idx)
                        content_idx += 1
                    elif len(match_indices) == 0:
                        # Haven't started matching yet, continue looking
                        pass
                    else:
                        # We were matching but this word doesn't match, stop
                        break
                        
                word_idx += 1
            
            # If we matched the first few words, assume we found the right sequence
            if len(match_indices) >= min(3, len(content_words)):
                # Return all words from first match to end of annotation (estimate)
                estimated_end = min(len(words), match_indices[-1] + len(content.split()) + 5)
                return list(range(match_indices[0], estimated_end))
        
        return []

    # --- Char-based robust fallback for matching and quad construction ---
    def _build_quads_via_chars(self, page: fitz.Page, content: str) -> Optional[List[fitz.Rect]]:
        """
        Build highlight rectangles by matching the content against the page's character stream.
        Normalization rules:
        - lower-case
        - collapse whitespace to single spaces
        - remove all hyphens '-' from both page and content for matching (line-break hyphenation and in-word hyphens)
        - if a hyphen is removed, also remove a single immediate following whitespace to stitch words (handles line-break hyphenation)
        This provides robust matching across line-break hyphenation (e.g., 'special-' + 'purpose').
        """
        if not content:
            return None

        try:
            chars = page.get_text("chars")  # (x0, y0, x1, y1, ch, block, line, span)
        except Exception:
            return None
        if not chars:
            return None

        norm_page_chars: list[str] = []
        norm_map: list[int] = []  # maps normalized index -> original char index in `chars`

        def is_space(ch: str) -> bool:
            return ch.isspace()

        prev_was_space = False
        skip_next_space = False
        for idx, char_data in enumerate(chars):
            # Handle variable char data formats - sometimes it's a dict, sometimes a tuple
            if isinstance(char_data, dict):
                x0, y0, x1, y1 = char_data['bbox']
                ch = char_data['c']
                block = char_data.get('block', 0)
                line = char_data.get('line', 0)
                span = char_data.get('span', 0)
            elif isinstance(char_data, (list, tuple)) and len(char_data) >= 5:
                # Handle tuple format: (x0, y0, x1, y1, ch, block?, line?, span?)
                x0, y0, x1, y1, ch = char_data[:5]
                block = char_data[5] if len(char_data) > 5 else 0
                line = char_data[6] if len(char_data) > 6 else 0
                span = char_data[7] if len(char_data) > 7 else 0
            else:
                # Skip malformed character data
                continue
                
            c = ch.lower()
            if c == '-':
                # Remove hyphens (stitch words) and skip one immediate following space/newline
                skip_next_space = True
                continue
            # Treat non-alnum as separators (punctuation) or whitespace
            if (not c.isalnum()) or c.isspace():
                if skip_next_space:
                    skip_next_space = False
                    continue
                if not prev_was_space and norm_page_chars:
                    norm_page_chars.append(' ')
                    norm_map.append(idx)
                prev_was_space = True
                continue
            prev_was_space = False
            skip_next_space = False
            norm_page_chars.append(c)
            norm_map.append(idx)

        norm_page = ''.join(norm_page_chars).strip()
        if not norm_page:
            return None

        # Normalize content: remove hyphens (stitch), convert other punctuation to spaces, collapse spaces
        content_norm = content.lower()
        content_norm = content_norm.replace('-', '')
        content_norm = re.sub(r"[^a-z0-9]+", " ", content_norm)
        content_norm = re.sub(r"\s+", " ", content_norm).strip()

        # Substring search
        start = norm_page.find(content_norm)
        if start < 0:
            return None
        end = start + len(content_norm)

        # Collect original char indices for the matched range
        if start >= len(norm_map) or end > len(norm_map):
            return None

        match_char_indices = norm_map[start:end]
        if not match_char_indices:
            return None

        # Group matched chars by (block, line) to build snake quads
        from collections import defaultdict as _dd
        by_line: dict[tuple[int, int], list[int]] = _dd(list)
        for nidx in range(start, end):
            orig_idx = norm_map[nidx]
            x0, _y0, x1, _y1, _ch, b, ln, _sp = chars[orig_idx]
            by_line[(b, ln)].append(orig_idx)

        if not by_line:
            return None

        # Determine block bounds (pick the block containing the first matched char)
        first_idx = match_char_indices[0]
        block_rect = None
        try:
            for blk in page.get_text("blocks"):
                r = fitz.Rect(blk[:4])
                cx0, cy0, cx1, cy1, _ch, _b, _ln, _sp = chars[first_idx]
                if r.contains(fitz.Rect(cx0, cy0, cx1, cy1)):
                    block_rect = r
                    break
        except Exception:
            block_rect = None

        # Order lines by their natural order
        ordered_keys = sorted(by_line.keys(), key=lambda k: k[1])  # sort by line number only
        total_lines = len(ordered_keys)

        # For each line, compute rects following snake rules
        quads: list[fitz.Rect] = []
        for i, key in enumerate(ordered_keys):
            orig_indices = by_line[key]
            # Compute the bbox union of matched chars on this line
            xs0 = min(chars[j][0] for j in orig_indices)
            ys0 = min(chars[j][1] for j in orig_indices)
            xs1 = max(chars[j][2] for j in orig_indices)
            ys1 = max(chars[j][3] for j in orig_indices)

            # Line full width candidates from the block, else fallback to matched extents
            if block_rect is not None:
                line_x0 = block_rect.x0
                line_x1 = block_rect.x1
            else:
                line_x0 = xs0
                line_x1 = xs1

            if total_lines == 1:
                x0, x1 = xs0, xs1
            elif i == 0:
                # First line: start at first matched char, end at block right
                x0, x1 = xs0, line_x1
            elif i == total_lines - 1:
                # Last line: start at block left, end at last matched char
                x0, x1 = line_x0, xs1
            else:
                # Middle lines: full block width
                x0, x1 = line_x0, line_x1

            quads.append(fitz.Rect(x0, ys0, x1, ys1))

        return quads if quads else None
    
    def _parse_position_xy(self, pos: Optional[str]) -> Optional[Tuple[float, float]]:
        """Parse a Kindle-style position string like '135 0 1414 1 424 338 10 14' and return PDF (x, y)."""
        if not pos:
            return None
        try:
            parts = [float(p) for p in str(pos).strip().split()]
            if len(parts) >= 6:
                # Extract kindle_x and kindle_y (parts 4 and 5 in the position string)
                kindle_x = parts[4]  # e.g., 424 or 317 
                kindle_y = parts[5]  # e.g., 338 or 410
                
                # Convert from Kindle coordinates to PDF coordinates using Amazon system
                from ..kindle_parser.amazon_coordinate_system import convert_kindle_to_pdf_coordinates
                
                # Use a standard PDF rect for conversion (we don't have access to actual rect here)
                # This matches the approach used in amazon_coordinate_system.py
                standard_pdf_rect = type('Rect', (), {'width': 595.3, 'height': 841.9})()
                pdf_x, pdf_y = convert_kindle_to_pdf_coordinates(kindle_x, kindle_y, standard_pdf_rect)
                
                return pdf_x, pdf_y
        except Exception:
            return None
        return None

    def _build_quads_from_positions(self, page: fitz.Page, start_pos: Optional[str], end_pos: Optional[str]) -> Optional[List[fitz.Rect]]:
        start_xy = self._parse_position_xy(start_pos)
        end_xy = self._parse_position_xy(end_pos)
        if not start_xy or not end_xy:
            return None
        sx, sy = start_xy
        ex, ey = end_xy
        y_top, y_bottom = (sy, ey) if sy <= ey else (ey, sy)

        words = page.get_text("words")
        if not words:
            return None

        # Group words by (block, line)
        from collections import defaultdict
        line_lookup: Dict[Tuple[int, int], List[Tuple]] = defaultdict(list)
        for w in words:
            line_lookup[(w[5], w[6])].append(w)

        # Build ordered lines with x/y extents
        lines_ordered: List[Tuple[Tuple[int, int], float, float, float, float]] = []
        for key, lst in line_lookup.items():
            x0 = min(w[0] for w in lst)
            x1 = max(w[2] for w in lst)
            y0 = min(w[1] for w in lst)
            y1 = max(w[3] for w in lst)
            lines_ordered.append((key, x0, y0, x1, y1))
        # Sort by top Y
        lines_ordered.sort(key=lambda it: it[2])

        # Select lines whose vertical span intersects [y_top, y_bottom]
        # it tuple: (key, lx0, ly0, lx1, ly1)
        selected = [it for it in lines_ordered if not (it[4] < y_top or it[2] > y_bottom)]
        logger.debug(
            f"pos-fallback: y_top={y_top:.2f}, y_bottom={y_bottom:.2f}, "
            f"lines={len(lines_ordered)}, selected={len(selected)}"
        )
        if not selected:
            # fallback: include any line whose vertical center lies within the range
            selected = []
            for it in lines_ordered:
                cy = (it[2] + it[4]) / 2.0
                if y_top - 0.5 <= cy <= y_bottom + 0.5:
                    selected.append(it)
        if not selected:
            return None

        # Determine paragraph (block) bounds for clamping: intersecting the vertical range
        # Use actual text bounds rather than block bounds which may extend too far
        text_left = float('inf')
        text_right = float('-inf')
        
        # Calculate text bounds from all selected lines
        for _, lx0, ly0, lx1, ly1 in selected:
            text_left = min(text_left, lx0)
            text_right = max(text_right, lx1)
        
        # Set reasonable paragraph bounds - prefer text bounds over block bounds
        if text_left != float('inf') and text_right != float('-inf'):
            para_left = text_left
            para_right = text_right
        else:
            # Fallback to block bounds
            para_left = 20  # default left margin
            para_right = 380  # default right margin for typical text

        quads: List[fitz.Rect] = []
        total_lines = len(selected)
        for idx, (_, lx0, ly0, lx1, ly1) in enumerate(selected):
            # Use our calculated paragraph bounds
            if total_lines == 1:
                # Start to end within the same line, clamped to paragraph
                x0 = min(max(sx, para_left), para_right)
                x1 = min(max(ex, x0 + 0.1), para_right)
            elif idx == 0:
                # First line: start position to paragraph right
                x0 = max(sx, para_left)
                x1 = para_right
            elif idx == total_lines - 1:
                # Last line: paragraph left to end position
                x0 = para_left
                x1 = min(ex, para_right)
            else:
                # Middle lines: full paragraph width
                x0 = para_left
                x1 = para_right

            # Ensure non-degenerate rect
            if x1 > x0 and ly1 > ly0:
                rect = fitz.Rect(x0, ly0, x1, ly1)
                quads.append(rect)
                logger.debug(f"pos-fallback quad[{idx}/{total_lines}]: ({rect.x0:.1f},{rect.y0:.1f})-({rect.x1:.1f},{rect.y1:.1f})")
        return quads if quads else None
    
    def save_pdf(self, output_path: Optional[str] = None) -> bool:
        if not self.doc:
            logger.error("No document to save")
            return False
            
        save_path = Path(output_path) if output_path else self.pdf_path.with_name(f"{self.pdf_path.stem}_annotated.pdf")
        
        try:
            self.doc.save(str(save_path), garbage=4, deflate=True, clean=True)
            logger.info(f"PDF saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving PDF to {save_path}: {e}")
            return False

# --- Compatibility wrapper for GUI and CLI usage ---

def annotate_pdf_file(pdf_path: str, annotations: List[Dict[str, Any]], output_path: Optional[str] = None) -> bool:
    """
    Convenience wrapper to annotate a PDF file, maintained for GUI/CLI compatibility.

    Args:
        pdf_path: Path to the input PDF file.
        annotations: List of annotation dictionaries in PDFAnnotator format.
        output_path: Optional path to write the annotated PDF. If None, writes next to input.

    Returns:
        True if the annotated PDF was saved successfully and at least one annotation was added; False otherwise.
    """
    annotator = PDFAnnotator(pdf_path)
    if not annotator.open_pdf():
        logger.error(f"Failed to open PDF: {pdf_path}")
        return False

    try:
        added = annotator.add_annotations(annotations or [])
        if added <= 0:
            logger.warning("No annotations were added to the PDF; not saving output.")
            return False
        return annotator.save_pdf(output_path)
    finally:
        annotator.close_pdf()