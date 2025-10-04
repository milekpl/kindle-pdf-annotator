#!/usr/bin/env python3
"""
Diff Analysis Script for Kindle PDF Annotator Learning Mode

This script analyzes the differences between unmatched clippings and their 
PDF context to identify patterns that prevent proper text matching.
"""

import json
import difflib
import sys
from pathlib import Path
from typing import List, Dict, Any


def normalize_text(text: str) -> str:
    """Normalize text for better comparison"""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Handle ligatures
    text = text.replace('ﬁ', 'f').replace('ﬂ', 'f').replace('ﬀ', 'f')
    text = text.replace('ﬃ', 'f').replace('ﬄ', 'f')
    text = text.replace('ﬆ', 's').replace('ﬅ', 's')
    # Handle soft hyphens
    text = text.replace('\u00AD', '')  # Soft hyphen
    text = text.replace('-\n', '').replace('-\r\n', '')  # Hyphenated line breaks
    return text


def analyze_differences(clipping: str, context: str) -> Dict[str, Any]:
    """
    Analyze the differences between a clipping and its PDF context.
    
    Args:
        clipping: The original clipping text from MyClippings.txt
        context: The surrounding context from the PDF
    
    Returns:
        A dictionary containing the differences and analysis
    """
    norm_clipping = normalize_text(clipping)
    norm_context = normalize_text(context)
    
    # Find the best matching substring in the context
    best_match = None
    best_ratio = 0
    
    # Try different slices of the context to find where the clipping might appear
    clipping_len = len(norm_clipping)
    context_len = len(norm_context)
    
    for i in range(max(0, context_len - clipping_len * 2)):
        # Extract a slice that's potentially longer than the clipping
        slice_end = min(i + clipping_len + 50, context_len)
        context_slice = norm_context[i:slice_end]
        
        # Calculate similarity ratio
        ratio = difflib.SequenceMatcher(None, norm_clipping, context_slice).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = {
                'start_pos': i,
                'end_pos': slice_end,
                'context_slice': context_slice,
                'similarity_ratio': ratio
            }
    
    # Perform diff analysis
    diff_lines = list(difflib.unified_diff(
        [norm_clipping], 
        [best_match['context_slice'] if best_match else norm_context], 
        lineterm='', 
        n=0
    ))
    
    return {
        'clipping': clipping,
        'context': context,
        'normalized_clipping': norm_clipping,
        'normalized_context': norm_context,
        'best_match': best_match,
        'similarity_ratio': best_ratio,
        'diff_analysis': diff_lines
    }


def run_diff_analysis(learning_data_path: str, output_path: str = None):
    """
    Run diff analysis on learning data and output results.
    
    Args:
        learning_data_path: Path to the learning data JSON file
        output_path: Path to save the analysis results (optional)
    """
    print(f"🔍 Loading learning data from: {learning_data_path}")
    
    with open(learning_data_path, 'r', encoding='utf-8') as f:
        learning_data = json.load(f)
    
    print(f"📊 Analyzing {len(learning_data)} unmatched clippings...")
    
    analysis_results = []
    
    for i, clipping_data in enumerate(learning_data):
        print(f"   Processing clipping {i+1}/{len(learning_data)}: {repr(clipping_data['original_clipping'][:50])}...")
        
        result = analyze_differences(
            clipping_data['original_clipping'],
            clipping_data['pdf_context']
        )
        
        result['original_data'] = clipping_data
        analysis_results.append(result)
    
    # Output results
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        print(f"📈 Analysis results saved to: {output_path}")
    else:
        # Print summary to console
        print("\n📈 ANALYSIS SUMMARY:")
        print("=" * 60)
        
        low_similarity_count = 0
        total_similarity = 0
        
        for result in analysis_results:
            if result['similarity_ratio'] < 0.5:
                low_similarity_count += 1
            total_similarity += result['similarity_ratio']
        
        avg_similarity = total_similarity / len(analysis_results) if analysis_results else 0
        
        print(f"Total unmatched clippings: {len(analysis_results)}")
        print(f"Low similarity matches (<0.5): {low_similarity_count}")
        print(f"Average similarity ratio: {avg_similarity:.2f}")
        
        print("\n🔍 SAMPLE DIFF ANALYSIS (first 3):")
        print("-" * 60)
        
        for i, result in enumerate(analysis_results[:3]):
            clipping = result['original_data']['original_clipping']
            context = result['original_data']['pdf_context']
            ratio = result['similarity_ratio']
            
            print(f"\nClipping {i+1} - Similarity: {ratio:.2f}")
            print(f"Original: {repr(clipping[:100])}...")
            print(f"Context:  {repr(context[:100])}...")
            
            if result['best_match']:
                print(f"Best match in context: {repr(result['best_match']['context_slice'][:100])}...")
    
    return analysis_results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Diff analysis for Kindle PDF Annotator learning data")
    parser.add_argument("input", help="Path to learning data JSON file")
    parser.add_argument("-o", "--output", help="Path to save analysis results (optional)")
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"Error: Learning data file does not exist: {args.input}")
        sys.exit(1)
    
    run_diff_analysis(args.input, args.output)


if __name__ == "__main__":
    main()