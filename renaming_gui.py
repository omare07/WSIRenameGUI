"""Phase 2: GUI for Label-Based Renaming of histology slides."""

import os
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pandas as pd

import config
import utils


class RenamingGUI:
    """GUI application for renaming slides based on label images."""
    
    def __init__(self, initial_folder: str = ""):
        self.root = tk.Tk()
        self.slide_folder = initial_folder
        self.label_folder = ""
        self.output_folder = ""
        self.prefix = config.DEFAULT_PREFIX
        self.extension = ".ndpi"
        
        self.label_files = []
        self.current_index = 0
        self.renaming_data = {}  # {original_path: new_name}
        
        # GUI components
        self.image_label = None
        self.identifier_var = None
        self.preview_var = None
        self.status_var = None
        self.progress_var = None
        
        self._setup_gui()
        
        # If initial folder is provided, set it and try to load images
        if initial_folder and os.path.exists(initial_folder):
            self.folder_var.set(initial_folder)
            # Auto-load images if folder is valid
            try:
                self._load_images()
            except Exception as e:
                print(f"Could not auto-load images from {initial_folder}: {e}")
        
        self._update_display()
    
    def _setup_gui(self):
        """Setup the main GUI."""
        self.root.title("Histology Slide Renaming Tool")
        self.root.geometry("1000x800")
        
        # Main menu
        self._create_menu()
        
        # Configuration frame
        config_frame = ttk.LabelFrame(self.root, text="Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Folder selection
        ttk.Label(config_frame, text="Slide Folder:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.folder_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.folder_var, width=50).grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(config_frame, text="Browse", command=self._browse_folder).grid(row=0, column=2, padx=5)
        
        # Output folder
        ttk.Label(config_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.output_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.output_var, width=50).grid(row=1, column=1, padx=5, sticky=tk.EW)
        ttk.Button(config_frame, text="Browse", command=self._browse_output).grid(row=1, column=2, padx=5)
        
        # Prefix and extension
        ttk.Label(config_frame, text="Prefix (auto-set):").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.prefix_var = tk.StringVar(value=config.DEFAULT_PREFIX)
        ttk.Entry(config_frame, textvariable=self.prefix_var, width=20).grid(row=2, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(config_frame, text="Extension:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.ext_var = tk.StringVar(value=".ndpi")
        ext_combo = ttk.Combobox(config_frame, textvariable=self.ext_var, 
                                values=[".ndpi", ".svs", ".scn", ".vms"], width=10)
        ext_combo.grid(row=2, column=3, padx=5, sticky=tk.W)
        
        ttk.Button(config_frame, text="Load Images", command=self._load_images).grid(row=3, column=1, pady=10)
        
        config_frame.columnconfigure(1, weight=1)
        
        # Image display frame
        image_frame = ttk.LabelFrame(self.root, text="Label Image", padding=10)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Image display
        self.image_label = ttk.Label(image_frame, text="No image loaded", anchor=tk.CENTER)
        self.image_label.pack(expand=True)
        
        # Navigation frame
        nav_frame = ttk.Frame(image_frame)
        nav_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(nav_frame, text="<< Previous", command=self._previous_image).pack(side=tk.LEFT, padx=5)
        
        self.image_info_var = tk.StringVar(value="No images loaded")
        ttk.Label(nav_frame, textvariable=self.image_info_var).pack(side=tk.LEFT, padx=20)
        
        ttk.Button(nav_frame, text="Next >>", command=self._next_image).pack(side=tk.RIGHT, padx=5)
        ttk.Button(nav_frame, text="Skip", command=self._skip_image).pack(side=tk.RIGHT, padx=5)
        
        # Input frame
        input_frame = ttk.LabelFrame(self.root, text="Renaming", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Identifier input
        ttk.Label(input_frame, text="Numeric Identifier:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.identifier_var = tk.StringVar()
        self.identifier_var.trace('w', self._update_preview)
        identifier_entry = ttk.Entry(input_frame, textvariable=self.identifier_var, width=20)
        identifier_entry.grid(row=0, column=1, padx=5, sticky=tk.W)
        identifier_entry.bind('<Return>', lambda e: self._apply_current_rename())
        
        ttk.Label(input_frame, text="(e.g., '002 001' or '002001')").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # Preview
        ttk.Label(input_frame, text="Preview:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.preview_var = tk.StringVar()
        preview_label = ttk.Label(input_frame, textvariable=self.preview_var, font=("Arial", 10, "bold"))
        preview_label.grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)
        
        # Action buttons
        ttk.Button(input_frame, text="Apply to Current", command=self._apply_current_rename).grid(row=2, column=0, pady=10, padx=5)
        ttk.Button(input_frame, text="Clear Current", command=self._clear_current_rename).grid(row=2, column=1, pady=10, padx=5)
        
        # Status and progress frame
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(20, 0))
        
        # Final action frame
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(action_frame, text="Show Rename Summary", command=self._show_summary).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Rename All Files", command=self._rename_all_files, 
                  style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Save Session", command=self._save_session).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Load Session", command=self._load_session).pack(side=tk.RIGHT, padx=5)
    
    def _create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Images", command=self._load_images)
        file_menu.add_separator()
        file_menu.add_command(label="Save Session", command=self._save_session)
        file_menu.add_command(label="Load Session", command=self._load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _browse_folder(self):
        """Browse for slide folder."""
        folder = filedialog.askdirectory(title="Select Slide Folder")
        if folder:
            self.folder_var.set(folder)
            # Auto-set prefix based on selected directory name
            folder_name = os.path.basename(os.path.normpath(folder))
            if folder_name and folder_name != '.':
                auto_prefix = f"{folder_name}_"
                self.prefix_var.set(auto_prefix)
                self.status_var.set(f"Auto-set prefix to '{auto_prefix}' based on directory name")
    
    def _browse_output(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_var.set(folder)
    
    def _load_images(self):
        """Load label images from the selected folder."""
        slide_folder = self.folder_var.get()
        if not slide_folder or not os.path.exists(slide_folder):
            messagebox.showerror("Error", "Please select a valid slide folder")
            return
        
        self.slide_folder = slide_folder
        self.label_folder = os.path.join(slide_folder, config.LABEL_FOLDER)
        
        if not os.path.exists(self.label_folder):
            messagebox.showerror("Error", f"Label folder not found: {self.label_folder}\\nRun Phase 1 first!")
            return
        
        # Auto-set prefix based on directory name
        folder_name = os.path.basename(os.path.normpath(slide_folder))
        if folder_name and folder_name != '.':
            auto_prefix = f"{folder_name}_"
            self.prefix_var.set(auto_prefix)
            self.status_var.set(f"Auto-set prefix to '{auto_prefix}' based on directory name")
        
        # Get output folder
        output_folder = self.output_var.get()
        if not output_folder:
            # Default to slide folder
            self.output_folder = slide_folder
            self.output_var.set(slide_folder)
        else:
            self.output_folder = output_folder
        
        # Load label files
        self.label_files = []
        for file in os.listdir(self.label_folder):
            if file.lower().endswith('.jpg') and not utils.should_skip_file(file):
                self.label_files.append(file)
        
        self.label_files.sort()
        
        if not self.label_files:
            messagebox.showwarning("Warning", "No label images found!")
            return
        
        # Update prefix and extension
        self.prefix = self.prefix_var.get()
        self.extension = self.ext_var.get()
        
        # Reset state
        self.current_index = 0
        self.renaming_data = {}
        
        self._update_display()
        self.status_var.set(f"Loaded {len(self.label_files)} label images")
    
    def _update_display(self):
        """Update the image display and info."""
        if not self.label_files:
            self.image_label.config(image='', text="No images loaded")
            self.image_info_var.set("No images loaded")
            return
        
        if self.current_index >= len(self.label_files):
            self.current_index = 0
        
        # Load and display current image
        current_file = self.label_files[self.current_index]
        image_path = os.path.join(self.label_folder, current_file)
        
        try:
            # Load and resize image for display
            pil_image = Image.open(image_path)
            
            # Calculate display size maintaining aspect ratio
            display_width, display_height = config.IMAGE_DISPLAY_SIZE
            img_width, img_height = pil_image.size
            
            scale = min(display_width / img_width, display_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            display_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(display_image)
            
            self.image_label.config(image=self.photo, text="")
            
        except Exception as e:
            self.image_label.config(image='', text=f"Error loading image: {e}")
        
        # Update info
        self.image_info_var.set(f"Image {self.current_index + 1} of {len(self.label_files)}: {current_file}")
        
        # Update identifier if already set for this image
        slide_name = os.path.splitext(current_file)[0]
        original_slide_path = self._find_original_slide(slide_name)
        
        if original_slide_path and original_slide_path in self.renaming_data:
            # Extract identifier from stored rename
            stored_name = self.renaming_data[original_slide_path]
            identifier = self._extract_identifier_from_name(stored_name)
            self.identifier_var.set(identifier)
        else:
            self.identifier_var.set("")
        
        self._update_preview()
    
    def _find_original_slide(self, slide_name: str) -> Optional[str]:
        """Find the original slide file corresponding to the label."""
        for ext in config.SUPPORTED_EXTENSIONS:
            slide_path = os.path.join(self.slide_folder, f"{slide_name}{ext}")
            if os.path.exists(slide_path):
                return slide_path
        return None
    
    def _extract_identifier_from_name(self, filename: str) -> str:
        """Extract identifier from generated filename."""
        # Remove prefix and extension
        base = os.path.splitext(filename)[0]
        if base.startswith(self.prefix):
            identifier_part = base[len(self.prefix):]
            # Convert underscores back to spaces for display
            return identifier_part.replace('_', ' ')
        return ""
    
    def _update_preview(self, *args):
        """Update the filename preview."""
        identifier = self.identifier_var.get().strip()
        if not identifier:
            self.preview_var.set("")
            return
        
        try:
            new_filename = utils.generate_new_filename(self.prefix, identifier, self.extension)
            
            # Check if file would exist in output folder
            output_path = os.path.join(self.output_folder, new_filename)
            if os.path.exists(output_path):
                duplicate_path = utils.check_duplicate_filename(output_path)
                duplicate_name = os.path.basename(duplicate_path)
                self.preview_var.set(f"{duplicate_name} (duplicate detected)")
            else:
                self.preview_var.set(new_filename)
                
        except Exception as e:
            self.preview_var.set(f"Error: {e}")
    
    def _previous_image(self):
        """Go to previous image."""
        if not self.label_files:
            return
        
        self.current_index = (self.current_index - 1) % len(self.label_files)
        self._update_display()
    
    def _next_image(self):
        """Go to next image."""
        if not self.label_files:
            return
        
        self.current_index = (self.current_index + 1) % len(self.label_files)
        self._update_display()
    
    def _skip_image(self):
        """Skip current image and go to next."""
        self._clear_current_rename()
        self._next_image()
    
    def _apply_current_rename(self):
        """Apply renaming for current image."""
        if not self.label_files:
            return
        
        identifier = self.identifier_var.get().strip()
        if not identifier:
            messagebox.showwarning("Warning", "Please enter a numeric identifier")
            return
        
        # Find original slide file
        current_label = self.label_files[self.current_index]
        slide_name = os.path.splitext(current_label)[0]
        original_slide_path = self._find_original_slide(slide_name)
        
        if not original_slide_path:
            messagebox.showerror("Error", f"Original slide file not found for {current_label}")
            return
        
        # Generate new filename
        try:
            new_filename = utils.generate_new_filename(self.prefix, identifier, self.extension)
            
            # Store in renaming data
            self.renaming_data[original_slide_path] = new_filename
            
            self.status_var.set(f"Applied rename: {os.path.basename(original_slide_path)} → {new_filename}")
            
            # Auto-advance to next image
            self._next_image()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error generating filename: {e}")
    
    def _clear_current_rename(self):
        """Clear renaming for current image."""
        if not self.label_files:
            return
        
        current_label = self.label_files[self.current_index]
        slide_name = os.path.splitext(current_label)[0]
        original_slide_path = self._find_original_slide(slide_name)
        
        if original_slide_path and original_slide_path in self.renaming_data:
            del self.renaming_data[original_slide_path]
            self.identifier_var.set("")
            self.status_var.set("Cleared current rename")
    
    def _show_summary(self):
        """Show renaming summary."""
        if not self.renaming_data:
            messagebox.showinfo("Summary", "No files scheduled for renaming")
            return
        
        summary_window = tk.Toplevel(self.root)
        summary_window.title("Rename Summary")
        summary_window.geometry("800x600")
        
        # Create treeview
        columns = ("Original", "New Name", "Status")
        tree = ttk.Treeview(summary_window, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=250)
        
        # Add data
        for original_path, new_name in self.renaming_data.items():
            original_name = os.path.basename(original_path)
            output_path = os.path.join(self.output_folder, new_name)
            
            if os.path.exists(output_path):
                status = "Duplicate - will add suffix"
            else:
                status = "Ready"
            
            tree.insert("", "end", values=(original_name, new_name, status))
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Close button
        ttk.Button(summary_window, text="Close", 
                  command=summary_window.destroy).pack(pady=10)
    
    def _rename_all_files(self):
        """Perform the actual file renaming."""
        if not self.renaming_data:
            messagebox.showwarning("Warning", "No files scheduled for renaming")
            return
        
        result = messagebox.askyesno("Confirm", 
                                   f"Rename {len(self.renaming_data)} files?\\nThis action cannot be undone!")
        if not result:
            return
        
        # Create output folder if needed
        utils.create_directory(self.output_folder)
        
        # Perform renaming
        success_count = 0
        error_count = 0
        rename_log = []
        
        total_files = len(self.renaming_data)
        
        for i, (original_path, new_name) in enumerate(self.renaming_data.items()):
            try:
                # Update progress
                progress = (i / total_files) * 100
                self.progress_var.set(progress)
                self.root.update_idletasks()
                
                # Determine final output path (handle duplicates)
                output_path = os.path.join(self.output_folder, new_name)
                final_output_path = utils.check_duplicate_filename(output_path)
                
                # Move and rename file
                shutil.move(original_path, final_output_path)
                
                # Log the action
                rename_log.append((original_path, final_output_path))
                success_count += 1
                
                self.status_var.set(f"Renamed: {os.path.basename(original_path)}")
                
            except Exception as e:
                print(f"Error renaming {original_path}: {e}")
                error_count += 1
        
        # Save log
        if rename_log:
            log_path = os.path.join(self.output_folder, config.LOG_FILENAME)
            utils.save_renaming_log(rename_log, log_path)
        
        # Complete progress
        self.progress_var.set(100)
        
        # Show results
        message = f"Renaming completed!\\n\\nSuccess: {success_count}\\nErrors: {error_count}"
        if rename_log:
            message += f"\\n\\nLog saved to: {config.LOG_FILENAME}"
        
        messagebox.showinfo("Results", message)
        
        # Reset progress
        self.progress_var.set(0)
        self.status_var.set("Renaming completed")
        
        # Clear renaming data
        self.renaming_data = {}
    
    def _save_session(self):
        """Save current session to file."""
        if not self.renaming_data:
            messagebox.showwarning("Warning", "No renaming data to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Session",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                import json
                
                session_data = {
                    "slide_folder": self.slide_folder,
                    "output_folder": self.output_folder,
                    "prefix": self.prefix,
                    "extension": self.extension,
                    "renaming_data": self.renaming_data
                }
                
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Session saved to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error saving session: {e}")
    
    def _load_session(self):
        """Load session from file."""
        file_path = filedialog.askopenfilename(
            title="Load Session",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                import json
                
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                
                # Restore session data
                self.slide_folder = session_data.get("slide_folder", "")
                self.output_folder = session_data.get("output_folder", "")
                self.prefix = session_data.get("prefix", config.DEFAULT_PREFIX)
                self.extension = session_data.get("extension", ".ndpi")
                self.renaming_data = session_data.get("renaming_data", {})
                
                # Update GUI
                self.folder_var.set(self.slide_folder)
                self.output_var.set(self.output_folder)
                # Don't override prefix here - let _load_images auto-set it based on folder
                self.ext_var.set(self.extension)
                
                # Reload images (this will auto-set prefix based on folder)
                self._load_images()
                
                # If session had a different prefix than auto-detected, restore it
                if self.prefix != self.prefix_var.get():
                    self.prefix_var.set(self.prefix)
                
                messagebox.showinfo("Success", f"Session loaded from {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error loading session: {e}")
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """Histology Slide Renaming Tool
        
Version 2.0

This application helps with histology slide review and file renaming:
• Phase 1: Extract label images from whole-slide images (parallel processing)
• Phase 2: GUI-based renaming using label images
• Auto-detection: Automatically determines which phase to run
• Smart prefix: Auto-sets model name based on directory
• Parallel processing: 3-12x faster label extraction

Supported formats: .svs, .ndpi, .scn, .vms, .vmu, .mrxs

Requirements:
• OpenSlide
• Pillow
• tkinter"""
        
        messagebox.showinfo("About", about_text)
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


def run_phase2(initial_folder: str = ""):
    """Run Phase 2: GUI for Label-Based Renaming."""
    app = RenamingGUI(initial_folder)
    app.run()


if __name__ == "__main__":
    run_phase2()