"""
MyClippings.txt Parser - Kindle Clippings File
This module handles parsing of the MyClippings.txt file that contains
user highlights, notes, and bookmarks from Kindle devices.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ClippingsParser:
    """Parser for Kindle MyClippings.txt file"""
    
    # Regex patterns for parsing clippings
    SEPARATOR = "=========="
    TITLE_AUTHOR_PATTERN = r"^(.+?)\s*\(([^)]+)\)$"
    LOCATION_PATTERN = r"- Your (\w+) on (Location|Page) (\d+(?:-\d+)?)(?: \| Added on (.+))?"
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.clippings = []
        
    def parse(self) -> Dict[str, Any]:
        """
        Parse the MyClippings.txt file
        
        Returns:
            Dict containing parsed clippings data
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                return self._parse_content(content)
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(self.file_path, 'r', encoding='latin-1') as file:
                    content = file.read()
                    return self._parse_content(content)
            except Exception as e:
                logger.error(f"Error reading file with latin-1 encoding: {e}")
                return {"error": str(e), "clippings": []}
        except Exception as e:
            logger.error(f"Error parsing MyClippings.txt file {self.file_path}: {e}")
            return {"error": str(e), "clippings": []}
    
    def _parse_content(self, content: str) -> Dict[str, Any]:
        """
        Parse the content of MyClippings.txt
        
        Args:
            content: File content as string
            
        Returns:
            Parsed data dictionary
        """
        # Split content by separator
        raw_clippings = content.split(self.SEPARATOR)
        
        parsed_clippings = []
        for raw_clipping in raw_clippings:
            clipping = self._parse_clipping(raw_clipping.strip())
            if clipping:
                parsed_clippings.append(clipping)
        
        # Group clippings by book
        books = self._group_by_book(parsed_clippings)
        
        return {
            "total_clippings": len(parsed_clippings),
            "total_books": len(books),
            "clippings": parsed_clippings,
            "books": books,
            "source_file": str(self.file_path)
        }
    
    def _parse_clipping(self, raw_clipping: str) -> Dict[str, Any]:
        """
        Parse a single clipping entry
        
        Args:
            raw_clipping: Raw clipping text
            
        Returns:
            Parsed clipping dictionary or None if invalid
        """
        if not raw_clipping:
            return None
        
        lines = raw_clipping.split('\n')
        if len(lines) < 2:  # Need at least title and metadata
            return None
        
        # Parse title and author
        title_line = lines[0].strip()
        title, author = self._parse_title_author(title_line)
        
        # Parse location and metadata
        meta_line = lines[1].strip()
        location_info = self._parse_location_info(meta_line)
        
        # Extract content (may be empty for bookmarks)
        content_lines = lines[2:] if len(lines) > 2 else []
        content = '\n'.join(line.strip() for line in content_lines).strip()
        
        clipping = {
            "title": title,
            "author": author,
            "type": location_info.get("type", "unknown"),
            "location": location_info.get("location"),
            "page": location_info.get("page"),
            "date_added": location_info.get("date_added"),
            "content": content,
            "raw_location_info": meta_line
        }
        
        return clipping
    
    def _parse_title_author(self, title_line: str) -> tuple[str, str]:
        """Parse title and author from the first line"""
        match = re.match(self.TITLE_AUTHOR_PATTERN, title_line)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        else:
            # If no parentheses found, treat entire line as title
            return title_line, ""
    
    def _parse_location_info(self, meta_line: str) -> Dict[str, Any]:
        """Parse location and metadata information"""
        match = re.search(self.LOCATION_PATTERN, meta_line)
        if not match:
            return {"raw": meta_line}
        
        clipping_type = match.group(1).lower()  # Highlight, Note, Bookmark
        location_type = match.group(2).lower()  # Location or Page
        location_value = match.group(3)
        date_str = match.group(4)
        
        result = {
            "type": clipping_type,
            "location_type": location_type,
            "raw": meta_line
        }
        
        # Parse location/page
        if location_type == "location":
            result["location"] = location_value
        else:
            result["page"] = location_value
        
        # Parse date
        if date_str:
            try:
                # Common Kindle date formats
                date_formats = [
                    "%A, %B %d, %Y %I:%M:%S %p",
                    "%A, %B %d, %Y at %I:%M:%S %p",
                    "%B %d, %Y %I:%M:%S %p",
                    "%m/%d/%Y %I:%M:%S %p",
                    "%Y-%m-%d %H:%M:%S"
                ]
                
                parsed_date = None
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str.strip(), date_format)
                        break
                    except ValueError:
                        continue
                
                if parsed_date:
                    result["date_added"] = parsed_date.isoformat()
                else:
                    result["date_added_raw"] = date_str
                    
            except Exception as e:
                logger.warning(f"Could not parse date '{date_str}': {e}")
                result["date_added_raw"] = date_str
        
        return result
    
    def _group_by_book(self, clippings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Group clippings by book title"""
        books = {}
        
        for clipping in clippings:
            title = clipping.get("title", "Unknown Title")
            if title not in books:
                books[title] = {
                    "title": title,
                    "author": clipping.get("author", ""),
                    "clippings": []
                }
            
            books[title]["clippings"].append(clipping)
        
        # Sort clippings within each book by location
        for book_data in books.values():
            book_data["clippings"].sort(key=lambda x: self._get_sort_key(x))
        
        return books
    
    def _get_sort_key(self, clipping: Dict[str, Any]) -> tuple:
        """Generate sort key for clipping ordering"""
        # Sort by location or page number
        location = clipping.get("location", "0")
        page = clipping.get("page", "0")
        
        # Extract numeric part for sorting
        def extract_number(value):
            if isinstance(value, str):
                match = re.search(r'\d+', value)
                return int(match.group()) if match else 0
            return value or 0
        
        location_num = extract_number(location)
        page_num = extract_number(page)
        
        return (location_num, page_num)


def parse_clippings_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse MyClippings.txt file
    
    Args:
        file_path: Path to the MyClippings.txt file
        
    Returns:
        Parsed clippings data
    """
    parser = ClippingsParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    # Test the parser
    import sys
    import json
    
    if len(sys.argv) > 1:
        result = parse_clippings_file(sys.argv[1])
        print(json.dumps(result, indent=2, default=str))