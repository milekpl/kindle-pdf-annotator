"""
Kindle PDF Annotator GUI
Main application window using tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import json
import logging
from typing import Dict, List, Any, Optional

# Import our modules
from kindle_parser.clippings_parser import parse_clippings_file
from kindle_parser.amazon_coordinate_system import create_amazon_compliant_annotations
from pdf_processor.amazon_to_pdf_adapter import convert_amazon_to_pdf_annotator_format
from pdf_processor.pdf_annotator import annotate_pdf_file

logger = logging.getLogger(__name__)


class KindlePDFAnnotatorGUI:
    """Main application GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kindle PDF Annotator")
        self.root.geometry("800x700")
        
        # Application state
        self.kindle_folder = ""
        self.pdf_file = ""
        self.clippings_file = ""
        self.output_file = ""
        self.annotations = []
        
        self._setup_ui()
        self._setup_logging()
    
    def _setup_ui(self):
        """Set up the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Kindle PDF Annotator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection section
        self._create_file_selection_section(main_frame, 1)
        
        # Processing options section
        self._create_processing_section(main_frame, 6)
        
        # Progress and output section
        self._create_output_section(main_frame, 10)
        
        # Action buttons
        self._create_action_buttons(main_frame, 14)
    
    def _create_file_selection_section(self, parent, start_row):
        """Create file selection section"""
        # Section title
        ttk.Label(parent, text="File Selection", 
                 font=("Arial", 12, "bold")).grid(row=start_row, column=0, 
                                                 columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Kindle documents folder
        ttk.Label(parent, text="Kindle Documents Folder:").grid(row=start_row+1, column=0, 
                                                                sticky=tk.W, pady=2)
        self.kindle_folder_var = tk.StringVar()
        kindle_entry = ttk.Entry(parent, textvariable=self.kindle_folder_var, width=50)
        kindle_entry.grid(row=start_row+1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(parent, text="Browse", 
                  command=self._browse_kindle_folder).grid(row=start_row+1, column=2, 
                                                          pady=2, padx=(5, 0))
        
        # PDF file
        ttk.Label(parent, text="PDF File:").grid(row=start_row+2, column=0, 
                                                 sticky=tk.W, pady=2)
        self.pdf_file_var = tk.StringVar()
        pdf_entry = ttk.Entry(parent, textvariable=self.pdf_file_var, width=50)
        pdf_entry.grid(row=start_row+2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(parent, text="Browse", 
                  command=self._browse_pdf_file).grid(row=start_row+2, column=2, 
                                                     pady=2, padx=(5, 0))
        
        # MyClippings.txt file (optional)
        ttk.Label(parent, text="MyClippings.txt (Optional):").grid(row=start_row+3, column=0, 
                                                                   sticky=tk.W, pady=2)
        self.clippings_file_var = tk.StringVar()
        clippings_entry = ttk.Entry(parent, textvariable=self.clippings_file_var, width=50)
        clippings_entry.grid(row=start_row+3, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(parent, text="Browse", 
                  command=self._browse_clippings_file).grid(row=start_row+3, column=2, 
                                                           pady=2, padx=(5, 0))
        
        # Output file
        ttk.Label(parent, text="Output PDF:").grid(row=start_row+4, column=0, 
                                                  sticky=tk.W, pady=2)
        self.output_file_var = tk.StringVar()
        output_entry = ttk.Entry(parent, textvariable=self.output_file_var, width=50)
        output_entry.grid(row=start_row+4, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        ttk.Button(parent, text="Browse", 
                  command=self._browse_output_file).grid(row=start_row+4, column=2, 
                                                        pady=2, padx=(5, 0))
    
    def _create_processing_section(self, parent, start_row):
        """Create processing options section"""
        # Section title
        ttk.Label(parent, text="Processing Options", 
                 font=("Arial", 12, "bold")).grid(row=start_row, column=0, 
                                                 columnspan=3, sticky=tk.W, pady=(20, 10))
        
        # Options frame
        options_frame = ttk.Frame(parent)
        options_frame.grid(row=start_row+1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Processing options
        self.include_highlights_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include Highlights", 
                       variable=self.include_highlights_var).grid(row=0, column=0, sticky=tk.W)
        
        self.include_notes_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include Notes", 
                       variable=self.include_notes_var).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        self.include_bookmarks_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include Bookmarks", 
                       variable=self.include_bookmarks_var).grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
    
    def _create_output_section(self, parent, start_row):
        """Create output and progress section"""
        # Section title
        ttk.Label(parent, text="Output", 
                 font=("Arial", 12, "bold")).grid(row=start_row, column=0, 
                                                 columnspan=3, sticky=tk.W, pady=(20, 10))
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        progress_label = ttk.Label(parent, textvariable=self.progress_var)
        progress_label.grid(row=start_row+1, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        self.progress_bar = ttk.Progressbar(parent, mode='indeterminate')
        self.progress_bar.grid(row=start_row+2, column=0, columnspan=3, 
                              sticky=(tk.W, tk.E), pady=5)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(parent, height=10, wrap=tk.WORD)
        self.output_text.grid(row=start_row+3, column=0, columnspan=3, 
                             sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure text area to expand
        parent.rowconfigure(start_row+3, weight=1)
    
    def _create_action_buttons(self, parent, start_row):
        """Create action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=start_row, column=0, columnspan=3, pady=(20, 0))
        
        # Process button
        self.process_button = ttk.Button(button_frame, text="Process Annotations", 
                                        command=self._start_processing)
        self.process_button.grid(row=0, column=0, padx=(0, 10))
        
        # Clear button
        ttk.Button(button_frame, text="Clear Log", 
                  command=self._clear_log).grid(row=0, column=1, padx=(0, 10))
        
        # Export annotations button
        ttk.Button(button_frame, text="Export Annotations", 
                  command=self._export_annotations).grid(row=0, column=2, padx=(0, 10))
        
        # Exit button
        ttk.Button(button_frame, text="Exit", 
                  command=self.root.quit).grid(row=0, column=3)
    
    def _setup_logging(self):
        """Set up logging to display in GUI"""
        # Create custom log handler for GUI
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.see(tk.END)
                self.text_widget.update()
        
        # Set up logging
        gui_handler = GUILogHandler(self.output_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Add handler to root logger
        logging.basicConfig(level=logging.INFO, handlers=[gui_handler])
    
    def _browse_kindle_folder(self):
        """Browse for Kindle documents folder"""
        folder = filedialog.askdirectory(title="Select Kindle Documents Folder")
        if folder:
            self.kindle_folder_var.set(folder)
            self.kindle_folder = folder
            self._log_message(f"Selected Kindle folder: {folder}")
    
    def _browse_pdf_file(self):
        """Browse for PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_file_var.set(file_path)
            self.pdf_file = file_path
            self._log_message(f"Selected PDF: {Path(file_path).name}")
            
            # Auto-suggest output filename
            if not self.output_file_var.get():
                output_path = str(Path(file_path).with_suffix('.annotated.pdf'))
                self.output_file_var.set(output_path)
    
    def _browse_clippings_file(self):
        """Browse for MyClippings.txt file"""
        file_path = filedialog.askopenfilename(
            title="Select MyClippings.txt File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.clippings_file_var.set(file_path)
            self.clippings_file = file_path
            self._log_message(f"Selected clippings file: {Path(file_path).name}")
    
    def _browse_output_file(self):
        """Browse for output PDF file"""
        file_path = filedialog.asksaveasfilename(
            title="Save Annotated PDF As",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            defaultextension=".pdf"
        )
        if file_path:
            self.output_file_var.set(file_path)
            self.output_file = file_path
            self._log_message(f"Output will be saved to: {Path(file_path).name}")
    
    def _start_processing(self):
        """Start processing annotations in a separate thread"""
        # Validate inputs
        if not self._validate_inputs():
            return
        
        # Disable process button
        self.process_button.config(state='disabled')
        self.progress_bar.start()
        self.progress_var.set("Processing...")
        
        # Start processing thread
        thread = threading.Thread(target=self._process_annotations)
        thread.daemon = True
        thread.start()
    
    def _validate_inputs(self) -> bool:
        """Validate user inputs"""
        if not self.kindle_folder or not Path(self.kindle_folder).exists():
            messagebox.showerror("Error", "Please select a valid Kindle documents folder")
            return False
        
        if not self.pdf_file or not Path(self.pdf_file).exists():
            messagebox.showerror("Error", "Please select a valid PDF file")
            return False
        
        if not self.output_file:
            messagebox.showerror("Error", "Please specify an output file")
            return False
        
        return True
    
    def _process_annotations(self):
        """Process annotations (runs in separate thread)"""
        try:
            self._log_message("🚀 Starting annotation processing with corrected page mapping...")
            
            # Step 1: Find and parse JSON files using the FINAL corrected parser
            annotations = []
            pdf_name = Path(self.pdf_file).stem
            
            self._log_message(f"Looking for JSON files for PDF: {pdf_name}")
            
            # Find JSON files in .sdr folder
            json_files = []
            if self.kindle_folder:
                kindle_path = Path(self.kindle_folder)
                for json_file in kindle_path.rglob("*.json"):
                    if pdf_name in str(json_file):
                        json_files.append(json_file)
            
            self._log_message(f"Found {len(json_files)} JSON files")
            
            # Parse each JSON file with FINAL corrected parser
            for json_file in json_files:
                try:
                    # Use FINAL corrected parser with MyClippings.txt for accurate page mapping
                    clippings_file = self.clippings_file if self.clippings_file and Path(self.clippings_file).exists() else None
                    if not clippings_file:
                        self._log_message(f"❌ MyClippings.txt file required for corrected parsing")
                        continue
                        
                    file_annotations = create_amazon_compliant_annotations(
                        str(json_file), 
                        clippings_file, 
                        pdf_name
                    )
                    
                    annotations.extend(file_annotations)
                    
                    self._log_message(f"✅ Extracted {len(file_annotations)} annotations from {json_file.name} with AMAZON coordinate system")
                except Exception as e:
                    self._log_message(f"❌ Error parsing {json_file.name}: {e}")
            
            self._log_message(f"📊 Total annotations with AMAZON coordinate system: {len(annotations)}")
            
            # Convert Amazon format to PDF annotator format
            self._log_message("Converting Amazon coordinate format to PDF annotator format...")
            converted_annotations = convert_amazon_to_pdf_annotator_format(annotations)
            self._log_message(f"📋 Converted {len(converted_annotations)} annotations for PDF embedding")
            
            # Quality check: Verify annotations aren't all on page 0
            if annotations:
                page_distribution = {}
                for annotation in annotations:
                    page = annotation.get('pdf_page_0based', 0)
                    page_distribution[page] = page_distribution.get(page, 0) + 1
                
                unique_pages = len(page_distribution)
                page_0_count = page_distribution.get(0, 0)
                
                self._log_message(f"📈 Page distribution: {unique_pages} unique pages")
                if unique_pages > 1:
                    self._log_message(f"✅ SUCCESS: Annotations spread across multiple pages (not all on page 0)")
                    sample_pages = sorted(page_distribution.keys())[:5]
                    self._log_message(f"   Sample pages: {sample_pages}")
                else:
                    if len(annotations) > 1:
                        self._log_message(f"❌ ERROR: All {len(annotations)} annotations on same page {list(page_distribution.keys())[0]}")
                    else:
                        self._log_message(f"ℹ️  Single annotation on page {list(page_distribution.keys())[0]}")
                
                if page_0_count > 0:
                    self._log_message(f"❌ ERROR: {page_0_count}/{len(annotations)} annotations incorrectly on page 0")
                else:
                    self._log_message(f"✅ SUCCESS: No annotations incorrectly placed on page 0")
                    
            # Store annotations for later use
            self.annotations = annotations
            if self.clippings_file and Path(self.clippings_file).exists():
                try:
                    clippings_result = parse_clippings_file(self.clippings_file)
                    
                    # Filter clippings for this PDF
                    pdf_title = pdf_name.replace('_', ' ').replace('-', ' ')
                    clippings_added = 0
                    
                    for book_title, book_data in clippings_result.get("books", {}).items():
                        if self._title_matches(book_title, pdf_title):
                            for clipping in book_data["clippings"]:
                                # Convert clipping to annotation format
                                clipping_annotation = {
                                    "type": f"clipping.{clipping.get('type', 'unknown')}",
                                    "category": clipping.get('type', 'unknown'),
                                    "content": clipping.get('content', ''),
                                    "page_number": 0,  # MyClippings doesn't have exact page mapping
                                    "coordinates": [50, 50, 200, 100],  # Default coordinates
                                    "creation_time": clipping.get('date_added'),
                                    "location": clipping.get('location', ''),
                                    "valid_position": False,
                                    "source": "MyClippings.txt"
                                }
                                annotations.append(clipping_annotation)
                                clippings_added += 1
                            
                            self._log_message(f"Added {clippings_added} clippings from MyClippings.txt")
                            break
                except Exception as e:
                    self._log_message(f"Error parsing MyClippings.txt: {e}")
            
            total_annotations = len(annotations)
            self._log_message(f"Total annotations found: {total_annotations}")
            
            if total_annotations == 0:
                self._log_message("No annotations found. Please check your files and try again.")
                return
            
            # Step 3: Analyze page distribution - use Amazon coordinate format
            amazon_annotations = [a for a in annotations if a.get("source", "").startswith("json") and "amazon" in a.get("source", "")]
            if amazon_annotations:
                pages = [a["pdf_page_0based"] for a in amazon_annotations]
                unique_pages = sorted(set(pages))
                self._log_message(f"Amazon annotations span pages: {unique_pages[:10]}..." if len(unique_pages) > 10 
                                 else f"Amazon annotations on pages: {unique_pages}")
            
            # Step 4: Create annotated PDF using Amazon coordinate system
            self._log_message("Creating annotated PDF with AMAZON coordinate system...")
            success = annotate_pdf_file(self.pdf_file, converted_annotations, self.output_file)
            
            if success:
                self._log_message(f"Successfully created annotated PDF: {self.output_file}")
                messagebox.showinfo("Success", f"Annotated PDF saved to:\n{self.output_file}")
            else:
                self._log_message("Failed to create annotated PDF")
                messagebox.showerror("Error", "Failed to create annotated PDF")
        
        except Exception as e:
            self._log_message(f"Error during processing: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
        
        finally:
            # Re-enable UI
            self.root.after(0, self._processing_complete)
    
    def _processing_complete(self):
        """Called when processing is complete"""
        self.process_button.config(state='normal')
        self.progress_bar.stop()
        self.progress_var.set("Ready")
    
    def _title_matches(self, title1: str, title2: str) -> bool:
        """Check if two titles match (fuzzy matching)"""
        t1 = title1.lower().replace(' ', '').replace('-', '').replace('_', '')
        t2 = title2.lower().replace(' ', '').replace('-', '').replace('_', '')
        return t1 in t2 or t2 in t1
    
    def _clear_log(self):
        """Clear the output log"""
        self.output_text.delete(1.0, tk.END)
    
    def _export_annotations(self):
        """Export found annotations to JSON file"""
        if not self.annotations:
            messagebox.showwarning("Warning", "No annotations to export. Process a file first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Annotations",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            defaultextension=".json"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.annotations, f, indent=2, default=str)
                self._log_message(f"Annotations exported to: {file_path}")
                messagebox.showinfo("Success", f"Annotations exported to:\n{file_path}")
            except Exception as e:
                self._log_message(f"Error exporting annotations: {e}")
                messagebox.showerror("Error", f"Failed to export annotations: {e}")
    
    def _log_message(self, message: str):
        """Add a message to the log"""
        self.root.after(0, lambda: self.output_text.insert(tk.END, f"{message}\n"))
        self.root.after(0, lambda: self.output_text.see(tk.END))
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


if __name__ == "__main__":
    app = KindlePDFAnnotatorGUI()
    app.run()