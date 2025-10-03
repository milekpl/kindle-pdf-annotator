#!/usr/bin/env python3
"""
Kindle PDF Annotator - Command Line Interface
Uses the Amazon coordinate system for accurate annotation placement
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import the working Amazon coordinate system
from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from src.pdf_processor.pdf_annotator import annotate_pdf_file


def main():
    """Command line interface main function"""
    parser = argparse.ArgumentParser(description="Kindle PDF Annotator CLI")
    parser.add_argument("--kindle-folder", required=True, help="Path to Kindle documents folder (.sdr folder)")
    parser.add_argument("--pdf-file", required=True, help="Path to PDF file") 
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--clippings", help="Path to MyClippings.txt file (optional)")
    parser.add_argument("--export-json", help="Export annotations to JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not Path(args.kindle_folder).exists():
        print(f"Error: Kindle folder does not exist: {args.kindle_folder}")
        sys.exit(1)
    
    if not Path(args.pdf_file).exists():
        print(f"Error: PDF file does not exist: {args.pdf_file}")
        sys.exit(1)
    
    # Extract PDF name for searching
    pdf_name = Path(args.pdf_file).stem
    print(f"Processing annotations for: {pdf_name}")
    
    # Find KRDS file (.pds or .pdt)
    kindle_folder_path = Path(args.kindle_folder)
    krds_files = list(kindle_folder_path.glob("*.pds")) + list(kindle_folder_path.glob("*.pdt"))
    
    # Also check .sdr subdirectories
    for sdr_dir in kindle_folder_path.glob("*.sdr"):
        if sdr_dir.is_dir():
            krds_files.extend(sdr_dir.glob("*.pds"))
            krds_files.extend(sdr_dir.glob("*.pdt"))
    
    if not krds_files:
        print(f"Error: No KRDS files (.pds or .pdt) found in {args.kindle_folder}")
        print("Expected format: <book-name>.pdf-cdeKey_<key>.sdr/ or .pds/.pdt files in folder")
        sys.exit(1)
    
    print(f"Found {len(krds_files)} KRDS files:")
    for i, krds_file in enumerate(krds_files, 1):
        print(f"  {i}. {krds_file}")
    
    # Find the KRDS file that matches the PDF filename
    pdf_path = Path(args.pdf_file)
    pdf_name = pdf_path.stem
    
    # Look for KRDS files that match the PDF name
    matching_krds = []
    for krds_file in krds_files:
        krds_path = Path(krds_file)
        # Check if the KRDS file name or its parent directory contains the PDF name
        if pdf_name in krds_path.name or pdf_name in krds_path.parent.name:
            matching_krds.append(krds_file)
    
    if matching_krds:
        krds_file = str(matching_krds[0])
        print(f"Found matching KRDS file for PDF: {Path(krds_file).name}")
    else:
        # Fallback to first file if no match found
        krds_file = str(krds_files[0])
        print(f"No specific match found, using first KRDS file: {Path(krds_file).name}")
        print(f"Warning: This KRDS file may not be for the specified PDF!")
    
    # Set up MyClippings file path
    clippings_file = args.clippings
    if not clippings_file:
        # Try default location
        default_clippings = str(Path.home() / "Documents" / "My Clippings.txt")
        if Path(default_clippings).exists():
            clippings_file = default_clippings
        else:
            clippings_file = ""  # No clippings file available
    
    if clippings_file and not Path(clippings_file).exists():
        print(f"Warning: MyClippings.txt not found at {clippings_file}")
        clippings_file = ""
    
    # Use Amazon coordinate system to get annotations
    print("Processing annotations with Amazon coordinate system...")
    try:
        # Extract book name from KRDS file path for matching with MyClippings
        book_name = pdf_name  # Start with PDF name
        # Try to extract from path if it follows Kindle format
        if "cdeKey_" in krds_file:
            parts = Path(krds_file).parent.name.split("-cdeKey_")
            if parts:
                book_name = parts[0]
        
        # If no clippings file, create a temporary empty one
        if not clippings_file:
            temp_clippings = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_clippings.write("")  # Empty file
            temp_clippings.close()
            clippings_file = temp_clippings.name
            print("No MyClippings.txt provided - processing annotations from JSON only")
            temp_file_created = True
        else:
            temp_file_created = False
        
        amazon_annotations = create_amazon_compliant_annotations(krds_file, clippings_file, book_name)
        print(f"Found {len(amazon_annotations)} annotations using Amazon coordinate system")
        
        # Clean up temp file if created
        if temp_file_created:
            Path(clippings_file).unlink(missing_ok=True)
        
        if args.verbose:
            # Show page distribution
            pages = [ann.get('pdf_page_0based', 0) for ann in amazon_annotations]
            unique_pages = sorted(set(pages))
            print(f"Page distribution: {unique_pages}")
            
            # Count types
            highlights = [ann for ann in amazon_annotations if ann.get('type') == 'highlight']
            notes = [ann for ann in amazon_annotations if ann.get('type') == 'note']
            print(f"  Highlights: {len(highlights)}")
            print(f"  Notes: {len(notes)}")
        
    except Exception as e:
        print(f"Error processing annotations: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    if not amazon_annotations:
        print("No annotations found. Exiting.")
        sys.exit(0)
    
    # Export annotations if requested
    if args.export_json:
        try:
            with open(args.export_json, 'w', encoding='utf-8') as f:
                json.dump(amazon_annotations, f, indent=2, default=str)
            print(f"Annotations exported to: {args.export_json}")
        except Exception as e:
            print(f"Error exporting annotations: {e}")
    
    # Convert to PDF annotator format
    print("Converting to PDF annotator format...")
    try:
        pdf_annotations = convert_amazon_to_pdf_annotator_format(amazon_annotations)
        print(f"Converted {len(pdf_annotations)} annotations for PDF creation")
    except Exception as e:
        print(f"Error converting annotations: {e}")
        sys.exit(1)
    
    # Create annotated PDF
    print(f"Creating annotated PDF: {args.output}")
    try:
        success = annotate_pdf_file(args.pdf_file, pdf_annotations, args.output)
        if success:
            print(f"✅ Success! Annotated PDF saved to: {args.output}")
            
            # Show summary
            if pdf_annotations:
                highlight_count = len([a for a in pdf_annotations if a.get('type') == 'highlight'])
                note_count = len([a for a in pdf_annotations if a.get('type') == 'note'])
                print(f"   📊 Added {highlight_count} highlights and {note_count} notes")
        else:
            print("❌ Failed to create annotated PDF")
            sys.exit(1)
    except Exception as e:
        print(f"Error creating annotated PDF: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()