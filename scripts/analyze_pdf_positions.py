#!/usr/bin/env python3
"""
Analyze actual text positions in the PDF to understand correct coordinate mapping
"""

import sys
import fitz
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

def analyze_pdf_text_positions():
    """Analyze where the expected text actually appears in the PDF"""
    
    print("🔍 ANALYZING ACTUAL TEXT POSITIONS IN PDF")
    
    # Open the original PDF
    doc = fitz.open('examples/sample_data/peirce-charles-fixation-belief.pdf')
    
    # Expected highlights from clippings
    expected_highlights = [
        {"page": 1, "text": "The Fixation of Belief"},
        {"page": 1, "text": "Few persons care to study logic, because everybody conceives himself to be profcient"},
        {"page": 2, "text": "The object of reasoning is to fnd out, from the consideration of what we already know, something else which we do not know.Consequently, reasoning is good if it be such as to give a true conclusion from true premises, and not otherwise"},
        {"page": 3, "text": "reasoning"},
        {"page": 4, "text": "We generally know when we wish to ask a question and when we wish to pronounce a judgment, for there is a dissimilarity between the sensation of doubting and that of believing. But"},
        {"page": 4, "text": "The Assassins, or followers of the Old Man of the Mountain"},
        {"page": 4, "text": "insure everlasting felicity"},
        {"page": 6, "text": "Oh, I could not believe so-and-so, because I should be wretched if I did."}
    ]
    
    for highlight in expected_highlights:
        page_num = highlight["page"] - 1  # Convert to 0-based
        expected_text = highlight["text"]
        
        if page_num >= len(doc):
            print(f"⚠️  Page {highlight['page']} not found in PDF")
            continue
            
        page = doc.load_page(page_num)
        
        print(f"\n📄 Page {highlight['page']} - Searching for: \"{expected_text[:50]}{'...' if len(expected_text) > 50 else ''}\"")
        
        # Get all text with coordinates
        text_dict = page.get_text("dict")
        
        # Search for the text in the page
        found = False
        search_terms = [expected_text]
        
        # Also try variations for OCR differences
        if "fnd" in expected_text:
            search_terms.append(expected_text.replace("fnd", "find"))
        if "profcient" in expected_text:
            search_terms.append(expected_text.replace("profcient", "proficient"))
        
        for search_text in search_terms:
            # Try to find the text using PyMuPDF's search
            text_instances = page.search_for(search_text[:30])  # Search for first 30 chars
            
            if text_instances:
                found = True
                for i, rect in enumerate(text_instances):
                    actual_text = page.get_textbox(rect)
                    print(f"  ✅ Found instance {i+1}:")
                    print(f"     Rectangle: {rect}")
                    print(f"     Width: {rect.width:.1f}pt, Height: {rect.height:.1f}pt")
                    print(f"     Text: \"{actual_text[:80]}{'...' if len(actual_text) > 80 else ''}\"")
                break
        
        if not found:
            # Try word-by-word search for the first few words
            words = expected_text.split()[:3]  # First 3 words
            search_phrase = " ".join(words)
            text_instances = page.search_for(search_phrase)
            
            if text_instances:
                print(f"  🔍 Found partial match for \"{search_phrase}\":")
                for i, rect in enumerate(text_instances):
                    actual_text = page.get_textbox(rect)
                    print(f"     Rectangle: {rect}")
                    print(f"     Width: {rect.width:.1f}pt, Height: {rect.height:.1f}pt")
                    print(f"     Text: \"{actual_text[:80]}{'...' if len(actual_text) > 80 else ''}\"")
            else:
                print(f"  ❌ Text not found on page {highlight['page']}")
                
                # Show some text from the page for debugging
                all_text = page.get_text()
                print(f"     Sample text from page: \"{all_text[:200]}...\"")
    
    doc.close()

if __name__ == "__main__":
    analyze_pdf_text_positions()