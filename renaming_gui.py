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
    
    def __init__(self, initial_folder: str = "", config_data: dict = None):
        self.root = tk.Tk()
        self.slide_folder = initial_folder
        self.label_folder = ""
        self.output_folder = ""
        self.prefix = config.DEFAULT_PREFIX
        self.extension = ".ndpi"
        
        self.label_files = []
        self.current_index = 0
        self.renaming_data = {}  # {original_path: new_name}
        
        # Configuration data from setup
        self.config_data = config_data or {}
        self.naming_sequence = []  # Auto-generated naming sequence
        self.naming_config_changed = False
        
        # Prevent infinite update loops
        self._updating_display = False
        self._updating_table = False
        
        # Optimized table loading with buffer for performance
        self.max_populated_index = -1  # Track how far we've populated the table
        self.table_buffer_size = 10  # Buffer ahead for smooth navigation
        
        # Simple renaming system - no buffer, only exact last file affects next
        self.renaming_buffer_size = 0  # No buffer - only exact last renamed file affects next
        self.last_renamed_index = -1  # Track the most recently renamed file
        
        # Track which files were explicitly renamed by user (vs auto-populated)
        self.user_explicit_renames = set()  # File paths explicitly renamed by user
        
        # Performance optimization - throttle table updates
        self._pending_table_update = False
        
        # Performance caches to avoid expensive repeated operations
        self._slide_path_cache = {}  # {slide_name: original_slide_path}
        self._identifier_cache = {}  # {filename: extracted_identifier}
        self._changed_rows = set()  # Track which table rows need updating
        self._image_cache = {}  # {image_path: PhotoImage} - Simple image cache
        
        # GUI components
        self.image_label = None
        self.identifier_var = None
        self.preview_var = None
        self.status_var = None
        self.progress_var = None
        
        self._setup_gui()
        
        # Bind keyboard navigation
        self._setup_keyboard_navigation()
        
        # If initial folder is provided, set it and try to load images
        if initial_folder and os.path.exists(initial_folder):
            # Ensure folder_var exists (it should be created in _setup_gui)
            if hasattr(self, 'folder_var'):
                self.folder_var.set(initial_folder)
                # Auto-load images if folder is valid
                try:
                    self._load_images()
                except Exception as e:
                    print(f"Could not auto-load images from {initial_folder}: {e}")
                    import traceback
                    traceback.print_exc()
                    # If auto-load fails, still call _update_display
                    self._update_display()
            else:
                print("Warning: folder_var not initialized, skipping auto-load")
                self._update_display()
        else:
            # Only call _update_display if we didn't load images (which calls it internally)
            self._update_display()
    
    def _center_and_size_window(self):
        """Center and size the window appropriately for the screen."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size (85% of screen or max 1200x900)
        window_width = min(int(screen_width * 0.85), 1200)
        window_height = min(int(screen_height * 0.85), 900)
        
        # Calculate position to center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _center_summary_window(self, window):
        """Center and size a summary window."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size (70% of screen or max 900x650)
        window_width = min(int(screen_width * 0.7), 900)
        window_height = min(int(screen_height * 0.7), 650)
        
        # Calculate position to center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _setup_keyboard_navigation(self):
        """Setup keyboard navigation for the application."""
        # Bind arrow keys for navigation (only when not in text entry)
        self.root.bind("<Left>", self._on_left_arrow)
        self.root.bind("<Right>", self._on_right_arrow)
        self.root.bind("<Return>", self._on_enter_key)
        
        # Focus handling
        self.root.focus_set()
    
    def _on_left_arrow(self, event):
        """Handle left arrow key press."""
        # Only navigate if focus is not in text entry
        focused_widget = self.root.focus_get()
        if not isinstance(focused_widget, tk.Entry):
            self._previous_image()
    
    def _on_right_arrow(self, event):
        """Handle right arrow key press."""
        # Only navigate if focus is not in text entry
        focused_widget = self.root.focus_get()
        if not isinstance(focused_widget, tk.Entry):
            self._next_image()
    
    def _on_enter_key(self, event):
        """Handle Enter key press."""
        # Only apply rename if focus is in identifier entry
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, tk.Entry) and focused_widget == self.identifier_entry:
            self._apply_current_rename()
    
    def _on_table_select(self, event):
        """Handle table row selection."""
        # Prevent infinite loops
        if self._updating_table or self._updating_display:
            return
            
        selection = self.table_tree.selection()
        if selection:
            item = selection[0]
            # Get the index from the item values
            values = self.table_tree.item(item, 'values')
            if values:
                try:
                    index = int(values[0]) - 1  # Convert to 0-based index
                    if 0 <= index < len(self.label_files) and index != self.current_index:
                        self.current_index = index
                        self._update_display()
                except (ValueError, IndexError):
                    pass
    
    def _on_table_double_click(self, event):
        """Handle table row double-click."""
        # Same as single click for now, but could add additional functionality
        self._on_table_select(event)
    
    def _populate_table(self):
        """Populate table with current file only (buffer=0)."""
        # Check if table_tree exists
        if not hasattr(self, 'table_tree'):
            return
        
        # Prevent infinite loops
        if self._updating_table:
            return
        
        self._updating_table = True
        
        try:
            if not self.label_files:
                return
            
            # Populate current file + buffer for smooth navigation
            target_index = min(self.current_index + self.table_buffer_size, len(self.label_files) - 1)
            
            # Only add new rows if we need to go further
            if target_index <= self.max_populated_index:
                # Current file already populated, table updates are handled separately
                return
            
            # Add new rows from max_populated_index + 1 to current_index
            start_index = max(0, self.max_populated_index + 1)
            
            for i in range(start_index, target_index + 1):
                if i >= len(self.label_files):
                    break
                    
                label_file = self.label_files[i]
                slide_name = os.path.splitext(label_file)[0]
                original_slide_path = self._find_original_slide(slide_name)
                
                # Get identifier and filename - PRIORITIZE user edits over auto-population
                identifier = ""
                new_filename = ""
                status = "Pending"
                
                # Check if user has already made edits (highest priority)
                if original_slide_path and original_slide_path in self.renaming_data:
                    new_filename = self.renaming_data[original_slide_path]
                    status = "Ready"
                    identifier = self._extract_identifier_from_name(new_filename)
                
                # Only auto-populate if no user edit exists
                elif self.config_data and hasattr(self, 'naming_sequence') and i < len(self.naming_sequence):
                    identifier = self.naming_sequence[i]
                
                # Insert new row
                self.table_tree.insert("", "end", values=(
                    i + 1,  # 1-based index
                    label_file,
                    identifier,
                    new_filename,
                    status
                ))
            
            # Update max populated index
            self.max_populated_index = target_index
            
        except Exception as e:
            # Don't let table errors stop the GUI from loading
            pass
        finally:
            self._updating_table = False
    
    def _update_existing_table_rows(self):
        """Update existing table rows to reflect current state (optimized)."""
        try:
            # Only update if we have changed rows or this is a full refresh
            if not self._changed_rows and hasattr(self, '_last_sequence_update'):
                return
            
            items = self.table_tree.get_children()
            for i, item in enumerate(items):
                values = self.table_tree.item(item, 'values')
                if values:
                    file_index = int(values[0]) - 1  # Convert to 0-based
                    
                    # Skip unchanged rows for performance (unless forcing update)
                    if self._changed_rows and file_index not in self._changed_rows:
                        continue
                    
                    if file_index < len(self.label_files):
                        # Get cached data for performance
                        label_file = self.label_files[file_index]
                        slide_name = os.path.splitext(label_file)[0]
                        original_slide_path = self._find_original_slide(slide_name)  # Cached
                        
                        # Get current identifier and filename
                        identifier = ""
                        new_filename = ""
                        status = "Pending"
                        
                        # PRIORITIZE: Always use latest naming_sequence for identifier display
                        if (self.config_data and hasattr(self, 'naming_sequence') and 
                            file_index < len(self.naming_sequence)):
                            identifier = self.naming_sequence[file_index]
                        
                        # Check if user has made edits (for filename and status)
                        if original_slide_path and original_slide_path in self.renaming_data:
                            new_filename = self.renaming_data[original_slide_path]
                            status = "Ready"
                            # For explicitly renamed files, extract identifier from actual filename
                            if original_slide_path in self.user_explicit_renames:
                                identifier = self._extract_identifier_from_name(new_filename)  # Cached
                        
                        # Update the row with current values
                        self.table_tree.item(item, values=(
                            file_index + 1,
                            label_file,
                            identifier,
                            new_filename,
                            status
                        ))
            
            # Clear changed rows after update
            self._changed_rows.clear()
            
        except Exception as e:
            pass
    
    def _highlight_current_row(self):
        """Highlight the current row in the table."""
        if not hasattr(self, 'table_tree') or not self.label_files:
            return
        
        try:
            # Clear current selection
            for item in self.table_tree.selection():
                self.table_tree.selection_remove(item)
            
            # Find current item by checking the INDEX column value (not row position)
            for item in self.table_tree.get_children():
                values = self.table_tree.item(item, 'values')
                if values:
                    try:
                        # The first column contains the 1-based index
                        file_index = int(values[0]) - 1  # Convert to 0-based
                        if file_index == self.current_index:
                            self.table_tree.selection_set(item)
                            self.table_tree.focus(item)
                            self.table_tree.see(item)
                            break
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            pass
    
    def _setup_gui(self):
        """Setup the main GUI."""
        self.root.title("Histology Slide Renaming Tool")
        
        # Make window resizable with better defaults
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        # Dynamic sizing based on screen
        self._center_and_size_window()
        
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
        
        # Naming configuration (if config_data is provided)
        if self.config_data:
            naming_frame = ttk.LabelFrame(config_frame, text="Auto-Naming Configuration")
            naming_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW, pady=10)
            
            ttk.Label(naming_frame, text="Amount per slide:").grid(row=0, column=0, padx=5, sticky=tk.W)
            self.amount_var = tk.IntVar(value=self.config_data.get('amount_per_slide', 2))
            amount_spinbox = ttk.Spinbox(naming_frame, from_=1, to=10, textvariable=self.amount_var, width=10)
            amount_spinbox.grid(row=0, column=1, padx=5)
            
            ttk.Label(naming_frame, text="Skip factor:").grid(row=0, column=2, padx=5, sticky=tk.W)
            self.skip_var = tk.IntVar(value=self.config_data.get('skip_factor', 1))
            skip_spinbox = ttk.Spinbox(naming_frame, from_=0, to=10, textvariable=self.skip_var, width=10)
            skip_spinbox.grid(row=0, column=3, padx=5)
            
            ttk.Button(naming_frame, text="Update Naming", command=self._update_naming_config).grid(row=1, column=1, columnspan=2, pady=5)
            
            # Bind changes to update naming
            self.amount_var.trace('w', self._on_naming_config_change)
            self.skip_var.trace('w', self._on_naming_config_change)
        
        config_frame.columnconfigure(1, weight=1)
        
        # Create main content paned window (split-pane layout)
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left pane: Image display frame
        image_frame = ttk.LabelFrame(main_paned, text="Label Image", padding=10)
        main_paned.add(image_frame, weight=2)  # Give more weight to image pane
        
        # Image display
        self.image_label = ttk.Label(image_frame, text="No image loaded", anchor=tk.CENTER)
        self.image_label.pack(expand=True)
        
        # Right pane: CSV Table Panel
        table_frame = ttk.LabelFrame(main_paned, text="Slide Overview", padding=10)
        main_paned.add(table_frame, weight=1)
        
        # Create treeview for slide overview
        self._create_table_panel(table_frame)
        
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
        self.identifier_entry = ttk.Entry(input_frame, textvariable=self.identifier_var, width=20)
        self.identifier_entry.grid(row=0, column=1, padx=5, sticky=tk.W)
        # Enter key binding is handled globally in _setup_keyboard_navigation()
        # Removed duplicate binding to prevent double-triggering
        
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
    
    def _create_table_panel(self, parent):
        """Create the CSV table panel with treeview."""
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Define columns
        columns = ("Index", "Label Image", "Identifier", "New Filename", "Status")
        self.table_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure column headings and widths
        self.table_tree.heading("Index", text="Index")
        self.table_tree.heading("Label Image", text="Label Image")
        self.table_tree.heading("Identifier", text="Identifier")
        self.table_tree.heading("New Filename", text="New Filename")
        self.table_tree.heading("Status", text="Status")
        
        # Set column widths
        self.table_tree.column("Index", width=50, minwidth=40)
        self.table_tree.column("Label Image", width=120, minwidth=100)
        self.table_tree.column("Identifier", width=80, minwidth=60)
        self.table_tree.column("New Filename", width=150, minwidth=120)
        self.table_tree.column("Status", width=80, minwidth=60)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.table_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.table_tree.xview)
        self.table_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.table_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind table selection events
        self.table_tree.bind("<<TreeviewSelect>>", self._on_table_select)
        self.table_tree.bind("<Double-1>", self._on_table_double_click)
    
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
        
        # Pre-build slide path cache for performance
        self._build_slide_path_cache()
        
        # Generate naming sequence and auto-populate if config data is available
        if self.config_data:
            self.naming_sequence = self._generate_naming_sequence(len(self.label_files))
            self._auto_populate_identifiers()
            self.status_var.set(f"Loaded {len(self.label_files)} label images with auto-naming")
        else:
            self.status_var.set(f"Loaded {len(self.label_files)} label images")
        
        # Populate the table with loaded data (deferred to avoid hanging)
        self._update_display()
        # Schedule initial table population
        self.root.after(100, self._populate_table)
    
    def _update_display(self):
        """Update the image display and info."""
        # Prevent infinite loops
        if self._updating_display:
            return
        
        self._updating_display = True
        
        try:
            if not self.label_files:
                self.image_label.config(image='', text="No images loaded")
                if hasattr(self, 'image_info_var'):
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
            if hasattr(self, 'image_info_var'):
                self.image_info_var.set(f"Image {self.current_index + 1} of {len(self.label_files)}: {current_file}")
            
            # Update identifier - Use latest naming_sequence unless explicitly renamed by user
            slide_name = os.path.splitext(current_file)[0]
            original_slide_path = self._find_original_slide(slide_name)
            
            # Check if user has explicitly renamed this slide (highest priority)
            if (original_slide_path and 
                original_slide_path in self.user_explicit_renames and 
                original_slide_path in self.renaming_data):
                # Extract identifier from user's explicit rename
                stored_name = self.renaming_data[original_slide_path]
                identifier = self._extract_identifier_from_name(stored_name)
                self.identifier_var.set(identifier)
            # Use updated naming sequence for auto-populated files
            elif self.config_data and self.current_index < len(self.naming_sequence):
                # Auto-populate with the latest naming sequence
                self.identifier_var.set(self.naming_sequence[self.current_index])
            else:
                self.identifier_var.set("")
            
            self._update_preview()
            
            # Update table highlighting (deferred to avoid blocking)
            self.root.after_idle(self._update_table_selection)
            
        finally:
            self._updating_display = False
    
    def _update_table_selection(self):
        """Update table selection to match current image."""
        if not hasattr(self, 'table_tree') or not self.label_files:
            return
        
        # Prevent infinite loops
        if self._updating_table:
            return
        
        # Populate table if needed (lightweight, append-only)
        self._populate_table()
        
        # Highlight current row
        self._highlight_current_row()
    
    def _find_original_slide(self, slide_name: str) -> Optional[str]:
        """Find the original slide file corresponding to the label (cached)."""
        # Check cache first for performance
        if slide_name in self._slide_path_cache:
            return self._slide_path_cache[slide_name]
        
        # Search file system only if not cached
        for ext in config.SUPPORTED_EXTENSIONS:
            slide_path = os.path.join(self.slide_folder, f"{slide_name}{ext}")
            if os.path.exists(slide_path):
                self._slide_path_cache[slide_name] = slide_path
                return slide_path
        
        # Cache negative results too
        self._slide_path_cache[slide_name] = None
        return None
    
    def _extract_identifier_from_name(self, filename: str) -> str:
        """Extract identifier from generated filename (cached)."""
        # Check cache first for performance
        if filename in self._identifier_cache:
            return self._identifier_cache[filename]
        
        # Remove prefix and extension
        base = os.path.splitext(filename)[0]
        if base.startswith(self.prefix):
            identifier_part = base[len(self.prefix):]
            # Convert underscores back to spaces for display
            identifier = identifier_part.replace('_', ' ')
        else:
            identifier = ""
        
        # Cache result
        self._identifier_cache[filename] = identifier
        return identifier
    
    def _build_slide_path_cache(self):
        """Pre-build the slide path cache for all label files to improve performance."""
        if not self.label_files:
            return
        
        # Build cache for all slide names at once
        for label_file in self.label_files:
            slide_name = os.path.splitext(label_file)[0]
            if slide_name not in self._slide_path_cache:
                # Cache the path (this will populate the cache)
                self._find_original_slide(slide_name)

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
        # Trigger dynamic table population
        self.root.after_idle(self._populate_table)
    
    def _next_image(self):
        """Go to next image."""
        if not self.label_files:
            return
        
        self.current_index = (self.current_index + 1) % len(self.label_files)
        self._update_display()
        # Trigger dynamic table population
        self.root.after_idle(self._populate_table)
    
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
            
            # Mark as explicitly renamed by user (not auto-populated)
            self.user_explicit_renames.add(original_slide_path)
            
            # Update last renamed index
            self.last_renamed_index = self.current_index
            
            # If config data exists and user manually edited the identifier, 
            # adjust subsequent sequence numbers (smart buffer logic)
            if self.config_data and self.current_index < len(self.naming_sequence):
                expected_identifier = self.naming_sequence[self.current_index]
                user_identifier = identifier.replace(' ', '_')  # Normalize underscores
                
                if user_identifier != expected_identifier:
                    self._smart_adjust_sequence(self.current_index, user_identifier)
            
            self.status_var.set(f"Applied rename: {os.path.basename(original_slide_path)} → {new_filename}")
            
            # Mark current row as changed for optimized table update
            self._changed_rows.add(self.current_index)
            
            # Force table update to show changes immediately (throttled)
            self._schedule_table_update()
            
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
        summary_window.resizable(True, True)
        summary_window.minsize(600, 400)
        
        # Center and size the summary window
        self._center_summary_window(summary_window)
        
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
                
                # 1. Rename the WSI file
                # Determine final output path (handle duplicates)
                output_path = os.path.join(self.output_folder, new_name)
                final_output_path = utils.check_duplicate_filename(output_path)
                
                # Move and rename WSI file
                shutil.move(original_path, final_output_path)
                
                # Log the WSI file action
                rename_log.append((original_path, final_output_path))
                success_count += 1
                
                # 2. Rename the corresponding JPEG label file
                try:
                    # Find corresponding label file
                    original_base = os.path.splitext(os.path.basename(original_path))[0]
                    label_file_path = os.path.join(self.label_folder, f"{original_base}.jpg")
                    
                    if os.path.exists(label_file_path):
                        # Generate new label filename
                        new_base = os.path.splitext(new_name)[0]
                        new_label_name = f"{new_base}.jpg"
                        label_output_path = os.path.join(self.label_folder, new_label_name)
                        
                        # Handle duplicates for label file
                        final_label_path = utils.check_duplicate_filename(label_output_path)
                        
                        # Rename label file
                        shutil.move(label_file_path, final_label_path)
                        
                        # Log the label file action
                        rename_log.append((label_file_path, final_label_path))
                        
                        self.status_var.set(f"Renamed: {os.path.basename(original_path)} + label")
                    else:
                        # Label file doesn't exist - warn but don't fail
                        print(f"Warning: Label file not found: {label_file_path}")
                        self.status_var.set(f"Renamed: {os.path.basename(original_path)} (no label file)")
                        
                except Exception as label_error:
                    # Label file renaming failed - warn but don't fail the main operation
                    print(f"Warning: Could not rename label file for {original_path}: {label_error}")
                    self.status_var.set(f"Renamed: {os.path.basename(original_path)} (label rename failed)")
                
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
    
    def _generate_naming_sequence(self, count: int) -> list:
        """Generate the naming sequence based on parameters."""
        if not self.config_data:
            return []
        
        amount_per_slide = self.config_data.get('amount_per_slide', 2)
        skip_factor = self.config_data.get('skip_factor', 1)
        
        # Use the updated values if they exist
        if hasattr(self, 'amount_var'):
            amount_per_slide = self.amount_var.get()
        if hasattr(self, 'skip_var'):
            skip_factor = self.skip_var.get()
        
        sequence = []
        current = 1
        slides_processed = 0
        
        while slides_processed < count:
            # Create combined identifier for this slide
            identifiers = []
            
            for i in range(amount_per_slide):
                identifiers.append(f"{current:03d}")
                current += 1
            
            # Combine identifiers with underscore
            combined_identifier = "_".join(identifiers)
            sequence.append(combined_identifier)
            slides_processed += 1
            
            # Skip numbers for next slide if we have more to process
            if slides_processed < count:
                current += skip_factor
        
        return sequence
    
    def _update_naming_config(self):
        """Update the naming configuration and regenerate sequence."""
        if not self.label_files:
            messagebox.showwarning("Warning", "Please load images first.")
            return
        
        # Regenerate naming sequence
        self.naming_sequence = self._generate_naming_sequence(len(self.label_files))
        
        # Clear existing auto-assigned renaming data but keep manual entries
        keys_to_remove = []
        for original_path, new_name in self.renaming_data.items():
            # Check if this was an auto-generated name
            base_name = os.path.splitext(os.path.basename(original_path))[0]
            if any(seq_num in new_name for seq_num in self.naming_sequence):
                keys_to_remove.append(original_path)
        
        for key in keys_to_remove:
            del self.renaming_data[key]
        
        # Auto-populate with new sequence
        self._auto_populate_identifiers()
        
        # Refresh table with updated data (deferred)
        self.root.after_idle(self._populate_table)
        
        # Update display
        self._update_display()
        self.status_var.set("Naming configuration updated")
    
    def _on_naming_config_change(self, *args):
        """Handle naming configuration changes during the process."""
        if not hasattr(self, 'amount_var') or not hasattr(self, 'skip_var'):
            return
            
        # Get new configuration values
        new_amount = self.amount_var.get()
        new_skip = self.skip_var.get()
        
        # Only regenerate sequence for proceeding slides (from current index onward)
        if hasattr(self, 'naming_sequence') and self.label_files:
            # Keep already processed slides unchanged
            # Only update from current index forward
            start_index = self.current_index
            
            # Generate new sequence for remaining slides
            remaining_slides = len(self.label_files) - start_index
            if remaining_slides > 0:
                # Get the last used number to continue from
                if start_index > 0 and start_index - 1 < len(self.naming_sequence):
                    prev_identifier = self.naming_sequence[start_index - 1]
                    
                    # Extract the last number from previous identifier
                    import re
                    numbers = re.findall(r'\d+', prev_identifier)
                    if numbers:
                        last_num = int(numbers[-1])
                        next_base = last_num + 1 + new_skip
                    else:
                        next_base = 1
                else:
                    next_base = 1
                
                # Update subsequent groups with new configuration
                # Regenerate naming sequence for files after the current index
                self._regenerate_sequence_from_index(start_index, next_base, new_amount, new_skip)
                
                # Refresh table to show changes for proceeding slides only
                self.root.after_idle(lambda: self._populate_table())
        
        self.naming_config_changed = True
    
    def _regenerate_sequence_from_index(self, start_index, next_base, amount_per_slide, skip_factor):
        """Regenerate naming sequence from a specific index with new configuration."""
        try:
            current_base = next_base
            
            # Only update files from start_index onwards that haven't been explicitly renamed
            for idx in range(start_index, len(self.naming_sequence)):
                if not self._is_user_renamed(idx):
                    if amount_per_slide > 1:
                        numbers = [f"{current_base + i:03d}" for i in range(amount_per_slide)]
                        suggestion = "_".join(numbers)
                        self.naming_sequence[idx] = suggestion
                    else:
                        suggestion = f"{current_base:03d}"
                        self.naming_sequence[idx] = suggestion
                    
                    # Mark this row as changed for optimized table update
                    self._changed_rows.add(idx)
                    
                    # Move to next group
                    current_base += amount_per_slide + skip_factor
                else:
                    # If we hit an explicitly renamed file, continue but adjust base
                    # Extract the user's number to continue sequence properly
                    if idx < len(self.label_files):
                        label_file = self.label_files[idx]
                        slide_name = os.path.splitext(label_file)[0]
                        original_slide_path = self._find_original_slide(slide_name)
                        
                        if original_slide_path and original_slide_path in self.renaming_data:
                            user_filename = self.renaming_data[original_slide_path]
                            user_identifier = self._extract_identifier_from_name(user_filename)
                            
                            # Parse user's numbers and continue from there
                            numbers = self._parse_identifier_numbers(user_identifier.replace(' ', '_'))
                            if numbers:
                                current_base = numbers[-1] + 1 + skip_factor
            
            # Schedule table update to reflect changes
            self._schedule_table_update()
            
        except Exception as e:
            print(f"Error regenerating sequence: {e}")
    
    def _auto_populate_identifiers(self):
        """Auto-populate identifiers based on naming sequence."""
        if not self.naming_sequence or not self.label_files:
            return
        
        for i, label_file in enumerate(self.label_files):
            if i < len(self.naming_sequence):
                slide_file = self._get_corresponding_slide_file(label_file)
                if slide_file and slide_file not in self.renaming_data:
                    # Auto-assign the identifier
                    identifier = self.naming_sequence[i]
                    new_name = f"{self.prefix}{identifier}{self.extension}"
                    self.renaming_data[slide_file] = new_name
    
    def _get_corresponding_slide_file(self, label_file: str) -> Optional[str]:
        """Get the corresponding slide file for a label file."""
        label_base = os.path.splitext(os.path.basename(label_file))[0]
        
        # Look for slide file with matching base name
        slide_files = utils.get_slide_files(self.slide_folder)
        for slide_file in slide_files:
            slide_base = os.path.splitext(os.path.basename(slide_file))[0]
            if slide_base == label_base:
                return slide_file
        
        return None
    
    def _smart_adjust_sequence(self, start_index: int, new_identifier: str):
        """Simple sequence adjustment - current file affects next file only."""
        try:
            # Update current identifier first
            self.naming_sequence[start_index] = new_identifier.replace(' ', '_')
            
            # SIMPLE LOGIC: Only propagate if editing the current file or the last renamed file
            if start_index != self.current_index and start_index != self.last_renamed_index:
                # Not current file or last renamed file - no cascade
                return
            
            # This file should affect the next file's suggestion
            import re
            new_num_str = new_identifier.replace(' ', '_').strip()
            
            # Parse the identifier correctly - handle formats like "005006" or "005_006"
            if '_' in new_num_str:
                # Already has underscores, split by them
                number_parts = new_num_str.split('_')
                numbers = [int(part) for part in number_parts if part.isdigit()]
            else:
                # No underscores - check if it's consecutive 3-digit numbers like "005006"
                if len(new_num_str) >= 6 and len(new_num_str) % 3 == 0:
                    # Split into 3-digit chunks
                    numbers = []
                    for i in range(0, len(new_num_str), 3):
                        chunk = new_num_str[i:i+3]
                        if chunk.isdigit():
                            numbers.append(int(chunk))
                else:
                    # Single number or other format
                    numbers = [int(match) for match in re.findall(r'\d+', new_num_str)]
            
            if not numbers:
                return
            
            # Calculate next file's starting number
            last_number = max(numbers)
            amount_per_slide = self.config_data.get('amount_per_slide', 2)
            skip_factor = self.config_data.get('skip_factor', 1)
            
            if hasattr(self, 'amount_var'):
                amount_per_slide = self.amount_var.get()
            if hasattr(self, 'skip_var'):
                skip_factor = self.skip_var.get()
            
            next_base = last_number + 1 + skip_factor
            next_index = start_index + 1
            
            # Update all subsequent files that haven't been explicitly renamed
            current_base = next_base
            idx = next_index
            
            while idx < len(self.naming_sequence):
                # Only update files that haven't been explicitly renamed by user
                if not self._is_user_renamed(idx):
                    if amount_per_slide > 1:
                        numbers = [f"{current_base + i:03d}" for i in range(amount_per_slide)]
                        suggestion = "_".join(numbers)
                        self.naming_sequence[idx] = suggestion
                    else:
                        suggestion = f"{current_base:03d}"
                        self.naming_sequence[idx] = suggestion
                    
                    # Mark this row as changed for optimized table update
                    self._changed_rows.add(idx)
                    
                    # Move to next group
                    current_base += amount_per_slide + skip_factor
                else:
                    # If we hit an explicitly renamed file, stop propagating
                    break
                
                idx += 1
            
            # Update table to reflect sequence changes (throttled for performance)
            self._schedule_table_update()
            
        except Exception as e:
            print(f"Error in sequence adjustment: {e}")
    
    def _schedule_table_update(self):
        """Schedule a table update, throttled to prevent excessive updates."""
        if not self._pending_table_update:
            self._pending_table_update = True
            self.root.after_idle(self._perform_table_update)
    
    def _perform_table_update(self):
        """Perform the actual table update."""
        self._pending_table_update = False
        self._update_existing_table_rows()
    
    def _is_user_renamed(self, index: int) -> bool:
        """Check if a file at given index has been explicitly renamed by the user (not auto-populated)."""
        if index >= len(self.label_files):
            return False
        
        # Get the corresponding slide file
        label_file = self.label_files[index]
        slide_name = os.path.splitext(label_file)[0]
        original_slide_path = self._find_original_slide(slide_name)
        
        # Check if this file was explicitly renamed by user (not just auto-populated)
        return original_slide_path and original_slide_path in self.user_explicit_renames
    
    def _update_auto_renamed_slides(self):
        """Update auto-populated renaming data based on current sequence."""
        if not self.naming_sequence or not self.label_files:
            return
        
        for i, label_file in enumerate(self.label_files):
            if i < len(self.naming_sequence):
                slide_file = self._get_corresponding_slide_file(label_file)
                if slide_file:
                    # Only update if this was previously auto-assigned
                    # (check if the current naming matches the old sequence)
                    if slide_file in self.renaming_data:
                        old_name = self.renaming_data[slide_file]
                        # If it follows the expected pattern, update it
                        if self.prefix in old_name:
                            identifier = self.naming_sequence[i]
                            new_name = f"{self.prefix}{identifier}{self.extension}"
                            self.renaming_data[slide_file] = new_name
    
    def _show_about(self):
        """Show about dialog."""
        about_text = """Histology Slide Renaming Tool
        
Version 2.0 with Setup Screen

This application helps with histology slide review and file renaming:
• Setup Screen: Configure crop presets and naming patterns
• Phase 1: Extract label images from whole-slide images (parallel processing)
• Phase 2: GUI-based renaming using label images with auto-numbering
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


def run_phase2_with_config(initial_folder: str, config_data: dict):
    """Run Phase 2: GUI for Label-Based Renaming with configuration."""
    print(f"Running Phase 2 with configuration:")
    print(f"  - Amount per slide: {config_data.get('amount_per_slide', 2)}")
    print(f"  - Skip factor: {config_data.get('skip_factor', 1)}")
    
    app = RenamingGUI(initial_folder, config_data)
    app.run()


if __name__ == "__main__":
    run_phase2()