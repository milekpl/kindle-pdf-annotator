"""
PDT File Parser - Kindle Personal Document Text
This module handles parsing of .pdt files which contain the actual text
and annotation data for Kindle documents.
"""

import json
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO
import logging

logger = logging.getLogger(__name__)


class PDTParser:
    """Parser for Kindle .pdt (Personal Document Text) files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.text_content = ""
        self.annotations = []
        
    def parse(self) -> Dict[str, Any]:
        """
        Parse the PDT file and extract text content and annotations
        
        Returns:
            Dict containing parsed data
        """
        try:
            with open(self.file_path, 'rb') as file:
                return self._parse_binary_data(file)
        except Exception as e:
            logger.error(f"Error parsing PDT file {self.file_path}: {e}")
            return {"error": str(e), "text_content": "", "annotations": []}
    
    def _parse_binary_data(self, file: BinaryIO) -> Dict[str, Any]:
        """
        Parse binary PDT data
        
        Args:
            file: Binary file object to read from
            
        Returns:
            Parsed data dictionary
        """
        # Read file header
        header = file.read(16)
        if len(header) < 16:
            raise ValueError("Invalid PDT file: header too short")
        
        # Parse header information
        magic_number = struct.unpack('>I', header[:4])[0]
        version = struct.unpack('>H', header[4:6])[0]
        text_offset = struct.unpack('>I', header[8:12])[0]
        
        logger.debug(f"PDT Magic: {magic_number:08x}, Version: {version}, Text Offset: {text_offset}")
        
        result = {
            "metadata": {
                "magic_number": magic_number,
                "version": version,
                "text_offset": text_offset,
                "file_path": str(self.file_path)
            },
            "text_content": "",
            "annotations": []
        }
        
        # Extract text content
        try:
            result["text_content"] = self._extract_text(file, text_offset)
        except Exception as e:
            logger.warning(f"Error extracting text: {e}")
            result["metadata"]["text_warning"] = str(e)
        
        # Parse annotations
        try:
            self._parse_annotations(file, result)
        except Exception as e:
            logger.warning(f"Error parsing annotations: {e}")
            result["metadata"]["annotation_warning"] = str(e)
        
        return result
    
    def _extract_text(self, file: BinaryIO, text_offset: int) -> str:
        """Extract the main text content from the PDT file"""
        file.seek(text_offset)
        
        # Read text length
        length_data = file.read(4)
        if len(length_data) < 4:
            raise ValueError("Cannot read text length")
        
        text_length = struct.unpack('>I', length_data)[0]
        
        # Read text content
        text_data = file.read(text_length)
        if len(text_data) < text_length:
            raise ValueError("Cannot read full text content")
        
        # Decode text (try UTF-8 first, then fallback)
        try:
            return text_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return text_data.decode('latin-1')
            except UnicodeDecodeError:
                return text_data.decode('utf-8', errors='ignore')
    
    def _parse_annotations(self, file: BinaryIO, result: Dict[str, Any]):
        """Parse annotation data from the PDT file"""
        # Seek to potential annotation section (after text)
        current_pos = file.tell()
        
        # Try to find annotation markers
        annotation_count = 0
        while True:
            try:
                # Look for annotation headers
                chunk = file.read(1024)
                if not chunk:
                    break
                
                # Simple heuristic: look for text that might be annotations
                text_chunk = chunk.decode('utf-8', errors='ignore')
                
                # Look for patterns that might indicate annotations
                if self._looks_like_annotation(text_chunk):
                    annotation = {
                        "type": "pdt_annotation",
                        "content": text_chunk.strip(),
                        "position": current_pos,
                        "source": "pdt_file"
                    }
                    result["annotations"].append(annotation)
                    annotation_count += 1
                
                current_pos = file.tell()
                
                # Limit to prevent infinite loops
                if annotation_count > 1000:
                    break
                    
            except Exception as e:
                logger.debug(f"Error reading annotation chunk: {e}")
                break
    
    def _looks_like_annotation(self, text: str) -> bool:
        """Simple heuristic to identify potential annotation text"""
        if not text or len(text.strip()) < 10:
            return False
        
        # Look for common annotation patterns
        annotation_indicators = [
            "highlight", "note", "bookmark", "annotation",
            "location", "page", "kindle"
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in annotation_indicators)


def parse_pdt_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a PDT file
    
    Args:
        file_path: Path to the .pdt file
        
    Returns:
        Parsed data dictionary
    """
    parser = PDTParser(file_path)
    return parser.parse()


if __name__ == "__main__":
    # Test the parser
    import sys
    if len(sys.argv) > 1:
        result = parse_pdt_file(sys.argv[1])
        print(json.dumps(result, indent=2, default=str))