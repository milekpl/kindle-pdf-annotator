#!/usr/bin/env python3
\"\"\"
Test script to parse multiple sample files and check annotation accuracy
\"\"\"\n
import fitz
from pathlib import Path
import sys\n
sys.path.insert(0, str(Path(__file__).parent / \"src\"))\n
from src.kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from src.pdf_processor.pdf_annotator import annotate_pdf_file\n
\n
def test_sample_files():
    \"\"\"Test parsing of multiple sample files\"\"\"
    \n
    samples_dir = Path(\"examples/sample_data\")
    \n
    # Define sample configurations - include all three PDFs
    test_cases = [
        {
            \"name\": \"Peirce - The Fixation of Belief\",
            \"pdf_path\": samples_dir / \"peirce-charles-fixation-belief.pdf\",
            \"sdr_path\": samples_dir / \"peirce-charles-fixation-belief.sdr\",
            \"clippings_path\": samples_dir / \"peirce-charles-fixation-belief-clippings.txt\",
            \"book_name\": \"peirce-charles-fixation-belief\",
        },
        {
            \"name\": \"Theatre Hunger Paper\",
            \"pdf_path\": samples_dir / \"Downey_2024_Theatre_Hunger_Scaling_Up_Paper.pdf\",
            \"sdr_path\": samples_dir / \"Downey_2024_Theatre_Hunger_Scaling_Up_Paper.sdr\",
            \"clippings_path\": samples_dir / \"Downey_2024_Theatre_Hunger_Scaling_Up_Paper-clippings.txt\",
            \"book_name\": \"Downey - 2024 - Theatre Hunger An Underestimated Scaling Up Pro\",
        },
        {
            \"name\": \"659ec7697e419\",
            \"pdf_path\": samples_dir / \"659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.pdf\",
            \"sdr_path\": samples_dir / \"659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ.sdr\",
            \"clippings_path\": samples_dir / \"659ec7697e419-clippings.txt\",
            \"book_name\": \"659ec7697e419.pdf-cdeKey_B7PXKZMQKCJFWMWAKW7CUBENBUE7XPLQ\",
        }
    ]
    \n
    for test_case in test_cases:
        print(f\"\\n{'='*60}\")
        print(f\"Testing: {test_case['name']}\")
        print(f\"{'='*60}\")
        \n
        pdf_path = test_case['pdf_path']
        sdr_path = test_case['sdr_path']
        clippings_path = test_case['clippings_path']
        book_name = test_case['book_name']
        \n
        if not pdf_path.exists():
            print(f\"❌ PDF file does not exist: {pdf_path}\")
            continue
            \n
        if not sdr_path.exists():
            print(f\"❌ SDR folder does not exist: {sdr_path}\")
            continue
            \n
        if not clippings_path.exists():
            print(f\"⚠️  Clippings file does not exist: {clippings_path}\")
        \n
        # Find KRDS files (.pds or .pdt)
        krds_files = list(sdr_path.glob(\"*.pds\")) + list(sdr_path.glob(\"*.pdt\"))
        if not krds_files:
            print(f\"❌ No KRDS files found in {sdr_path}\")
            continue
            \n
        print(f\"📖 Found {len(krds_files)} KRDS files:\")
        for krds_file in krds_files:
            print(f\"   - {krds_file.name}\")
        \n
        # Try to process the first KRDS file
        krds_file_path = str(krds_files[0])
        clippings_file_path = str(clippings_path) if clippings_path.exists() else \"\"
        \n
        print(f\"\\nProcessing annotations...\")
        try:
            annotations = create_amazon_compliant_annotations(
                krds_file_path, 
                clippings_file_path, 
                book_name
            )
            \n
            print(f\"✅ Found {len(annotations)} annotations\")
            \n
            # Check some sample annotations
            highlights = [a for a in annotations if a['type'] == 'highlight']
            notes = [a for a in annotations if a['type'] == 'note']
            bookmarks = [a for a in annotations if a['type'] == 'bookmark']
            \n
            print(f\"   - Highlights: {len(highlights)}\")
            print(f\"   - Notes: {len(notes)}\")
            print(f\"   - Bookmarks: {len(bookmarks)}\")
            \n
            # Check if we have the correct coordinates for sample annotations
            print(\"\\nSample highlight annotations:\")
            for i, h in enumerate(highlights[:3]):  # Show first 3
                print(f\"   {i+1}. Page {h['pdf_page_0based']}: ({h['pdf_x']:.2f}, {h['pdf_y']:.2f}) - w:{h['pdf_width']:.2f}, h:{h['pdf_height']:.2f}\")
                if h.get('content'):
                    print(f\"      Content: '{h['content'][:50]}...'\")
\n
            # Try to create annotated PDF
            output_path = f\"test_output_{test_case['book_name'].replace(' ', '_')[:20]}.pdf\"
            print(f\"\\nCreating annotated PDF: {output_path}\")
            \n
            success = annotate_pdf_file(str(pdf_path), annotations, output_path)
            if success:
                print(f\"✅ Annotated PDF created successfully: {output_path}\")
            else:
                print(f\"❌ Failed to create annotated PDF\")
                \n
        except Exception as e:
            print(f\"❌ Error processing annotations: {e}\")
            import traceback
            traceback.print_exc()\n
\n
\n
if __name__ == \"__main__\": 
    test_sample_files()