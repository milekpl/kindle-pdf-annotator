"""
KRDS Parser - Kindle Reader Data Store
Integrated and refactored from the original KRDS project by John Howell
https://github.com/K-R-D-S/KRDS

Directly parses .pds and .pdt files without requiring JSON intermediaries.
"""

import collections
import datetime
import struct
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class KindlePosition:
    """Represents a Kindle position with page and coordinate information"""

    def __init__(self, position_string: str):
        self.raw = position_string
        self.parts = position_string.split() if position_string else []

        # Parse position string - handle both full and short formats
        # Full format: "page seq char_pos ? x y width height" (8 parts for highlights/notes)
        # Short format: "page ? ? ?" (4 parts for bookmarks)
        if len(self.parts) >= 8:
            # Full position with coordinates
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
        elif len(self.parts) >= 4:
            # Short position (typically bookmarks) - page info only
            try:
                self.page = int(self.parts[0])
                self.sequence = int(self.parts[1]) if len(self.parts) > 1 else 0
                self.char_pos = int(self.parts[2]) if len(self.parts) > 2 else 0
                self.unknown = int(self.parts[3]) if len(self.parts) > 3 else 0
                # No coordinate info for bookmarks
                self.x = 0
                self.y = 0
                self.width = 0
                self.height = 0
                # Mark as valid if we have page info
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
        """Convert to PDF rectangle coordinates [x0, y0, x1, y1]"""
        if not self.valid:
            return [0.0, 0.0, 0.0, 0.0]
        return [float(self.x), float(self.y), float(self.x + self.width), float(self.y + self.height)]


class KindleAnnotation:
    """Represents a Kindle annotation (highlight, note, bookmark)"""

    def __init__(self, annotation_type: str, start_pos: Union[KindlePosition, str, Dict[str, Any]], end_pos: Optional[Union[KindlePosition, str]] = None):
        self.annotation_type = annotation_type
        
        # Handle different input formats
        if isinstance(start_pos, dict):
            # Dictionary format from tests
            data = start_pos
            self.start_position = KindlePosition(data.get("startPosition", ""))
            self.end_position = KindlePosition(data.get("endPosition", data.get("startPosition", "")))
            self.creation_time = data.get("creationTime")
            self.last_modification_time = data.get("lastModificationTime")
            self.template = data.get("template")
            self.note_text = data.get("note", "")
            self.content = ""
        else:
            # Original format
            self.start_position = start_pos if isinstance(start_pos, KindlePosition) else KindlePosition(start_pos)
            self.end_position = end_pos if isinstance(end_pos, KindlePosition) else (KindlePosition(end_pos) if end_pos else self.start_position)
            self.creation_time = None
            self.last_modification_time = None
            self.template = None
            self.note_text = ""
            self.content = ""

    @property
    def type(self):
        """Get annotation type"""
        return self.annotation_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "type": self.annotation_type,
            "page_number": self.start_position.page,
            "category": self.category,
            "coordinates": self.start_position.to_pdf_rect(),
            "valid_position": self.start_position.valid,
            "start_position": str(self.start_position),
            "end_position": str(self.end_position),
            "creation_time": self.creation_time,
            "last_modification_time": self.last_modification_time,
            "template": self.template,
            "note_text": self.note_text,
            "content": self.content
        }

    @property
    def category(self):
        """Get human-readable category"""
        categories = {
            "annotation.personal.highlight": "highlight",
            "annotation.personal.note": "note",
            "annotation.personal.bookmark": "bookmark",
            "annotation.personal.underline": "underline"
        }
        return categories.get(self.annotation_type, self.annotation_type)

    def __str__(self):
        return f"{self.category} on page {self.start_position.page}"


class Deserializer:
    """Binary deserializer for KRDS data"""

    def __init__(self, data: bytes):
        self.buffer = data
        self.offset = 0

    def unpack(self, fmt: str, advance: bool = True) -> Any:
        result = struct.unpack_from(fmt, self.buffer, self.offset)[0]
        if advance:
            self.offset += struct.calcsize(fmt)
        return result

    def extract(self, size: Optional[int] = None, upto: Optional[int] = None, advance: bool = True) -> bytes:
        if size is None:
            size = len(self) if upto is None else (upto - self.offset)
        data = self.buffer[self.offset:self.offset + size]

        if len(data) < size or size < 0:
            raise Exception(f"Deserializer: Insufficient data (need {size} bytes, have {len(data)} bytes)")
        if advance:
            self.offset += size

        return data

    def __len__(self) -> int:
        return len(self.buffer) - self.offset


class KindleReaderDataStore:
    """
    Complete KRDS parser integrated from John Howell's KRDS project
    Parses .pds and .pdt files directly without JSON intermediaries
    """

    SIGNATURE = b"\x00\x00\x00\x00\x00\x1A\xB1\x26"

    # Data types
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

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.data = None
        self.krds = None
        self.log = logger

    def parse(self) -> Dict[str, Any]:
        """Parse the KRDS file and return structured data"""
        try:
            with open(self.file_path, 'rb') as f:
                self.data = f.read()

            return self.deserialize()
        except Exception as e:
            logger.error(f"Error parsing KRDS file {self.file_path}: {e}")
            return {"error": str(e), "annotations": []}

    def deserialize(self) -> Dict[str, Any]:
        """Complete deserialization of KRDS binary data"""
        assert self.data is not None, "Data must be loaded before deserialization"
        self.krds = Deserializer(self.data)

        signature = self.krds.extract(len(self.SIGNATURE))
        if signature != self.SIGNATURE:
            raise Exception("KindleReaderDataStore signature is incorrect")

        first_value = self.decode_next()
        if first_value != 1:
            raise Exception(f"first_value = {repr(first_value)}")

        value_cnt = self.decode_next()
        value = collections.OrderedDict()

        for _ in range(value_cnt):
            try:
                val = self.decode_next()
            except Exception:
                self.log.info(f"KindleReaderDataStore decode failed at offset {len(self.data) - len(self.krds)}")
                self.log.info(f"partial value = {repr(value)}")
                raise

            # Handle different value types
            if isinstance(val, dict):
                for k, v in val.items():
                    # Allow overwrites for duplicate keys (keep the last one)
                    value[k] = v
            elif isinstance(val, (str, int, float, bool)):
                # Skip non-dict values that don't fit the expected format
                self.log.debug(f"Skipping non-dict value: {repr(val)}")
                continue
            else:
                # Try to handle other types gracefully
                self.log.debug(f"Skipping unexpected value type {type(val)}: {repr(val)}")
                continue

        if len(self.krds) != 0:
            self.log.error(f"KindleReaderDataStore has {len(self.krds)} bytes of extra data")

        return dict(value)

    def decode_next(self, datatype: Optional[int] = None) -> Any:
        """Decode the next value from the binary stream"""
        if datatype is None:
            datatype = self.krds.unpack("b")

        if datatype == self.DATATYPE_BOOLEAN:
            b = self.krds.unpack("b")
            if b == 0:
                value = False
            elif b == 1:
                value = True
            else:
                raise Exception(f"Unknown boolean value {b}")

        elif datatype == self.DATATYPE_INT:
            value = self.krds.unpack(">l")

        elif datatype == self.DATATYPE_LONG:
            value = self.krds.unpack(">q")

        elif datatype == self.DATATYPE_UTF:
            if self.decode_next(self.DATATYPE_BOOLEAN):
                value = ""
            else:
                value = self.krds.extract(self.krds.unpack(">H")).decode("utf-8")

        elif datatype == self.DATATYPE_DOUBLE:
            value = self.krds.unpack(">d")

        elif datatype == self.DATATYPE_SHORT:
            value = self.krds.unpack(">h")

        elif datatype == self.DATATYPE_FLOAT:
            value = self.krds.unpack(">f")

        elif datatype == self.DATATYPE_BYTE:
            value = self.krds.unpack("b")

        elif datatype == self.DATATYPE_CHAR:
            value = self.krds.unpack("c").decode("utf-8")

        elif datatype == self.DATATYPE_OBJECT_BEGIN:
            name = self.decode_next(self.DATATYPE_UTF)
            val = []

            while self.krds.unpack("b", advance=False) != self.DATATYPE_OBJECT_END:
                val.append(self.decode_next())

            self.krds.unpack("b")  # consume DATATYPE_OBJECT_END
            value = self.decode_object(name, val)

        else:
            raise Exception(f"Unknown datatype {datatype}")

        return value

    def decode_object(self, name: str, val: List) -> Any:
        """Decode object based on its type"""
        # Handle malformed data where val is not a list
        if not isinstance(val, list):
            return val  # Return as-is for non-list values

        obj = collections.OrderedDict()

        # Handle different object types
        if name in {
            "clock.data.store", "dictionary", "lpu", "pdf.contrast",
            "sync_lpr", "tpz.line.spacing", "XRAY_OTA_UPDATE_STATE",
            "XRAY_SHOWING_SPOILERS", "XRAY_SORTING_STATE", "XRAY_TAB_STATE"
        }:
            obj = val.pop(0)  # single value

        elif name in {"dict.prefs.v2", "EndActions", "ReaderMetrics",
                      "StartActions", "Translator", "Wikipedia"}:
            for _ in range(val.pop(0)):  # key/value pairs
                k = val.pop(0)
                obj[k] = val.pop(0)

        elif name in {"buy.asin.response.data", "next.in.series.info.data", "price.info.data"}:
            obj = val.pop(0)  # single value json

        elif name == "erl":
            obj = self.decode_position(val.pop(0))

        elif name in {"lpr"}:
            version = val.pop(0)
            if isinstance(version, str):
                obj["position"] = self.decode_position(version)  # old-style lpr
            elif version <= 2:
                obj["position"] = self.decode_position(val.pop(0))
                time = val.pop(0)
                obj["time"] = datetime.datetime.fromtimestamp(time / 1000.0).isoformat() if time != -1 else None
            else:
                raise Exception(f"Unknown lpr version {version}")

        elif name in {"fpr", "updated_lpr"}:
            obj["position"] = self.decode_position(val.pop(0))
            time = val.pop(0)
            obj["time"] = datetime.datetime.fromtimestamp(time / 1000.0).isoformat() if time != -1 else None
            timezone = val.pop(0)
            obj["timeZoneOffset"] = timezone if timezone != -1 else None
            obj["country"] = val.pop(0)
            obj["device"] = val.pop(0)

        elif name == "annotation.cache.object":
            try:
                count = val.pop(0)
                if not isinstance(count, int):
                    raise ValueError(f"Expected integer count, got {type(count)}")
                for _ in range(count):
                    if not val:
                        break
                    annotation_type = val.pop(0)
                    annot_class_name = self.ANNOT_CLASS_NAMES.get(annotation_type)
                    if annot_class_name is None:
                        continue  # Skip unknown annotation types
                    if not val:
                        break
                    annotations_data = val.pop(0)
                    
                    annotations = []
                    if isinstance(annotations_data, dict) and "saved.avl.interval.tree" in annotations_data:
                        # Original expected format
                        for annotation in annotations_data["saved.avl.interval.tree"]:
                            if isinstance(annotation, dict) and len(annotation) == 1 and annot_class_name in annotation:
                                annotations.append(annotation[annot_class_name])
                    elif isinstance(annotations_data, list):
                        # annotations_data is directly the list from saved.avl.interval.tree
                        for annotation in annotations_data:
                            if isinstance(annotation, dict) and 'startPosition' in annotation:
                                annotations.append(annotation)
                    
                    if annotations:
                        obj[annot_class_name] = annotations
            except (IndexError, ValueError, TypeError, KeyError):
                # Skip malformed annotation.cache.object
                pass

        elif name == "saved.avl.interval.tree":
            obj = [val.pop(0) for _ in range(val.pop(0))]  # annotation.personal.xxx

        elif name == "font.prefs":
            # Handle font preferences - just store the values
            obj = val[0] if val else None

        elif name == "language.store":
            # Handle language store - just store the values
            obj = val[0] if val else None

        elif name in self.ANNOT_CLASS_NAMES.values():
            obj["startPosition"] = self.decode_position(val.pop(0))
            obj["endPosition"] = self.decode_position(val.pop(0))
            obj["creationTime"] = datetime.datetime.fromtimestamp(val.pop(0) / 1000.0).isoformat()
            obj["lastModificationTime"] = datetime.datetime.fromtimestamp(val.pop(0) / 1000.0).isoformat()
            obj["template"] = val.pop(0)

            if name == "annotation.personal.note":
                obj["note"] = val.pop(0)
            elif name == "annotation.personal.handwritten_note":
                obj["handwritten_note_nbk_ref"] = val.pop(0)
            elif name == "annotation.personal.sticky_note":
                obj["sticky_note_nbk_ref"] = val.pop(0)

        # Add more object type handlers as needed...
        else:
            # For unhandled object types, store the raw values
            obj["_raw_values"] = val
            obj["_unhandled_type"] = name

        return obj

    @staticmethod
    def decode_position(position: str) -> str:
        """Decode position string (currently just returns as-is)"""
        return position

    def extract_annotations(self) -> List[KindleAnnotation]:
        """Extract annotations from parsed KRDS data"""
        parsed_data = self.parse()
        annotations = []

        # Check for annotations in annotation.cache.object (original format)
        cache = parsed_data.get("annotation.cache.object", {})
        annotation_sources = [cache]
        
        # Also check for annotation types directly in parsed_data (new merged format)
        for key, value in parsed_data.items():
            if key.startswith("annotation.personal.") and isinstance(value, list):
                # This is a merged annotation type
                annotation_sources.append({key: value})

        for source in annotation_sources:
            for annot_type, annot_list in source.items():
                for annot_data in annot_list:
                    try:
                        start_pos = KindlePosition(annot_data.get("startPosition", ""))
                        end_pos = KindlePosition(annot_data.get("endPosition", ""))

                        annotation = KindleAnnotation(annot_type, start_pos, end_pos)
                        annotation.creation_time = annot_data.get("creationTime")
                        annotation.last_modification_time = annot_data.get("lastModificationTime")
                        annotation.template = annot_data.get("template")
                        annotation.note_text = annot_data.get("note", "")

                        annotations.append(annotation)
                    except Exception as e:
                        logger.warning(f"Failed to parse annotation: {e}")

        return annotations


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
            print(f"  {annotation.category} on page {annotation.start_position.page}")