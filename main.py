#!/usr/bin/env python3
"""
Kindle PDF Annotator - Main Entry Point
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for the application"""
    try:
        from gui.main_window import KindlePDFAnnotatorGUI
        app = KindlePDFAnnotatorGUI()
        app.run()
    except ImportError as e:
        print(f"Error importing GUI components: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()