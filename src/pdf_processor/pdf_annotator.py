"""
PDF Annotator - Embed annotations into PDF files
This module uses PyMuPDF (fitz) to embed Kindle annotations into PDF files.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import re

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
        # Extract annotation data
        content = annotation.get("content", "")
        location = annotation.get("location")
        page_num = annotation.get("page_number")
        coordinates = annotation.get("coordinates")
        annotation_type = annotation.get("type", "highlight").lower()
        
        # Skip empty annotations, but NOT for highlights (they don't need content)
        if not content and annotation_type != "highlight":
            return False
        
        # Determine page number
        if page_num is None and location:
            page_num = self._estimate_page_from_location(location)
        
        if page_num is None or page_num < 0 or page_num >= len(self.doc):
            logger.warning(f"Invalid page number: {page_num}")
            return False
        
        # Get the page
        page = self.doc[page_num]
        
        # Determine annotation position
        if coordinates:
            rect = fitz.Rect(coordinates)
        else:
            rect = self._find_text_position(page, content)
        
        if not rect:
            # Default position if text not found
            rect = fitz.Rect(50, 50, 200, 100)
        
        # Create annotation based on type
        if annotation_type == "highlight":
            return self._add_highlight_annotation(page, rect, content, annotation)
        elif annotation_type == "note":
            return self._add_note_annotation(page, rect, content, annotation)
        else:
            return self._add_text_annotation(page, rect, content, annotation)
    
    def _add_highlight_annotation(self, page, rect: fitz.Rect, content: str, 
                                annotation: Dict[str, Any]) -> bool:
        """Add a highlight annotation"""
        try:
            # Create highlight annotation
            highlight = page.add_highlight_annot(rect)
            highlight.set_info(title="Kindle Highlight", content=content)
            highlight.set_colors(stroke=[1, 1, 0])  # Yellow highlight
            highlight.update()
            return True
        except Exception as e:
            logger.error(f"Error adding highlight: {e}")
            return False
    
    def _add_note_annotation(self, page, rect: fitz.Rect, content: str,
                           annotation: Dict[str, Any]) -> bool:
        """Add a note annotation"""
        try:
            # Create text annotation (note)
            note = page.add_text_annot(rect.top_left, content)
            note.set_info(title="Kindle Note", content=content)
            note.update()
            return True
        except Exception as e:
            logger.error(f"Error adding note: {e}")
            return False
    
    def _add_text_annotation(self, page, rect: fitz.Rect, content: str,
                           annotation: Dict[str, Any]) -> bool:
        """Add a generic text annotation"""
        try:
            # Create free text annotation
            text_annot = page.add_freetext_annot(rect, content)
            text_annot.set_info(title="Kindle Annotation", content=content)
            text_annot.update()
            return True
        except Exception as e:
            logger.error(f"Error adding text annotation: {e}")
            return False
    
    def _find_text_position(self, page, text: str) -> Optional[fitz.Rect]:
        """
        Find the position of text on the page
        
        Args:
            page: PDF page object
            text: Text to search for
            
        Returns:
            Rectangle coordinates if found, None otherwise
        """
        try:
            # Search for text on the page
            text_instances = page.search_for(text[:50])  # Search first 50 chars
            if text_instances:
                return text_instances[0]  # Return first match
            
            # If exact match not found, try partial matches
            words = text.split()[:5]  # Try first 5 words
            for word in words:
                if len(word) > 3:  # Only search meaningful words
                    instances = page.search_for(word)
                    if instances:
                        return instances[0]
            
            return None
        except Exception as e:
            logger.warning(f"Error searching for text: {e}")
            return None
    
    def _estimate_page_from_location(self, location: str) -> Optional[int]:
        """
        Estimate PDF page number from Kindle location
        
        Args:
            location: Kindle location string
            
        Returns:
            Estimated page number or None
        """
        try:
            # Extract numeric part from location
            location_match = re.search(r'\d+', str(location))
            if not location_match:
                return None
            
            location_num = int(location_match.group())
            
            # Simple heuristic: assume ~250 words per page, ~10 locations per page
            # This is very approximate and may need adjustment
            estimated_page = max(0, (location_num // 10) - 1)
            
            # Ensure page exists in document
            if estimated_page >= len(self.doc):
                estimated_page = len(self.doc) - 1
            
            return estimated_page
        except Exception as e:
            logger.warning(f"Error estimating page from location {location}: {e}")
            return None
    
    def save_pdf(self, output_path: str) -> bool:
        """
        Save the annotated PDF
        
        Args:
            output_path: Path to save the annotated PDF
            
        Returns:
            True if successful, False otherwise
        """
        if not self.doc:
            logger.error("No PDF document to save")
            return False
        
        try:
            self.doc.save(output_path)
            logger.info(f"Annotated PDF saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving PDF to {output_path}: {e}")
            return False
    
    def get_pdf_info(self) -> Dict[str, Any]:
        """Get basic information about the PDF"""
        if not self.doc:
            return {}
        
        return {
            "page_count": len(self.doc),
            "title": self.doc.metadata.get("title", ""),
            "author": self.doc.metadata.get("author", ""),
            "subject": self.doc.metadata.get("subject", ""),
            "keywords": self.doc.metadata.get("keywords", ""),
            "file_path": str(self.pdf_path)
        }


def annotate_pdf_file(pdf_path: str, annotations: List[Dict[str, Any]], 
                     output_path: str) -> bool:
    """
    Convenience function to annotate a PDF file
    
    Args:
        pdf_path: Path to the source PDF
        annotations: List of annotations to add
        output_path: Path to save the annotated PDF
        
    Returns:
        True if successful, False otherwise
    """
    annotator = PDFAnnotator(pdf_path)
    
    try:
        if not annotator.open_pdf():
            return False
        
        added_count = annotator.add_annotations(annotations)
        logger.info(f"Added {added_count} annotations to PDF")
        
        success = annotator.save_pdf(output_path)
        return success
        
    finally:
        annotator.close_pdf()


if __name__ == "__main__":
    # Test the annotator
    import sys
    import json
    
    if len(sys.argv) > 3:
        pdf_path = sys.argv[1]
        annotations_file = sys.argv[2]
        output_path = sys.argv[3]
        
        # Load annotations from JSON file
        with open(annotations_file, 'r') as f:
            annotations = json.load(f)
        
        success = annotate_pdf_file(pdf_path, annotations, output_path)
        print(f"Annotation {'successful' if success else 'failed'}")