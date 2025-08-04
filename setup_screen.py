"""Setup screen for configuring the histology slide renaming workflow."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from typing import Dict, Optional, Tuple
import config


class SetupScreen:
    """GUI for configuring workflow parameters before processing begins."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Histology Slide Renaming - Setup")
        
        # Make window resizable and set minimum size
        self.root.resizable(True, True)
        self.root.minsize(600, 500)
        
        # Center window on screen with dynamic sizing
        self._center_window()
        
        # Configuration variables
        self.folder_path = ""
        self.use_default_crop = tk.BooleanVar(value=True)
        self.crop_coords = [10, 13, 578, 732]  # Default crop preset
        self.amount_per_slide = tk.IntVar(value=2)
        self.skip_factor = tk.IntVar(value=1)
        self.batch_size = tk.IntVar(value=config.DEFAULT_BATCH_SIZE)
        
        # Results
        self.config_data = None
        self.should_proceed = False
        
        self._setup_gui()
    
    def _center_window(self):
        """Center the window on screen with appropriate size."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size (80% of screen or max 800x600)
        window_width = min(int(screen_width * 0.8), 800)
        window_height = min(int(screen_height * 0.8), 600)
        
        # Calculate position to center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _center_preview_window(self, window):
        """Center a preview window on screen."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size (70% of screen or max 700x500)
        window_width = min(int(screen_width * 0.7), 700)
        window_height = min(int(screen_height * 0.7), 500)
        
        # Calculate position to center window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def _setup_gui(self):
        """Setup the main GUI."""
        # Title
        title_label = tk.Label(
            self.root,
            text="Workflow Setup",
            font=("Arial", 18, "bold"),
            pady=20
        )
        title_label.pack()
        
        # Description
        desc_text = """Configure the parameters for your histology slide processing workflow.
These settings will be used for both label extraction and renaming phases."""
        
        desc_label = tk.Label(
            self.root,
            text=desc_text,
            font=("Arial", 10),
            justify=tk.CENTER,
            pady=10
        )
        desc_label.pack()
        
        # Create a scrollable frame for the content
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 20), pady=10)
        
        # Main configuration frame inside scrollable frame
        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Folder selection
        self._create_folder_section(main_frame)
        
        # Crop preset section
        self._create_crop_section(main_frame)
        
        # Slide naming section
        self._create_naming_section(main_frame)
        
        # Batch size section
        self._create_batch_section(main_frame)
        
        # Bind mousewheel to canvas for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Add keyboard shortcuts
        self.root.bind('<Escape>', lambda e: self._cancel())
        self.root.bind('<Return>', lambda e: self._start_processing())
        self.root.bind('<F1>', lambda e: self._show_help())
        
        # Button frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel,
            width=15
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            button_frame,
            text="Start Processing",
            command=self._start_processing,
            width=20
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame,
            text="Preview Naming",
            command=self._preview_naming,
            width=15
        ).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Status/help label
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        status_label = ttk.Label(
            status_frame,
            text="💡 Window is resizable • Use mouse wheel to scroll • Press F1 for help",
            font=("Arial", 8),
            foreground="gray"
        )
        status_label.pack(anchor=tk.CENTER)
    
    def _create_folder_section(self, parent):
        """Create folder selection section."""
        folder_frame = ttk.LabelFrame(parent, text="1. Select Slide Folder", padding=15)
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(folder_frame, text="Choose the folder containing your WSI files:").pack(anchor=tk.W)
        
        path_frame = ttk.Frame(folder_frame)
        path_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(path_frame, textvariable=self.folder_var, width=60)
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            path_frame,
            text="Browse",
            command=self._browse_folder
        ).pack(side=tk.RIGHT, padx=(10, 0))
    
    def _create_crop_section(self, parent):
        """Create crop preset section."""
        crop_frame = ttk.LabelFrame(parent, text="2. Crop Preset", padding=15)
        crop_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            crop_frame,
            text="Choose how to crop label images during extraction:"
        ).pack(anchor=tk.W)
        
        # Default crop option
        default_frame = ttk.Frame(crop_frame)
        default_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Radiobutton(
            default_frame,
            text="Use default crop preset (10, 13, 578, 732)",
            variable=self.use_default_crop,
            value=True
        ).pack(side=tk.LEFT)
        
        # Custom crop option
        custom_frame = ttk.Frame(crop_frame)
        custom_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(
            custom_frame,
            text="Select crop region manually during Phase 1",
            variable=self.use_default_crop,
            value=False
        ).pack(side=tk.LEFT)
    
    def _create_naming_section(self, parent):
        """Create slide naming configuration section."""
        naming_frame = ttk.LabelFrame(parent, text="3. Slide Naming Order", padding=15)
        naming_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            naming_frame,
            text="Configure automatic slide numbering pattern:"
        ).pack(anchor=tk.W)
        
        # Configuration inputs
        config_frame = ttk.Frame(naming_frame)
        config_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Amount per slide
        ttk.Label(config_frame, text="Amount per slide:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        amount_spinbox = ttk.Spinbox(
            config_frame,
            from_=1, to=10,
            textvariable=self.amount_per_slide,
            width=10
        )
        amount_spinbox.grid(row=0, column=1, padx=(0, 20))
        
        # Skip factor
        ttk.Label(config_frame, text="Skip factor:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        skip_spinbox = ttk.Spinbox(
            config_frame,
            from_=0, to=10,
            textvariable=self.skip_factor,
            width=10
        )
        skip_spinbox.grid(row=0, column=3)
        
        # Example
        example_frame = ttk.Frame(naming_frame)
        example_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            example_frame,
            text="Example: Amount=2, Skip=1 → slides labeled as 001_002, [skip 003], 004_005, [skip 006], etc.",
            font=("Arial", 9),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        # Update example when values change
        self.amount_per_slide.trace('w', self._update_naming_example)
        self.skip_factor.trace('w', self._update_naming_example)
        
        # Store reference to example label for updates
        self.example_label = example_frame.winfo_children()[0]
    
    def _create_batch_section(self, parent):
        """Create batch size section."""
        batch_frame = ttk.LabelFrame(parent, text="4. Processing Batch Size", padding=15)
        batch_frame.pack(fill=tk.X)
        
        ttk.Label(
            batch_frame,
            text="Number of slides to process simultaneously:"
        ).pack(anchor=tk.W)
        
        batch_config_frame = ttk.Frame(batch_frame)
        batch_config_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(batch_config_frame, text="Batch size:").pack(side=tk.LEFT)
        
        batch_spinbox = ttk.Spinbox(
            batch_config_frame,
            from_=1, to=50,
            textvariable=self.batch_size,
            width=10
        )
        batch_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(
            batch_config_frame,
            text="(higher = faster but more memory usage)",
            font=("Arial", 9),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(10, 0))
    
    def _browse_folder(self):
        """Browse for slide folder."""
        folder = filedialog.askdirectory(
            title="Select Folder with Slide Files",
            initialdir=os.getcwd()
        )
        if folder:
            self.folder_var.set(folder)
            self.folder_path = folder
    
    def _update_naming_example(self, *args):
        """Update the naming example when parameters change."""
        try:
            amount = self.amount_per_slide.get()
            skip = self.skip_factor.get()
            
            # Generate example sequence with combined identifiers
            example_parts = []
            current = 1
            
            for i in range(3):  # Show 3 slide examples
                # Create combined identifier for this slide
                identifiers = []
                for j in range(amount):
                    identifiers.append(f"{current:03d}")
                    current += 1
                
                combined_id = "_".join(identifiers)
                example_parts.append(combined_id)
                
                # Show skipped numbers
                if skip > 0 and i < 2:  # Don't show skip after last example
                    skipped = []
                    for k in range(skip):
                        skipped.append(f"{current:03d}")
                        current += 1
                    if skipped:
                        example_parts.append(f"[skip {', '.join(skipped)}]")
            
            example_text = f"Example: Amount={amount}, Skip={skip} → slides labeled as {', '.join(example_parts)}..."
            
            # Update the example label
            for widget in self.example_label.master.winfo_children():
                if isinstance(widget, ttk.Label):
                    widget.config(text=example_text)
                    break
            
        except (tk.TclError, ValueError):
            # Handle cases where spinbox values are being changed
            pass
    
    def _preview_naming(self):
        """Preview the naming pattern with actual slide count."""
        if not self.folder_path or not os.path.exists(self.folder_path):
            messagebox.showerror("Error", "Please select a valid slide folder first.")
            return
        
        # Count WSI files
        import utils
        wsi_files = utils.get_slide_files(self.folder_path)
        if not wsi_files:
            messagebox.showerror("Error", "No supported WSI files found in the selected folder.")
            return
        
        # Generate naming preview
        naming_sequence = self._generate_naming_sequence(len(wsi_files))
        
        # Create preview window
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Naming Preview")
        preview_window.resizable(True, True)
        preview_window.minsize(500, 300)
        
        # Center preview window
        self._center_preview_window(preview_window)
        
        ttk.Label(
            preview_window,
            text=f"Preview for {len(wsi_files)} slides",
            font=("Arial", 14, "bold")
        ).pack(pady=10)
        
        # Scrollable text area
        text_frame = ttk.Frame(preview_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=60, height=20)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add content
        content = "Slide files will be numbered as follows:\n\n"
        for i, (filename, number) in enumerate(zip(wsi_files, naming_sequence)):
            content += f"{os.path.basename(filename)} → {number}\n"
            if i >= 50:  # Limit display for very large sets
                content += f"\n... and {len(wsi_files) - 50} more files"
                break
        
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(
            preview_window,
            text="Close",
            command=preview_window.destroy
        ).pack(pady=10)
    
    def _generate_naming_sequence(self, count: int) -> list:
        """Generate the naming sequence based on parameters."""
        sequence = []
        current = 1
        slides_processed = 0
        
        while slides_processed < count:
            # Create combined identifier for this slide
            amount_per_slide = self.amount_per_slide.get()
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
                current += self.skip_factor.get()
        
        return sequence
    
    def _start_processing(self):
        """Validate settings and start processing."""
        if not self.folder_path or not os.path.exists(self.folder_path):
            messagebox.showerror("Error", "Please select a valid slide folder.")
            return
        
        # Validate naming parameters
        if self.amount_per_slide.get() < 1:
            messagebox.showerror("Error", "Amount per slide must be at least 1.")
            return
        
        if self.skip_factor.get() < 0:
            messagebox.showerror("Error", "Skip factor cannot be negative.")
            return
        
        if self.batch_size.get() < 1:
            messagebox.showerror("Error", "Batch size must be at least 1.")
            return
        
        # Create configuration data
        self.config_data = {
            'folder_path': self.folder_path,
            'use_default_crop': self.use_default_crop.get(),
            'crop_coords': self.crop_coords,
            'amount_per_slide': self.amount_per_slide.get(),
            'skip_factor': self.skip_factor.get(),
            'batch_size': self.batch_size.get()
        }
        
        # Save configuration to file for later use
        self._save_config()
        
        self.should_proceed = True
        self.root.destroy()
    
    def _cancel(self):
        """Cancel setup."""
        self.should_proceed = False
        self.root.destroy()
    
    def _save_config(self):
        """Save configuration to a file."""
        config_path = os.path.join(self.folder_path, 'workflow_config.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
    
    def _show_help(self):
        """Show help dialog with keyboard shortcuts."""
        help_text = """Keyboard Shortcuts:
        
Enter - Start Processing
Escape - Cancel Setup
F1 - Show this help

Window Controls:
- Window is resizable - drag corners/edges
- Content is scrollable with mouse wheel
- All dialogs center automatically

Configuration Tips:
- Default crop preset works for most slides
- Amount per slide: how many slides per group
- Skip factor: how many numbers to skip between groups
- Preview shows exact numbering pattern"""
        
        messagebox.showinfo("Setup Help", help_text)
    
    def run(self) -> Optional[Dict]:
        """Run the setup screen and return configuration."""
        self.root.mainloop()
        return self.config_data if self.should_proceed else None


def load_config(folder_path: str) -> Optional[Dict]:
    """Load configuration from file if it exists."""
    config_path = os.path.join(folder_path, 'workflow_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load configuration: {e}")
    return None


def run_setup() -> Optional[Dict]:
    """Run the setup screen and return configuration."""
    setup = SetupScreen()
    return setup.run()


if __name__ == "__main__":
    config_data = run_setup()
    if config_data:
        print("Configuration saved:")
        print(json.dumps(config_data, indent=2))
    else:
        print("Setup cancelled")