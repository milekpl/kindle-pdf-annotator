#!/usr/bin/env python3
"""
Process Multiple Files in Learning Directory

This script processes multiple PDFs that have accompanying KRDS files and 
uses My Clippings.txt to extract highlights. It identifies PDFs that have 
accompanying KRDS files and processes them in learning mode to gather 
unmatched clippings data for analysis.
"""

import json
import subprocess
import sys
from pathlib import Path as PathLib
from typing import List, Dict, Any


def find_matching_files(learn_dir: str) -> List[Dict[str, str]]:
    """
    Find all PDF files with matching KRDS files in the learning directory.
    
    Args:
        learn_dir: Path to the learning directory
        
    Returns:
        List of dictionaries with PDF, KRDS, and MyClippings paths
    """
    learn_path = PathLib(learn_dir)
    
    if not learn_path.exists():
        print(f"Error: Learning directory does not exist: {learn_dir}")
        return []
    
    matches = []
    
    # Find all PDF files first, excluding those starting with "._"
    all_pdf_files = list(learn_path.glob("*.pdf"))
    pdf_files = [f for f in all_pdf_files if not f.name.startswith("._")]
    
    for pdf_file in pdf_files:
        print(f"Checking PDF: {pdf_file.name}")
        
        # Look for KRDS files that might match this PDF
        pdf_stem = pdf_file.stem  # Name without extension
        
        # Look for KRDS files in the same directory or .sdr subdirectories
        krds_files = []
        krds_files.extend(learn_path.glob(f"{pdf_stem}*.pds"))  # Files with same stem
        krds_files.extend(learn_path.glob(f"{pdf_stem}*.pdt"))
        
        # Look in .sdr subdirectories
        for sdr_dir in learn_path.glob("*.sdr"):
            if sdr_dir.is_dir():
                krds_files.extend(sdr_dir.glob(f"{pdf_stem}*.pds"))
                krds_files.extend(sdr_dir.glob(f"{pdf_stem}*.pdt"))
        
        if krds_files:
            print(f"  Found {len(krds_files)} KRDS files for {pdf_file.name}")
            
            # Find MyClippings.txt file
            clippings_file = None
            # First, try the default location
            default_clippings = PathLib.home() / "Documents" / "My Clippings.txt"
            if default_clippings.exists():
                clippings_file = str(default_clippings)
            else:
                # Try to find in the learning directory or its parent
                possible_clippings = list(learn_path.parent.glob("**/My Clippings.txt"))
                if possible_clippings:
                    clippings_file = str(possible_clippings[0])
            
            matches.append({
                'pdf_file': str(pdf_file),
                'krds_file': str(krds_files[0]),  # Use the first matching KRDS file
                'clippings_file': clippings_file,
                'book_name': pdf_stem
            })
        else:
            print(f"  No matching KRDS files found for {pdf_file.name}")
    
    return matches


def process_book_learning(pdf_path: str, krds_path: str, clippings_path: str, book_name: str, output_dir: str) -> str:
    """
    Process a single book in learning mode and return the path to the learning data.
    
    Args:
        pdf_path: Path to the PDF file
        krds_path: Path to the KRDS file
        clippings_path: Path to the MyClippings.txt file
        book_name: Name of the book
        output_dir: Directory to save the learning output
        
    Returns:
        Path to the generated learning data file
    """
    output_path = PathLib(output_dir) / f"{book_name}_learning_data.json"
    
    print(f"  Processing: {book_name}")
    print(f"    PDF: {pdf_path}")
    print(f"    KRDS: {krds_path}")
    print(f"    Clippings: {clippings_path or 'None'}")
    print(f"    Output: {output_path}")
    
    # Build the CLI command
    cmd = [
        sys.executable, str(PathLib(__file__).parent.parent / "cli.py"),
        "--kindle-folder", str(PathLib(krds_path).parent),
        "--pdf-file", pdf_path,
        "--output", str(PathLib(output_dir) / f"{book_name}_annotated.pdf"),  # Use temporary output
        "--learn",
        "--learn-output", str(output_path)
    ]
    
    if clippings_path:
        cmd.extend(["--clippings", clippings_path])
    
    # Run the command
    try:
        print(f"    Running learning mode...")
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"    Command output: {result.stdout[:200]}...")  # Print first 200 chars
        if result.stderr:  # Print stderr if present
            print(f"    Command errors: {result.stderr}")
        
        # Check if the output file was created
        if PathLib(output_path).exists():
            print(f"    Learning data saved to: {output_path}")
            return str(output_path)
        else:
            print(f"    Warning: Learning data file not created at {output_path}")
            return ""
    
    except subprocess.CalledProcessError as e:
        print(f"    Error processing {book_name} with CLI: {e}")
        print(f"    Command output: {e.stdout}")
        print(f"    Command errors: {e.stderr}")
        return ""
    except Exception as e:
        print(f"    Error processing {book_name}: {e}")
        import traceback
        traceback.print_exc()
        return ""


def process_learning_directory(learn_dir: str, output_dir: str):
    """
    Process all matching PDF/KRDS pairs in the learning directory.
    
    Args:
        learn_dir: Path to the learning directory
        output_dir: Path to save all learning data
    """
    print(f"📚 Processing learning directory: {learn_dir}")
    
    # Create output directory if it doesn't exist
    output_path = PathLib(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find matching PDF/KRDS files
    matches = find_matching_files(learn_dir)
    
    if not matches:
        print("No matching PDF/KRDS pairs found.")
        return
    
    print(f"Found {len(matches)} matching PDF/KRDS pairs")
    
    # Process each match
    all_learning_data_paths = []
    
    for match in matches:
        try:
            learning_data_path = process_book_learning(
                match['pdf_file'],
                match['krds_file'],
                match['clippings_file'],
                match['book_name'],
                output_dir
            )
            
            if learning_data_path:
                all_learning_data_paths.append(learning_data_path)
                
        except Exception as e:
            print(f"Error processing {match['book_name']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Combine all learning data into one file
    if all_learning_data_paths:
        combined_data = []
        
        for data_path in all_learning_data_paths:
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                    combined_data.extend(book_data)
            except Exception as e:
                print(f"Error loading learning data from {data_path}: {e}")
        
        # Save combined data
        combined_output_path = output_path / "combined_learning_data.json"
        with open(combined_output_path, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Combined learning data for {len(combined_data)} unmatched clippings saved to {combined_output_path}")
    
    print("✅ Processing complete!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Process multiple files in learning directory for Kindle PDF Annotator")
    parser.add_argument("learn_dir", help="Path to the learning directory containing PDFs and KRDS files")
    parser.add_argument("-o", "--output", default="learning_output", help="Output directory for learning data (default: learning_output)")
    
    args = parser.parse_args()
    
    process_learning_directory(args.learn_dir, args.output)


if __name__ == "__main__":
    main()