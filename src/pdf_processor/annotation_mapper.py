"""
Annotation Mapper - Map Kindle annotations to PDF coordinates
This module handles the complex task of mapping Kindle location data
to actual PDF coordinates and text positions.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class AnnotationMapper:
    """Maps Kindle annotations to PDF coordinates"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self.text_blocks = []  # Cache of text blocks from PDF
        self.location_map = {}  # Maps locations to coordinates
        
    def open_pdf(self) -> bool:
        """Open PDF and extract text blocks for mapping"""
        try:
            self.doc = fitz.open(str(self.pdf_path))
            self._extract_text_blocks()
            return True
        except Exception as e:
            logger.error(f"Error opening PDF for mapping: {e}")
            return False
    
    def close_pdf(self):
        """Close the PDF document"""
        if self.doc:
            self.doc.close()
            self.doc = None
    
    def _extract_text_blocks(self):
        """Extract text blocks from all pages for mapping"""
        self.text_blocks = []
        
        for page_num in range(len(self.doc)):
            try:
                page = self.doc[page_num]
                blocks = page.get_text("dict")
                
                for block in blocks.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line.get("spans", []):
                                text = span.get("text", "").strip()
                                if text:
                                    bbox = span.get("bbox", [0, 0, 0, 0])
                                    self.text_blocks.append({
                                        "page": page_num,
                                        "text": text,
                                        "bbox": bbox,
                                        "font": span.get("font", ""),
                                        "size": span.get("size", 0)
                                    })
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
    
    def map_annotations(self, annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map Kindle annotations to PDF coordinates
        
        Args:
            annotations: List of Kindle annotations
            
        Returns:
            List of annotations with added coordinate information
        """
        if not self.doc:
            logger.error("PDF not opened for mapping")
            return annotations
        
        mapped_annotations = []
        
        for annotation in annotations:
            try:
                mapped_annotation = self._map_single_annotation(annotation)
                mapped_annotations.append(mapped_annotation)
            except Exception as e:
                logger.warning(f"Error mapping annotation: {e}")
                # Add original annotation without mapping
                mapped_annotations.append(annotation.copy())
        
        return mapped_annotations
    
    def _map_single_annotation(self, annotation: Dict[str, Any]) -> Dict[str, Any]:
        """Map a single annotation to PDF coordinates"""
        mapped = annotation.copy()
        
        content = annotation.get("content", "")
        location = annotation.get("location")
        page_num = annotation.get("page")
        
        # Try different mapping strategies
        coordinates = None
        estimated_page = None
        
        # Strategy 1: Direct text search
        if content:
            coordinates, page_found = self._find_text_coordinates(content)
            if coordinates:
                estimated_page = page_found
        
        # Strategy 2: Location-based estimation
        if not coordinates and location:
            estimated_page = self._estimate_page_from_location(location)
            if estimated_page is not None:
                coordinates = self._estimate_coordinates_on_page(estimated_page, content, location)
        
        # Strategy 3: Page number if available
        if not coordinates and page_num is not None:
            try:
                page_int = int(page_num)
                if 0 <= page_int < len(self.doc):
                    estimated_page = page_int
                    coordinates = self._estimate_coordinates_on_page(page_int, content, location)
            except (ValueError, TypeError):
                pass
        
        # Add mapping results
        if coordinates:
            mapped["coordinates"] = coordinates
            mapped["page_number"] = estimated_page
            mapped["mapping_method"] = "text_search" if content else "location_estimation"
        else:
            # Fallback to first page
            mapped["page_number"] = 0
            mapped["coordinates"] = [50, 50, 200, 100]  # Default rectangle
            mapped["mapping_method"] = "fallback"
        
        return mapped
    
    def _find_text_coordinates(self, text: str) -> Tuple[Optional[List[float]], Optional[int]]:
        """
        Find coordinates by searching for text content
        
        Args:
            text: Text to search for
            
        Returns:
            Tuple of (coordinates, page_number) or (None, None)
        """
        if not text or len(text) < 5:
            return None, None
        
        # Clean text for search
        search_text = self._clean_text_for_search(text)
        
        # Search in text blocks
        for block in self.text_blocks:
            block_text = self._clean_text_for_search(block["text"])
            
            if search_text in block_text or self._fuzzy_match(search_text, block_text):
                bbox = block["bbox"]
                return list(bbox), block["page"]
        
        # Try partial matches with first few words
        words = search_text.split()[:10]  # First 10 words
        for i in range(len(words), 2, -1):  # Try decreasing word counts
            partial_text = " ".join(words[:i])
            if len(partial_text) < 10:  # Skip very short phrases
                continue
                
            for block in self.text_blocks:
                block_text = self._clean_text_for_search(block["text"])
                if partial_text in block_text:
                    bbox = block["bbox"]
                    return list(bbox), block["page"]
        
        return None, None
    
    def _clean_text_for_search(self, text: str) -> str:
        """Clean text for better matching"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        # Remove common punctuation that might not match
        text = re.sub(r'[""''""``]', '"', text)
        text = re.sub(r'[–—]', '-', text)
        return text.strip().lower()
    
    def _fuzzy_match(self, search_text: str, block_text: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching based on word overlap"""
        if not search_text or not block_text:
            return False
        
        search_words = set(search_text.split())
        block_words = set(block_text.split())
        
        if not search_words:
            return False
        
        # Calculate overlap ratio
        overlap = len(search_words.intersection(block_words))
        ratio = overlap / len(search_words)
        
        return ratio >= threshold
    
    def _estimate_page_from_location(self, location: str) -> Optional[int]:
        """Estimate page number from Kindle location"""
        try:
            # Extract numeric location
            location_match = re.search(r'\d+', str(location))
            if not location_match:
                return None
            
            location_num = int(location_match.group())
            
            # Different estimation strategies based on book length
            total_pages = len(self.doc)
            
            if total_pages <= 1:
                return 0
            
            # Strategy 1: Linear estimation (rough approximation)
            # Assume locations are somewhat linear with pages
            estimated_page = min(int(location_num / 50), total_pages - 1)
            
            # Strategy 2: Consider typical Kindle locations per page (~10-20)
            alt_estimate = min(int(location_num / 15), total_pages - 1)
            
            # Use the more conservative estimate
            return min(estimated_page, alt_estimate)
            
        except Exception as e:
            logger.warning(f"Error estimating page from location {location}: {e}")
            return None
    
    def _estimate_coordinates_on_page(self, page_num: int, content: str, 
                                    location: str) -> Optional[List[float]]:
        """Estimate coordinates on a specific page"""
        if page_num < 0 or page_num >= len(self.doc):
            return None
        
        try:
            # Search for text on the specific page
            page = self.doc[page_num]
            
            if content:
                # Try to find the content on this page
                search_results = page.search_for(content[:100])  # First 100 chars
                if search_results:
                    rect = search_results[0]
                    return [rect.x0, rect.y0, rect.x1, rect.y1]
            
            # If no direct match, estimate based on page position
            page_rect = page.rect
            
            # Estimate vertical position based on location within page
            if location:
                location_match = re.search(r'\d+', str(location))
                if location_match:
                    location_num = int(location_match.group())
                    # Estimate position within page (very rough)
                    relative_pos = (location_num % 20) / 20.0  # 20 locations per page assumption
                    y_pos = page_rect.y0 + (page_rect.height * relative_pos)
                    
                    return [
                        page_rect.x0 + 50,  # Left margin
                        y_pos,
                        page_rect.x1 - 50,  # Right margin
                        y_pos + 20          # Small height
                    ]
            
            # Default position in middle of page
            return [
                page_rect.x0 + 50,
                page_rect.y0 + page_rect.height / 2,
                page_rect.x1 - 50,
                page_rect.y0 + page_rect.height / 2 + 20
            ]
            
        except Exception as e:
            logger.warning(f"Error estimating coordinates on page {page_num}: {e}")
            return None


def map_annotations_to_pdf(pdf_path: str, annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to map annotations to PDF coordinates
    
    Args:
        pdf_path: Path to PDF file
        annotations: List of Kindle annotations
        
    Returns:
        List of annotations with coordinate mapping
    """
    mapper = AnnotationMapper(pdf_path)
    
    try:
        if not mapper.open_pdf():
            return annotations
        
        return mapper.map_annotations(annotations)
        
    finally:
        mapper.close_pdf()


if __name__ == "__main__":
    # Test the mapper
    import sys
    import json
    
    if len(sys.argv) > 2:
        pdf_path = sys.argv[1]
        annotations_file = sys.argv[2]
        
        # Load annotations from JSON file
        with open(annotations_file, 'r') as f:
            annotations = json.load(f)
        
        mapped = map_annotations_to_pdf(pdf_path, annotations)
        print(json.dumps(mapped, indent=2, default=str))