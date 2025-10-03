"""
Fixed MyClippings Parser - Handles case-insensitive parsing and correct page extraction
"""

import re
import json
from typing import List, Dict, Any


def parse_myclippings_for_book(clippings_file: str, book_name: str) -> List[Dict[str, Any]]:
    """
    Parse MyClippings.txt and extract entries for a specific book
    FIXED: Handles case-insensitive 'page' and extracts first page from ranges
    
    Note: Kindle strips the book name at the first '.pdf' in the filename.
    So '659ec7697e419.pdf-cdeKey_ABC.pdf' becomes '659ec7697e419' in clippings.
    """
    with open(clippings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    entries = content.split('==========')
    book_entries = []
    
    # Normalize book name: strip at first .pdf if present
    # This matches how Kindle stores book names in MyClippings.txt
    normalized_book_name = book_name.split('.pdf')[0] if '.pdf' in book_name else book_name
    
    print(f"🔍 Parsing MyClippings for book: {book_name}")
    if normalized_book_name != book_name:
        print(f"   Normalized to: {normalized_book_name}")
    print(f"📄 Total raw entries in file: {len(entries)}")
    
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
            
        lines = entry.split('\n')
        if len(lines) < 2:
            continue
            
        title_line = lines[0].strip()
        
        # Check if this entry is for our book using normalized name
        if normalized_book_name.lower() in title_line.lower():
            meta_line = lines[1].strip()
            
            # FIXED: Case-insensitive regex pattern
            page_match = re.search(r'page\s+(\d+(?:-\d+)?)', meta_line, re.IGNORECASE)
            if not page_match:
                print(f"⚠️  No page match in: {meta_line}")
                continue
            
            page_str = page_match.group(1)
            
            # FIXED: Extract first page number from ranges like '5-5' or '12-15'
            if '-' in page_str:
                pdf_page = int(page_str.split('-')[0])
            else:
                pdf_page = int(page_str)
            
            # Extract timestamp
            date_match = re.search(r'Added on (.+)$', meta_line)
            timestamp = date_match.group(1) if date_match else ""
            
            # Extract type (case-insensitive)
            entry_type = "note" if re.search(r'note', meta_line, re.IGNORECASE) else "highlight"
            
            # Extract content (rest of lines)
            content_text = '\n'.join(lines[2:]).strip() if len(lines) > 2 else ""
            
            book_entries.append({
                'type': entry_type,
                'pdf_page': pdf_page,  # This is the 1-based page from MyClippings
                'content': content_text,
                'timestamp': timestamp,
                'raw_meta': meta_line,
                'page_str': page_str  # Keep original for debugging
            })
            
            print(f"✅ Parsed: page {pdf_page} ({page_str}) - {entry_type}: {content_text[:30]}...")
    
    print(f"📊 Found {len(book_entries)} entries for {book_name}")
    return book_entries


def test_fixed_parser():
    """Test the fixed parser"""
    clippings_file = 'examples/sample_data/My Clippings.txt'
    book_name = 'rorot-thesis-20250807'
    
    entries = parse_myclippings_for_book(clippings_file, book_name)
    
    # Analyze page distribution
    pages = [entry['pdf_page'] for entry in entries]
    unique_pages = sorted(set(pages))
    
    print(f"\n📈 PAGE ANALYSIS:")
    print(f"   Unique pages: {unique_pages}")
    print(f"   Page range: {min(unique_pages)} to {max(unique_pages)}")
    print(f"   Total annotations: {len(entries)}")
    
    # Check for page 0 annotations (should be none!)
    page_0_count = pages.count(0)
    page_1_count = pages.count(1)
    print(f"   Page 0 annotations: {page_0_count}")
    print(f"   Page 1 annotations: {page_1_count}")
    
    if page_0_count > 0:
        print("ℹ️  INFO: Found page 0 annotations (valid for title/cover pages)")
    else:
        print("ℹ️  INFO: No page 0 annotations found")
        
    return entries


if __name__ == "__main__":
    test_fixed_parser()