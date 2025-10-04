#!/usr/bin/env python3
"""
Frequency Analysis Script for Kindle PDF Annotator

This script analyzes the differences between unmatched clippings and their 
PDF context to identify common transformations needed for better matching.
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Tuple


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


def find_text_differences(clipping: str, context: str) -> List[Tuple[str, str]]:
    """
    Find differences between clipping and context by comparing character by character.
    
    Args:
        clipping: The original clipping text
        context: The surrounding PDF context
        
    Returns:
        List of (clipping_part, context_part) tuples showing differences
    """
    norm_clipping = normalize_text(clipping)
    norm_context = normalize_text(context)
    
    # Find the position in context where the clipping most likely appears
    best_match_pos = -1
    best_similarity = 0
    
    # Try to find where the clipping might start in the context
    for i in range(len(norm_context) - len(norm_clipping) + 1):
        context_slice = norm_context[i:i + len(norm_clipping)]
        similarity = similarity_ratio(norm_clipping, context_slice)
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match_pos = i
    
    if best_match_pos == -1:
        # If we can't find a good match, return the full texts as different
        return [(norm_clipping, norm_context)]
    
    # Compare the matched section in more detail
    matched_context = norm_context[best_match_pos:best_match_pos + len(norm_clipping)]
    
    # Use difflib to find more detailed differences
    import difflib
    
    # Tokenize into words for more detailed comparison
    clip_words = re.findall(r'\S+|\s+', norm_clipping)
    context_words = re.findall(r'\S+|\s+', matched_context)
    
    # Compare word by word
    differences = []
    min_len = min(len(clip_words), len(context_words))
    
    for i in range(min_len):
        if clip_words[i] != context_words[i]:
            differences.append((clip_words[i], context_words[i]))
    
    # Add any remaining words if lengths differ
    if len(clip_words) > min_len:
        differences.extend([(word, '') for word in clip_words[min_len:]])
    if len(context_words) > min_len:
        differences.extend([('', word) for word in context_words[min_len:]])
    
    return differences


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # Use a simple similarity calculation
    import difflib
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def extract_transformation_patterns(differences: List[Tuple[str, str]]) -> List[str]:
    """
    Extract potential transformation patterns from the differences.
    
    Args:
        differences: List of (clipping_part, context_part) tuples
        
    Returns:
        List of transformation patterns detected
    """
    transformations = []
    
    for clip_part, context_part in differences:
        # Check for whitespace differences
        if clip_part.replace(' ', '') == context_part.replace(' ', ''):
            transformations.append('whitespace_normalization')
        
        # Check for case differences
        if clip_part.lower() == context_part.lower():
            transformations.append('case_normalization')
        
        # Check for punctuation differences
        clip_clean = re.sub(r'[^\w\s]', '', clip_part)
        context_clean = re.sub(r'[^\w\s]', '', context_part)
        if clip_clean == context_clean:
            transformations.append('punctuation_normalization')
        
        # Check for specific character differences (ligatures, etc.)
        if clip_part.replace('fi', 'ﬁ') == context_part or clip_part.replace('fl', 'ﬂ') == context_part:
            transformations.append('ligature_normalization')
        
        # Check for hyphen differences
        clip_no_hyphen = clip_part.replace('-', '').replace('\u00AD', '')
        context_no_hyphen = context_part.replace('-', '').replace('\u00AD', '')
        if clip_no_hyphen == context_no_hyphen:
            transformations.append('hyphen_normalization')
        
        # Check for special character substitutions
        if len(clip_part) == len(context_part):
            for i in range(len(clip_part)):
                if clip_part[i] != context_part[i]:
                    transformations.append(f'character_substitution_{clip_part[i]}_to_{context_part[i]}')
    
    return transformations


def analyze_learning_data(learning_data_path: str) -> Dict[str, Any]:
    """
    Analyze learning data to identify transformation patterns.
    
    Args:
        learning_data_path: Path to the learning data JSON file
        
    Returns:
        Analysis results including transformation frequency
    """
    print(f"🔍 Loading learning data from: {learning_data_path}")
    
    with open(learning_data_path, 'r', encoding='utf-8') as f:
        learning_data = json.load(f)
    
    print(f"📊 Analyzing {len(learning_data)} unmatched clippings...")
    
    all_differences = []
    all_transformations = []
    
    for i, clipping_data in enumerate(learning_data):
        print(f"   Analyzing clipping {i+1}/{len(learning_data)}: {repr(clipping_data['original_clipping'][:50])}...")
        
        differences = find_text_differences(
            clipping_data['original_clipping'],
            clipping_data['pdf_context']
        )
        
        all_differences.extend(differences)
        
        transformations = extract_transformation_patterns(differences)
        all_transformations.extend(transformations)
    
    # Count transformation frequencies
    transformation_counts = Counter(all_transformations)
    
    # Prepare results
    results = {
        'total_clippings': len(learning_data),
        'total_differences': len(all_differences),
        'transformation_counts': dict(transformation_counts),
        'transformation_frequency': {k: v/len(learning_data) for k, v in transformation_counts.items()},
        'top_transformations': transformation_counts.most_common()
    }
    
    return results


def suggest_transformations(analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Suggest specific text transformation rules based on analysis.
    
    Args:
        analysis_results: Results from analyze_learning_data function
        
    Returns:
        List of suggested transformation rules
    """
    suggestions = []
    
    # Get top transformations
    top_transformations = analysis_results.get('top_transformations', [])
    
    for transformation, count in top_transformations:
        frequency = count / analysis_results['total_clippings']
        
        if 'whitespace' in transformation:
            suggestions.append({
                'transformation': transformation,
                'count': count,
                'frequency': frequency,
                'suggestion': 'Implement aggressive whitespace normalization (collapse multiple spaces, normalize line endings)',
                'code_implementation': "text = ' '.join(text.split())"
            })
        elif 'case' in transformation:
            suggestions.append({
                'transformation': transformation,
                'count': count,
                'frequency': frequency,
                'suggestion': 'Consider case-insensitive matching',
                'code_implementation': "text = text.lower()"
            })
        elif 'punctuation' in transformation:
            suggestions.append({
                'transformation': transformation,
                'count': count,
                'frequency': frequency,
                'suggestion': 'Implement punctuation normalization',
                'code_implementation': "text = re.sub(r'[^\w\s]', '', text)"
            })
        elif 'ligature' in transformation:
            suggestions.append({
                'transformation': transformation,
                'count': count,
                'frequency': frequency,
                'suggestion': 'Add ligature replacement',
                'code_implementation': "text = text.replace('ﬁ', 'f').replace('ﬂ', 'f')"
            })
        elif 'hyphen' in transformation:
            suggestions.append({
                'transformation': transformation,
                'count': count,
                'frequency': frequency,
                'suggestion': 'Handle soft hyphens and hyphenation',
                'code_implementation': "text = text.replace('-\n', '').replace('\u00AD', '')"
            })
        else:
            suggestions.append({
                'transformation': transformation,
                'count': count,
                'frequency': frequency,
                'suggestion': f'Investigate pattern: {transformation}',
                'code_implementation': 'TBD'
            })
    
    return suggestions


def run_frequency_analysis(learning_data_path: str, output_path: str = None):
    """
    Run frequency analysis on learning data and output results.
    
    Args:
        learning_data_path: Path to the learning data JSON file
        output_path: Path to save the analysis results (optional)
    """
    # Perform analysis
    analysis_results = analyze_learning_data(learning_data_path)
    
    # Generate suggestions
    suggestions = suggest_transformations(analysis_results)
    
    # Print results
    print("\n📈 FREQUENCY ANALYSIS RESULTS:")
    print("=" * 80)
    print(f"Total clippings analyzed: {analysis_results['total_clippings']}")
    print(f"Total differences found: {analysis_results['total_differences']}")
    print("\nTop transformation patterns:")
    
    for i, (transformation, count) in enumerate(analysis_results['top_transformations'][:10]):
        frequency = analysis_results['transformation_frequency'][transformation]
        print(f"  {i+1:2d}. {transformation:30s} | Count: {count:4d} | Frequency: {frequency:.2%}")
    
    print("\n💡 SUGGESTED TRANSFORMATIONS:")
    print("-" * 80)
    
    for i, suggestion in enumerate(suggestions[:10]):  # Show top 10 suggestions
        print(f"\n{i+1:2d}. Transformation: {suggestion['transformation']}")
        print(f"    Count: {suggestion['count']}, Frequency: {suggestion['frequency']:.2%}")
        print(f"    Suggestion: {suggestion['suggestion']}")
        print(f"    Implementation: {suggestion['code_implementation']}")
    
    # Output to file if specified
    if output_path:
        output_data = {
            'analysis_results': analysis_results,
            'suggestions': suggestions
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Analysis results saved to: {output_path}")
    
    return analysis_results, suggestions


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Frequency analysis for Kindle PDF Annotator learning data")
    parser.add_argument("input", help="Path to learning data JSON file")
    parser.add_argument("-o", "--output", help="Path to save analysis results (optional)")
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"Error: Learning data file does not exist: {args.input}")
        sys.exit(1)
    
    run_frequency_analysis(args.input, args.output)


if __name__ == "__main__":
    main()