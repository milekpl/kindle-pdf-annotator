#!/usr/bin/env python3
"""
Kindle PDF Annotator - Main Entry Point (GUI)
"""

import sys


def main():
    """Main entry point for the GUI application"""
    try:
        from kindle_pdf_annotator.gui.main_window import KindlePDFAnnotatorGUI
        app = KindlePDFAnnotatorGUI()
        app.run()
    except ImportError as e:
        print(f"Error importing GUI components: {e}")
        print("Please ensure all dependencies are installed: pip install kindle-pdf-annotator")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
