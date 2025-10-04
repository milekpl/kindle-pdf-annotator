#!/bin/bash

# Kindle PDF Annotator - Learning Mode Script
# This script runs the full learning mode workflow to analyze unmatched clippings

set -e  # Exit on any error

echo "📚 Kindle PDF Annotator - Learning Mode Workflow"
echo "================================================"

# Define directories
LEARN_DIR="./learn/documents"
OUTPUT_DIR="./learning_output"
SCRIPTS_DIR="./scripts"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "📁 Processing learning directory: $LEARN_DIR"
echo "📂 Output directory: $OUTPUT_DIR"
echo
echo "💡 Note: PDF files starting with '._' (hidden system files) will be ignored"
echo

# Step 1: Process multiple files in learning directory
echo "🔍 Step 1: Processing multiple files in learning directory..."
echo "Command: python $SCRIPTS_DIR/process_learning_directory.py $LEARN_DIR -o $OUTPUT_DIR"
python "$SCRIPTS_DIR/process_learning_directory.py" "$LEARN_DIR" -o "$OUTPUT_DIR"

# Check if combined learning data was created
COMBINED_DATA="$OUTPUT_DIR/combined_learning_data.json"
if [ ! -f "$COMBINED_DATA" ]; then
    echo "❌ Error: Combined learning data not found at $COMBINED_DATA"
    exit 1
fi

echo "✅ Combined learning data created: $COMBINED_DATA"
echo

# Step 2: Run diff analysis
echo "🔍 Step 2: Running diff analysis on learning data..."
DIFF_OUTPUT="$OUTPUT_DIR/diff_analysis_results.json"
echo "Command: python $SCRIPTS_DIR/diff_analysis.py $COMBINED_DATA -o $DIFF_OUTPUT"
python "$SCRIPTS_DIR/diff_analysis.py" "$COMBINED_DATA" -o "$DIFF_OUTPUT"

if [ -f "$DIFF_OUTPUT" ]; then
    echo "✅ Diff analysis results saved: $DIFF_OUTPUT"
else
    echo "⚠️  Warning: Diff analysis did not create output file"
fi
echo

# Step 3: Run frequency analysis
echo "🔍 Step 3: Running frequency analysis to identify transformations..."
FREQ_OUTPUT="$OUTPUT_DIR/frequency_analysis_results.json"
echo "Command: python $SCRIPTS_DIR/frequency_transformations.py $COMBINED_DATA -o $FREQ_OUTPUT"
python "$SCRIPTS_DIR/frequency_transformations.py" "$COMBINED_DATA" -o "$FREQ_OUTPUT"

if [ -f "$FREQ_OUTPUT" ]; then
    echo "✅ Frequency analysis results saved: $FREQ_OUTPUT"
else
    echo "⚠️  Warning: Frequency analysis did not create output file"
fi
echo

# Summary
echo "📊 SUMMARY"
echo "=========="
echo "Learning data processed: $COMBINED_DATA"
echo "Diff analysis: $DIFF_OUTPUT"
echo "Frequency analysis: $FREQ_OUTPUT"
echo
echo "💡 Next steps:"
echo "  1. Review $FREQ_OUTPUT to see suggested transformations for improving text matching"
echo "  2. Apply the most frequent transformations to the text matching algorithm"
echo "  3. Re-run the learning process to measure improvements"
echo
echo "✅ Learning mode workflow completed!"