"""
KRDS Parser - Kindle Reader Data Store
Integrated from the original KRDS project by John Howell
https://github.com/K-R-D-S/KRDS
"""

import collections
import datetime
import json
import struct
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, BinaryIO, Union
import io

logger = logging.getLogger(__name__)


class KindlePosition:
    """Represents a Kindle position with page and coordinate information"""
    
    def __init__(self, position_string: str):
        self.raw = position_string
        self.parts = position_string.split() if position_string else []
        
        # Parse position string: "page seq char_pos ? x y width height"
        if len(self.parts) >= 8:
            try:
                self.page = int(self.parts[0])
                self.sequence = int(self.parts[1]) 
                self.char_pos = int(self.parts[2])
                self.unknown = int(self.parts[3])
                self.x = int(self.parts[4])
                self.y = int(self.parts[5])
                self.width = int(self.parts[6])
                self.height = int(self.parts[7])
                self.valid = True
            except (ValueError, IndexError):
                self.valid = False
                self._set_defaults()
        else:
            self.valid = False
            self._set_defaults()
    
    def _set_defaults(self):
        self.page = 0
        self.sequence = 0
        self.char_pos = 0
        self.unknown = 0
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
    
    def to_pdf_rect(self) -> List[float]:
        """Convert to PDF rectangle coordinates"""
        return [float(self.x), float(self.y), 
                float(self.x + self.width), float(self.y + self.height)]
    
    def __str__(self):
        return f"Page {self.page} at ({self.x}, {self.y})"


class KindleAnnotation:
    """Represents a parsed Kindle annotation"""
    
    def __init__(self, annotation_type: str, data: Dict[str, Any]):
        self.type = annotation_type
        self.start_position = KindlePosition(data.get("startPosition", ""))
        self.end_position = KindlePosition(data.get("endPosition", ""))
        self.creation_time = data.get("creationTime")
        self.last_modified = data.get("lastModificationTime")
        self.template = data.get("template")
        self.note_text = data.get("note", "")
        
        # Determine annotation category
        if "highlight" in annotation_type:
            self.category = "highlight"
        elif "note" in annotation_type:
            self.category = "note"
        elif "bookmark" in annotation_type:
            self.category = "bookmark"
        else:
            self.category = "other"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.type,
            "category": self.category,
            "page_number": self.start_position.page,
            "coordinates": self.start_position.to_pdf_rect(),
            "content": self.note_text,
            "creation_time": self.creation_time,
            "last_modified": self.last_modified,
            "start_position": self.start_position.raw,
            "end_position": self.end_position.raw,
            "valid_position": self.start_position.valid
        }


class KindleReaderDataStore:
    """Parser for Kindle Reader Data Store files (.pds, .pdt files)"""
    
    SIGNATURE = b"\x00\x00\x00\x00\x00\x1A\xB1\x26"
    
    # Data types from KRDS
    DATATYPE_BOOLEAN = 0
    DATATYPE_INT = 1
    DATATYPE_LONG = 2
    DATATYPE_UTF = 3
    DATATYPE_DOUBLE = 4
    DATATYPE_SHORT = 5
    DATATYPE_FLOAT = 6
    DATATYPE_BYTE = 7
    DATATYPE_CHAR = 9
    DATATYPE_OBJECT_BEGIN = -2
    DATATYPE_OBJECT_END = -1
    
    ANNOT_CLASS_NAMES = {
        0: "annotation.personal.bookmark",
        1: "annotation.personal.highlight", 
        2: "annotation.personal.note",
        3: "annotation.personal.clip_article",
        10: "annotation.personal.handwritten_note",
        11: "annotation.personal.sticky_note",
        13: "annotation.personal.underline",
    }
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = None
        self.krds = None
        
    def parse(self) -> Dict[str, Any]:
        """Parse the KRDS file and return structured data"""
        try:
            with open(self.file_path, 'rb') as f:
                self.data = f.read()
            
            return self._deserialize()
        except Exception as e:
            logger.error(f"Error parsing KRDS file {self.file_path}: {e}")
            return {"error": str(e), "annotations": []}
    
    def _deserialize(self) -> Dict[str, Any]:
        """Deserialize the binary data"""
        self.krds = Deserializer(self.data)
        
        # Check signature
        signature = self.krds.extract(len(self.SIGNATURE))
        if signature != self.SIGNATURE:
            raise Exception("Invalid KRDS signature")
        
        # Decode first value (should be 1)
        first_value = self._decode_next()
        if first_value != 1:
            raise Exception(f"Unexpected first value: {first_value}")
        
        # Decode value count and data
        value_count = self._decode_next()
        result = collections.OrderedDict()
        
        for _ in range(value_count):
            val = self._decode_next()
            if isinstance(val, dict):
                for k, v in val.items():
                    if k in result:
                        raise Exception(f"Duplicate key: {k}")
                    result[k] = v
        
        return dict(result)
    
    def _decode_next(self, datatype: Optional[int] = None) -> Any:
        """Decode the next value from the stream"""
        if datatype is None:
            datatype = self.krds.unpack("b")
        
        if datatype == self.DATATYPE_BOOLEAN:
            b = self.krds.unpack("b")
            return b == 1
        elif datatype == self.DATATYPE_INT:
            return self.krds.unpack(">l")
        elif datatype == self.DATATYPE_LONG:
            return self.krds.unpack(">q")
        elif datatype == self.DATATYPE_UTF:
            if self._decode_next(self.DATATYPE_BOOLEAN):
                return ""
            else:
                length = self.krds.unpack(">H")
                return self.krds.extract(length).decode("utf-8")
        elif datatype == self.DATATYPE_DOUBLE:
            return self.krds.unpack(">d")
        elif datatype == self.DATATYPE_SHORT:
            return self.krds.unpack(">h")
        elif datatype == self.DATATYPE_FLOAT:
            return self.krds.unpack(">f")
        elif datatype == self.DATATYPE_BYTE:
            return self.krds.unpack("b")
        elif datatype == self.DATATYPE_CHAR:
            return self.krds.unpack("c").decode("utf-8")
        elif datatype == self.DATATYPE_OBJECT_BEGIN:
            name = self._decode_next(self.DATATYPE_UTF)
            values = []
            
            while self.krds.unpack("b", advance=False) != self.DATATYPE_OBJECT_END:
                values.append(self._decode_next())
            
            self.krds.unpack("b")  # consume DATATYPE_OBJECT_END
            return self._decode_object(name, values)
        else:
            raise Exception(f"Unknown datatype: {datatype}")
    
    def _decode_object(self, name: str, values: List[Any]) -> Dict[str, Any]:
        """Decode object based on its name and values"""
        obj = collections.OrderedDict()
        
        if name == "annotation.cache.object":
            # This contains the annotations we want
            annotation_count = values.pop(0)
            for _ in range(annotation_count):
                annotation_type_id = values.pop(0)
                annotation_class = self.ANNOT_CLASS_NAMES.get(annotation_type_id)
                if annotation_class:
                    annotation_data = values.pop(0)
                    if "saved.avl.interval.tree" in annotation_data:
                        obj[annotation_class] = annotation_data["saved.avl.interval.tree"]
        
        elif name == "saved.avl.interval.tree":
            # Array of annotation objects
            count = values.pop(0)
            obj = []
            for _ in range(count):
                annotation_obj = values.pop(0)
                # The annotation_obj is a dict with annotation type as key
                # We need to unwrap it to get the actual annotation data
                for annotation_type, annotation_data in annotation_obj.items():
                    if annotation_type in self.ANNOT_CLASS_NAMES.values():
                        obj.append(annotation_data)
                    else:
                        obj.append(annotation_obj)
        
        elif name in self.ANNOT_CLASS_NAMES.values():
            # Individual annotation
            obj["startPosition"] = values.pop(0)
            obj["endPosition"] = values.pop(0)
            obj["creationTime"] = datetime.datetime.fromtimestamp(values.pop(0) / 1000.0).isoformat()
            obj["lastModificationTime"] = datetime.datetime.fromtimestamp(values.pop(0) / 1000.0).isoformat()
            obj["template"] = values.pop(0)
            
            # Add note text if it's a note annotation
            if name == "annotation.personal.note" and values:
                obj["note"] = values.pop(0)
        
        else:
            # For other objects, just store the values
            obj = values.pop(0) if len(values) == 1 else values
        
        return {name: obj}
    
    def extract_annotations(self) -> List[KindleAnnotation]:
        """Extract annotations from the parsed data"""
        parsed_data = self.parse()
        annotations = []
        
        if "error" in parsed_data:
            logger.error(f"Error in parsed data: {parsed_data['error']}")
            return annotations
        
        # Look for annotation cache object
        annotation_cache = parsed_data.get("annotation.cache.object", {})
        
        for annotation_type, annotation_list in annotation_cache.items():
            if annotation_type in self.ANNOT_CLASS_NAMES.values():
                for annotation_data in annotation_list:
                    try:
                        annotation = KindleAnnotation(annotation_type, annotation_data)
                        annotations.append(annotation)
                    except Exception as e:
                        logger.warning(f"Error parsing annotation: {e}")
        
        # Sort by page number and position
        annotations.sort(key=lambda a: (a.start_position.page, a.start_position.y, a.start_position.x))
        
        logger.info(f"Extracted {len(annotations)} annotations from {self.file_path}")
        return annotations


class Deserializer:
    """Helper class for deserializing binary data"""
    
    def __init__(self, data: bytes):
        self.buffer = data
        self.offset = 0
    
    def unpack(self, fmt: str, advance: bool = True) -> Any:
        """Unpack data using struct format"""
        result = struct.unpack_from(fmt, self.buffer, self.offset)[0]
        if advance:
            self.offset += struct.calcsize(fmt)
        return result
    
    def extract(self, size: int, advance: bool = True) -> bytes:
        """Extract bytes from buffer"""
        if size < 0 or self.offset + size > len(self.buffer):
            raise Exception(f"Cannot extract {size} bytes at offset {self.offset}")
        
        data = self.buffer[self.offset:self.offset + size]
        if advance:
            self.offset += size
        return data
    
    def __len__(self):
        return len(self.buffer) - self.offset


def parse_krds_file(file_path: str) -> List[KindleAnnotation]:
    """
    Parse a KRDS file and return annotations
    
    Args:
        file_path: Path to .pds or .pdt file
        
    Returns:
        List of KindleAnnotation objects
    """
    parser = KindleReaderDataStore(file_path)
    return parser.extract_annotations()


def find_krds_files(kindle_folder: str, pdf_name: str) -> List[Path]:
    """
    Find KRDS files (.pds, .pdt) for a given PDF
    
    Args:
        kindle_folder: Path to Kindle documents folder
        pdf_name: PDF filename without extension
        
    Returns:
        List of KRDS file paths
    """
    kindle_path = Path(kindle_folder)
    krds_files = []
    
    # Look for files matching the PDF name
    patterns = [
        f"*{pdf_name}*.pds",
        f"*{pdf_name}*.pdt",
    ]
    
    for pattern in patterns:
        krds_files.extend(kindle_path.glob(pattern))
    
    # Also look in .sdr subdirectories
    sdr_folders = list(kindle_path.glob(f"*{pdf_name}*.sdr"))
    for sdr_folder in sdr_folders:
        krds_files.extend(sdr_folder.glob("*.pds"))
        krds_files.extend(sdr_folder.glob("*.pdt"))
    
    return krds_files


if __name__ == "__main__":
    # Test the parser
    import sys
    
    if len(sys.argv) > 1:
        annotations = parse_krds_file(sys.argv[1])
        print(f"Found {len(annotations)} annotations:")
        for annotation in annotations:
            print(f"  {annotation.category} on page {annotation.start_position.page}: {annotation.note_text}")