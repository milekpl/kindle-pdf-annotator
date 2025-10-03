# Sample Kindle PDF Annotator Data

This directory contains sample data files for testing the Kindle PDF Annotator application.

## Files Included

- `sample_MyClippings.txt` - Example MyClippings.txt file with sample annotations
- `sample_annotations.json` - JSON format annotations for testing
- `README.md` - This documentation file

## Usage

1. Use these files to test the application without real Kindle data
2. Copy the structure to create your own test data
3. The sample MyClippings.txt shows the expected format for Kindle annotations

## File Formats

### MyClippings.txt Format
```
Book Title (Author Name)
- Your Highlight on Location 156-157 | Added on Wednesday, March 15, 2023 2:34:15 PM

[Highlighted text content]
==========
```

Each annotation is separated by a line of equal signs (==========).

### JSON Annotations Format
```json
{
  "title": "Book Title",
  "author": "Author Name",
  "type": "highlight",
  "location": "156-157",
  "content": "Highlighted text content",
  "date_added": "2023-03-15T14:34:15"
}
```