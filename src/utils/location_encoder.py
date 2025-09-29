"""
Location Encoder - Handle Kindle location encoding
This module provides utilities for understanding and converting
Kindle's location encoding system.
"""

import re
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class KindleLocationEncoder:
    """Handle Kindle location encoding and conversion"""
    
    def __init__(self):
        # Typical ranges for different types of content
        self.WORDS_PER_LOCATION = 150  # Approximate words per Kindle location
        self.LOCATIONS_PER_PAGE = 10   # Approximate locations per traditional page
        
    def decode_location(self, location_str: str) -> Dict[str, Any]:
        """
        Decode a Kindle location string into components
        
        Args:
            location_str: Location string (e.g., "1234-1235", "567")
            
        Returns:
            Dictionary with decoded location information
        """
        if not location_str:
            return {"error": "Empty location string"}
        
        try:
            # Clean the location string
            clean_location = str(location_str).strip()
            
            # Handle range locations (e.g., "1234-1235")
            if '-' in clean_location:
                parts = clean_location.split('-')
                if len(parts) == 2:
                    try:
                        start_loc = int(parts[0])
                        end_loc = int(parts[1])
                        return {
                            "type": "range",
                            "start_location": start_loc,
                            "end_location": end_loc,
                            "span": end_loc - start_loc + 1,
                            "estimated_words": (end_loc - start_loc + 1) * self.WORDS_PER_LOCATION,
                            "estimated_page": self._location_to_page(start_loc)
                        }
                    except ValueError:
                        return {"error": f"Invalid range format: {clean_location}"}
            
            # Handle single location
            try:
                location_num = int(clean_location)
                return {
                    "type": "single",
                    "location": location_num,
                    "estimated_words": self.WORDS_PER_LOCATION,
                    "estimated_page": self._location_to_page(location_num)
                }
            except ValueError:
                # Try to extract number from mixed string
                match = re.search(r'\d+', clean_location)
                if match:
                    location_num = int(match.group())
                    return {
                        "type": "extracted",
                        "location": location_num,
                        "original": clean_location,
                        "estimated_page": self._location_to_page(location_num)
                    }
                
                return {"error": f"Cannot parse location: {clean_location}"}
                
        except Exception as e:
            logger.warning(f"Error decoding location '{location_str}': {e}")
            return {"error": str(e)}
    
    def _location_to_page(self, location: int) -> int:
        """
        Estimate traditional page number from Kindle location
        
        Args:
            location: Kindle location number
            
        Returns:
            Estimated page number (1-based)
        """
        # Simple linear estimation
        estimated_page = max(1, location // self.LOCATIONS_PER_PAGE)
        return estimated_page
    
    def location_to_percentage(self, location: int, total_locations: Optional[int] = None) -> Optional[float]:
        """
        Convert location to percentage through book
        
        Args:
            location: Current location
            total_locations: Total locations in book (if known)
            
        Returns:
            Percentage (0.0 to 1.0) or None if cannot calculate
        """
        if total_locations and total_locations > 0:
            return min(1.0, max(0.0, location / total_locations))
        return None
    
    def estimate_reading_position(self, location: int, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Estimate reading position based on location
        
        Args:
            location: Kindle location
            context: Additional context (book length, etc.)
            
        Returns:
            Dictionary with position estimates
        """
        result = {
            "location": location,
            "estimated_page": self._location_to_page(location),
            "estimated_word_position": location * self.WORDS_PER_LOCATION
        }
        
        if context:
            total_locations = context.get("total_locations")
            if total_locations:
                result["percentage"] = self.location_to_percentage(location, total_locations)
                result["pages_remaining"] = max(0, (total_locations - location) // self.LOCATIONS_PER_PAGE)
        
        return result
    
    def compare_locations(self, loc1: str, loc2: str) -> Dict[str, Any]:
        """
        Compare two Kindle locations
        
        Args:
            loc1: First location
            loc2: Second location
            
        Returns:
            Comparison result dictionary
        """
        decoded1 = self.decode_location(loc1)
        decoded2 = self.decode_location(loc2)
        
        if "error" in decoded1 or "error" in decoded2:
            return {"error": "Cannot compare invalid locations"}
        
        # Get numeric values for comparison
        def get_location_value(decoded):
            if decoded["type"] == "range":
                return decoded["start_location"]
            elif decoded["type"] in ["single", "extracted"]:
                return decoded["location"]
            return 0
        
        val1 = get_location_value(decoded1)
        val2 = get_location_value(decoded2)
        
        return {
            "location1": decoded1,
            "location2": decoded2,
            "difference": abs(val2 - val1),
            "first_is_earlier": val1 < val2,
            "distance_in_pages": abs(val2 - val1) // self.LOCATIONS_PER_PAGE
        }
    
    def normalize_location_format(self, location_str: str) -> str:
        """
        Normalize location string to a standard format
        
        Args:
            location_str: Raw location string
            
        Returns:
            Normalized location string
        """
        decoded = self.decode_location(location_str)
        
        if "error" in decoded:
            return str(location_str)  # Return original if cannot decode
        
        if decoded["type"] == "range":
            return f"{decoded['start_location']}-{decoded['end_location']}"
        elif decoded["type"] in ["single", "extracted"]:
            return str(decoded["location"])
        
        return str(location_str)


class PageLocationMapper:
    """Map between PDF pages and Kindle locations"""
    
    def __init__(self, pdf_page_count: int, estimated_total_locations: Optional[int] = None):
        self.pdf_page_count = pdf_page_count
        self.estimated_total_locations = estimated_total_locations or (pdf_page_count * 10)
        self.encoder = KindleLocationEncoder()
        
    def kindle_location_to_pdf_page(self, location: str) -> Tuple[int, float]:
        """
        Map Kindle location to PDF page number
        
        Args:
            location: Kindle location string
            
        Returns:
            Tuple of (page_number, confidence_score)
        """
        decoded = self.encoder.decode_location(location)
        
        if "error" in decoded:
            return 0, 0.0  # Default to first page with low confidence
        
        # Get location number
        if decoded["type"] == "range":
            loc_num = decoded["start_location"]
        elif decoded["type"] in ["single", "extracted"]:
            loc_num = decoded["location"]
        else:
            return 0, 0.0
        
        # Calculate PDF page (0-based)
        percentage = loc_num / self.estimated_total_locations
        pdf_page = int(percentage * self.pdf_page_count)
        pdf_page = max(0, min(pdf_page, self.pdf_page_count - 1))
        
        # Confidence based on how well we can estimate
        confidence = 0.7 if self.estimated_total_locations else 0.3
        
        return pdf_page, confidence
    
    def pdf_page_to_kindle_location(self, page_number: int) -> Tuple[int, float]:
        """
        Estimate Kindle location from PDF page number
        
        Args:
            page_number: PDF page number (0-based)
            
        Returns:
            Tuple of (estimated_location, confidence_score)
        """
        if page_number < 0 or page_number >= self.pdf_page_count:
            return 0, 0.0
        
        # Estimate location based on page position
        percentage = page_number / self.pdf_page_count
        estimated_location = int(percentage * self.estimated_total_locations)
        
        confidence = 0.6  # Medium confidence for reverse mapping
        
        return estimated_location, confidence


# Convenience functions
def decode_kindle_location(location_str: str) -> Dict[str, Any]:
    """Convenience function to decode a Kindle location"""
    encoder = KindleLocationEncoder()
    return encoder.decode_location(location_str)


def create_location_mapper(pdf_page_count: int, total_locations: Optional[int] = None) -> PageLocationMapper:
    """Create a page-location mapper for a specific book"""
    return PageLocationMapper(pdf_page_count, total_locations)


if __name__ == "__main__":
    # Test the encoder
    import json
    
    encoder = KindleLocationEncoder()
    
    test_locations = ["1234", "567-890", "Location 1500", "invalid", ""]
    
    for loc in test_locations:
        result = encoder.decode_location(loc)
        print(f"Location '{loc}': {json.dumps(result, indent=2)}")
    
    # Test mapper
    mapper = PageLocationMapper(300, 3000)  # 300-page PDF, ~3000 locations
    
    test_kindle_locs = ["150", "1500", "2999"]
    for loc in test_kindle_locs:
        page, conf = mapper.kindle_location_to_pdf_page(loc)
        print(f"Kindle location {loc} -> PDF page {page} (confidence: {conf:.2f})")