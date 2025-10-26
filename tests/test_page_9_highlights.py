#!/usr/bin/env python3
"""
Unit test for highlights on page 9 - focus on "allows" word
"""

import sys
import fitz
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from src.kindle_parser.krds_parser import KindleAnnotation, KindlePosition

# Import from src subdirectory
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from pdf_processor.pdf_annotator import annotate_pdf_file


def load_mock_krds_from_json(json_path: str):
    """
    Load mock KRDS annotations from JSON file.
    This converts the JSON format to KindleAnnotation objects as if they came from a PDS file.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    annotations = []
    cache = data.get("annotation.cache.object", {})
    
    # Process highlights
    for annot_data in cache.get("annotation.personal.highlight", []):
        try:
            start_pos = KindlePosition(annot_data.get("startPosition", ""))
            end_pos = KindlePosition(annot_data.get("endPosition", ""))
            
            annotation = KindleAnnotation("annotation.personal.highlight", start_pos, end_pos)
            annotation.creation_time = annot_data.get("creationTime")
            annotation.last_modification_time = annot_data.get("lastModificationTime")
            annotation.template = annot_data.get("template")
            annotation.note_text = annot_data.get("text", "")
            
            annotations.append(annotation)
        except Exception as e:
            print(f"Warning: Failed to parse highlight: {e}")
    
    # Process notes
    for annot_data in cache.get("annotation.personal.note", []):
        try:
            start_pos = KindlePosition(annot_data.get("startPosition", ""))
            end_pos = KindlePosition(annot_data.get("endPosition", annot_data.get("startPosition", "")))
            
            annotation = KindleAnnotation("annotation.personal.note", start_pos, end_pos)
            annotation.creation_time = annot_data.get("creationTime")
            annotation.note_text = annot_data.get("text", "")
            
            annotations.append(annotation)
        except Exception as e:
            print(f"Warning: Failed to parse note: {e}")
    
    return annotations

def test_page_9_highlights():
    """Test highlights specifically on page 9 with focus on 'allows' word"""
    
    print("🧪 TESTING PAGE 9 HIGHLIGHTS - FOCUS ON 'ALLOWS'")
    
    # Test files
    json_file = 'tests/page_9_test_annotations.json'
    clippings_file = 'tests/page_9_test_clippings.txt'
    pdf_file = 'tests/page_9_test.pdf'
    output_file = 'tests/page_9_annotated.pdf'
    book_name = 'rorot-thesis-20250807'
    
    print(f"   Input PDF: {pdf_file}")
    print(f"   Output PDF: {output_file}")
    print("   Mode: Mock KRDS from JSON + MyClippings text matching")
    
    try:
        # Load mock annotations from JSON
        mock_annotations = load_mock_krds_from_json(json_file)
        print(f"\n   Loaded {len(mock_annotations)} mock annotations from JSON")
        
        # Mock the KindleReaderDataStore to return our JSON-based annotations
        with patch('src.kindle_parser.krds_parser.KindleReaderDataStore') as mock_krds:
            # Create a mock parser instance
            mock_parser = MagicMock()
            mock_parser.extract_annotations.return_value = mock_annotations
            mock_krds.return_value = mock_parser
            
            # Step 1: Get Amazon annotations
            print("\n1. Getting Amazon annotations...")
            amazon_annotations = create_amazon_compliant_annotations(json_file, clippings_file, book_name)
            
            highlights = [ann for ann in amazon_annotations if ann.get('type') == 'highlight']
            notes = [ann for ann in amazon_annotations if ann.get('type') == 'note']
            
            print(f"   📊 Total: {len(amazon_annotations)} ({len(highlights)} highlights, {len(notes)} notes)")
            
            # Debug highlights specifically
            print("\n🔍 HIGHLIGHT ANALYSIS:")
            for i, highlight in enumerate(highlights):
                content = highlight.get('content', '')
                coords = highlight.get('coordinates', [])
                page = highlight.get('pdf_page_0based', '?')
                print(f"   {i+1}. Content: '{content}'")
                print(f"      Page: {page}, Coordinates: {coords}")
                if len(coords) >= 2:
                    inches_x = coords[0] / 72
                    inches_y = coords[1] / 72
                    print(f"      Position: ({inches_x:.2f}\", {inches_y:.2f}\")")
                print()
            
            # Step 2: Convert to PDF annotator format
            print("2. Converting to PDF annotator format...")
            pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
            
            highlight_annotations = [ann for ann in pdf_annotations if ann.get('type') == 'highlight']
            note_annotations = [ann for ann in pdf_annotations if ann.get('type') == 'note']
            
            print(f"   📋 PDF format: {len(pdf_annotations)} ({len(highlight_annotations)} highlights, {len(note_annotations)} notes)")
            
            # Debug PDF annotations
            print("\n🔍 PDF ANNOTATION FORMAT:")
            for i, ann in enumerate(pdf_annotations):
                ann_type = ann.get('type', '?')
                content = ann.get('content', '')
                coords = ann.get('coordinates', [])
                page = ann.get('page_number', '?')
                print(f"   {i+1}. {ann_type.upper()}: '{content[:30]}...'")
                print(f"      Page: {page}, Coordinates: {coords}")
                print()
            
            # Step 3: Create annotated PDF
            print("3. Creating annotated PDF...")
            success = annotate_pdf_file(pdf_file, pdf_annotations, output_file)
            
            if success:
                print("\n✅ SUCCESS: Test PDF created!")
                print(f"   File: {output_file}")
                
                # Verify annotations in the output
                print("\n🔍 VERIFYING OUTPUT PDF:")
                doc = fitz.open(output_file)
                
                total_annotations = 0
                highlight_count = 0
                note_count = 0
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    annots = list(page.annots())
                    
                    if annots:
                        total_annotations += len(annots)
                        print(f"   Page {page_num + 1}: {len(annots)} annotations")
                        
                        for i, annot in enumerate(annots):
                            rect = annot.rect
                            annot_type = annot.type[1]
                            
                            if annot_type == "Highlight":
                                highlight_count += 1
                                print(f"      {i+1}. HIGHLIGHT at ({rect.x0:.1f}, {rect.y0:.1f}) - ({rect.x1:.1f}, {rect.y1:.1f})")
                            elif annot_type in ["Text", "FreeText"]:
                                note_count += 1
                                print(f"      {i+1}. NOTE at ({rect.x0:.1f}, {rect.y0:.1f})")
                
                print("\n📊 FINAL RESULT:")
                print(f"   Total annotations: {total_annotations}")
                print(f"   Highlights: {highlight_count}")
                print(f"   Notes: {note_count}")
                
                if highlight_count > 0:
                    print(f"   ✅ SUCCESS: {highlight_count} highlights created!")
                    print(f"   🎯 Check if 'allows' text is highlighted in {output_file}")
                else:
                    print("   ❌ PROBLEM: No highlights created!")
                    print("   🔧 Need to fix highlight creation logic")
                    raise AssertionError("No highlights were created in the output PDF")
                
                doc.close()
                
            else:
                print("\n❌ ERROR: Failed to create test PDF")
                raise AssertionError("Failed to create annotated PDF")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_page_9_highlights()