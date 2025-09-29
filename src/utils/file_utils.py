"""
File Utilities - Common file handling functions
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import chardet

logger = logging.getLogger(__name__)


def find_kindle_files(kindle_folder: str, pdf_name: str) -> Dict[str, List[Path]]:
    """
    Find Kindle annotation files for a given PDF
    
    Args:
        kindle_folder: Path to Kindle documents folder
        pdf_name: Name of the PDF file (without extension)
        
    Returns:
        Dictionary with lists of found files by type
    """
    kindle_path = Path(kindle_folder)
    if not kindle_path.exists():
        logger.error(f"Kindle folder does not exist: {kindle_folder}")
        return {"pds": [], "pdt": [], "sdr": []}
    
    # Clean PDF name for searching
    clean_name = pdf_name.replace(' ', '_').replace('-', '_')
    
    # Search patterns
    patterns = [
        f"*{pdf_name}*",
        f"*{clean_name}*",
        f"*{pdf_name.replace('_', ' ')}*",
        f"*{pdf_name.replace(' ', '_')}*"
    ]
    
    found_files = {"pds": [], "pdt": [], "sdr": []}
    
    # Search for each pattern
    for pattern in patterns:
        # Find PDS files
        pds_files = list(kindle_path.glob(f"{pattern}.pds"))
        found_files["pds"].extend(pds_files)
        
        # Find PDT files
        pdt_files = list(kindle_path.glob(f"{pattern}.pdt"))
        found_files["pdt"].extend(pdt_files)
        
        # Find SDR folders (Sidecar Data Records)
        sdr_folders = list(kindle_path.glob(f"{pattern}.sdr"))
        found_files["sdr"].extend(sdr_folders)
    
    # Remove duplicates
    for file_type in found_files:
        found_files[file_type] = list(set(found_files[file_type]))
    
    logger.info(f"Found {len(found_files['pds'])} PDS, {len(found_files['pdt'])} PDT, "
                f"and {len(found_files['sdr'])} SDR files for '{pdf_name}'")
    
    return found_files


def detect_file_encoding(file_path: str) -> str:
    """
    Detect the encoding of a text file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Detected encoding name
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            logger.debug(f"Detected encoding for {file_path}: {encoding} (confidence: {confidence:.2f})")
            
            # Fallback to common encodings if confidence is low
            if confidence < 0.5:
                return 'utf-8'
            
            return encoding
    except Exception as e:
        logger.warning(f"Error detecting encoding for {file_path}: {e}")
        return 'utf-8'


def safe_read_text_file(file_path: str, encoding: Optional[str] = None) -> str:
    """
    Safely read a text file with encoding detection
    
    Args:
        file_path: Path to the file
        encoding: Specific encoding to use (optional)
        
    Returns:
        File contents as string
    """
    if not encoding:
        encoding = detect_file_encoding(file_path)
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # Try fallback encodings
        fallback_encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for fallback in fallback_encodings:
            if fallback != encoding:
                try:
                    with open(file_path, 'r', encoding=fallback) as f:
                        logger.warning(f"Used fallback encoding {fallback} for {file_path}")
                        return f.read()
                except UnicodeDecodeError:
                    continue
        
        # Last resort: ignore errors
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            logger.warning(f"Reading {file_path} with error handling")
            return f.read()


def create_backup(file_path: str, backup_suffix: str = ".backup") -> Optional[str]:
    """
    Create a backup of a file
    
    Args:
        file_path: Path to the original file
        backup_suffix: Suffix to add to backup filename
        
    Returns:
        Path to backup file or None if failed
    """
    try:
        original_path = Path(file_path)
        if not original_path.exists():
            return None
        
        backup_path = original_path.with_suffix(original_path.suffix + backup_suffix)
        shutil.copy2(file_path, str(backup_path))
        
        logger.info(f"Created backup: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Error creating backup for {file_path}: {e}")
        return None


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    path = Path(file_path)
    
    if not path.exists():
        return {"exists": False, "error": "File not found"}
    
    try:
        stat = path.stat()
        return {
            "exists": True,
            "name": path.name,
            "stem": path.stem,
            "suffix": path.suffix,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "absolute_path": str(path.absolute())
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}


def clean_filename(filename: str) -> str:
    """
    Clean a filename to make it safe for file system
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    cleaned = filename
    
    for char in invalid_chars:
        cleaned = cleaned.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip(' .')
    
    # Limit length
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    
    return cleaned


def find_myclippings_file(kindle_folder: str) -> Optional[str]:
    """
    Find the MyClippings.txt file in Kindle folder
    
    Args:
        kindle_folder: Path to Kindle documents folder
        
    Returns:
        Path to MyClippings.txt file or None if not found
    """
    kindle_path = Path(kindle_folder)
    if not kindle_path.exists():
        return None
    
    # Common locations and names for MyClippings.txt
    possible_locations = [
        kindle_path / "My Clippings.txt",
        kindle_path / "MyClippings.txt",
        kindle_path / "documents" / "My Clippings.txt",
        kindle_path / "documents" / "MyClippings.txt",
        kindle_path.parent / "My Clippings.txt",
        kindle_path.parent / "MyClippings.txt"
    ]
    
    for location in possible_locations:
        if location.exists() and location.is_file():
            logger.info(f"Found MyClippings.txt at: {location}")
            return str(location)
    
    logger.warning("MyClippings.txt not found in expected locations")
    return None


def list_pdf_files(directory: str) -> List[str]:
    """
    List all PDF files in a directory
    
    Args:
        directory: Directory path to search
        
    Returns:
        List of PDF file paths
    """
    try:
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        
        pdf_files = []
        for file_path in dir_path.glob("*.pdf"):
            if file_path.is_file():
                pdf_files.append(str(file_path))
        
        pdf_files.sort()  # Sort alphabetically
        return pdf_files
        
    except Exception as e:
        logger.error(f"Error listing PDF files in {directory}: {e}")
        return []


def copy_file_with_progress(src: str, dst: str, chunk_size: int = 64 * 1024) -> bool:
    """
    Copy a file with progress tracking capability
    
    Args:
        src: Source file path
        dst: Destination file path
        chunk_size: Size of chunks to copy at a time
        
    Returns:
        True if copy was successful
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            logger.error(f"Source file does not exist: {src}")
            return False
        
        # Ensure destination directory exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file in chunks
        with open(src_path, 'rb') as src_file, open(dst_path, 'wb') as dst_file:
            while True:
                chunk = src_file.read(chunk_size)
                if not chunk:
                    break
                dst_file.write(chunk)
        
        logger.info(f"Successfully copied {src} to {dst}")
        return True
        
    except Exception as e:
        logger.error(f"Error copying file from {src} to {dst}: {e}")
        return False


if __name__ == "__main__":
    # Test the utilities
    import tempfile
    
    # Test file operations
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Hello, world!")
        
        info = get_file_info(str(test_file))
        print(f"File info: {info}")
        
        backup = create_backup(str(test_file))
        print(f"Backup created: {backup}")
        
        content = safe_read_text_file(str(test_file))
        print(f"File content: {content}")